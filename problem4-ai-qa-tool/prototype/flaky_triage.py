"""
Flaky Triage Assistant — 프로토타입

CI 실패 레코드(JSON)를 읽어, 각 실패를 5개 카테고리 중 하나로 분류하고
근거 / 제안 조치 / Slack·Jira용 코멘트 초안을 생성한다.

동작 모드
    - 기본(폴백) 모드: ANTHROPIC_API_KEY가 없거나 --use-llm을 주지 않으면
      규칙 기반 휴리스틱(rule_based_classify)으로 동작한다. 키 없이도 바로 실행 가능.
    - LLM 모드(--use-llm): prompts/classify_prompt.md 템플릿으로 프롬프트를 구성해
      Claude에 분류를 요청한다. 응답 파싱에 실패하면 규칙 기반으로 자동 폴백한다.

실행 예시
    python flaky_triage.py sample_failures.json
    python flaky_triage.py sample_failures.json --use-llm
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

PROMPT_TEMPLATE_PATH = Path(__file__).parent / "prompts" / "classify_prompt.md"
CONFIDENCE_THRESHOLD = 0.6  # 이 미만이면 자동 라우팅하지 않고 "사람 확인 필요"로 표시

CATEGORY_TO_OWNER = {
    "ENV_ISSUE": "INFRA",
    "TIMING_ISSUE": "QA",
    "TEST_CODE_DEFECT": "QA",
    "DATA_ISSUE": "QA",
    "REAL_BUG": "DEV",
}


@dataclass
class TriageResult:
    category: str
    confidence: float
    evidence: str
    suggested_owner: str
    suggested_fix: str
    draft_comment: str
    source: str  # "llm" | "rule_based"


def load_failures(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 규칙 기반 폴백 분류기
# ---------------------------------------------------------------------------
def rule_based_classify(failure: dict) -> TriageResult:
    stack = failure.get("stack_trace", "")
    history: list[bool] = failure.get("recent_history", [])
    retry_passed = failure.get("retry_passed")

    fail_rate = (len(history) - sum(history)) / len(history) if history else 0.0
    is_consistent_failure = len(history) >= 3 and fail_rate >= 0.9  # 최근 이력 대부분 실패

    def result(category: str, confidence: float, evidence: str, fix: str) -> TriageResult:
        return TriageResult(
            category=category,
            confidence=confidence,
            evidence=evidence,
            suggested_owner=CATEGORY_TO_OWNER[category],
            suggested_fix=fix,
            draft_comment=(
                f"[Flaky Triage] `{failure['test_name']}` 실패를 `{category}`로 잠정 분류했습니다 "
                f"(신뢰도 {confidence:.0%}, 규칙 기반). 근거: {evidence} 담당: {CATEGORY_TO_OWNER[category]}. "
                f"확인 후 결과를 알려주시면 분류 정확도 개선에 반영됩니다."
            ),
            source="rule_based",
        )

    lowered = stack.lower()

    if any(k in lowered for k in ["connectionerror", "connection refused", "timed out connecting", "503"]):
        return result(
            "ENV_ISSUE", 0.75,
            "스택트레이스에 네트워크/연결 오류(ConnectionError, Connection refused 등) 문구가 확인됨.",
            "스테이징 인프라 상태 확인, 재시도 정책 점검. 인프라 이슈면 배포/점검 일정과 대조.",
        )

    if "timeoutexception" in lowered and retry_passed:
        return result(
            "TIMING_ISSUE", 0.8,
            "TimeoutException 발생 + 재시도 시 통과함 → 고정 대기/타이밍 부족이 원인일 가능성이 높음.",
            "고정 sleep 제거 및 폴링 기반 명시적 대기로 전환 (UiWaitUtils 등). 문제3 리팩토링 패턴 적용.",
        )

    if is_consistent_failure and not retry_passed:
        return result(
            "REAL_BUG", 0.85,
            f"최근 {len(history)}회 중 {sum(1 for h in history if not h)}회 실패, 재시도해도 통과하지 않음 → 우연이 아닌 일관된 실패.",
            "테스트가 실제 결함을 정확히 잡아낸 것으로 판단. 개발팀에 재현 절차와 함께 이관.",
        )

    if "assert" in lowered and not is_consistent_failure and history.count(True) > 0 and history.count(False) > 0:
        return result(
            "DATA_ISSUE", 0.55,
            "간헐적으로만 실패하고 실패/성공이 실행마다 뒤바뀜 → 테스트 간 공유 데이터/픽스처 충돌 의심.",
            "공유 테스트 데이터(예: 고정 유저 ID)를 테스트별 격리된 데이터로 교체.",
        )

    return result(
        "TEST_CODE_DEFECT", 0.4,
        "명확한 패턴이 감지되지 않아 규칙 기반으로는 확신도가 낮음.",
        "사람이 직접 스택트레이스와 최근 변경 이력을 확인 필요.",
    )


# ---------------------------------------------------------------------------
# LLM 기반 분류기
# ---------------------------------------------------------------------------
def build_prompt(failure: dict) -> str:
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    # 프롬프트 md 파일에서 ``` 코드블록 안의 템플릿 본문만 추출
    body = template.split("```\n", 1)[1].rsplit("\n```", 1)[0]
    history = failure.get("recent_history", [])

    # str.format()은 쓰지 않는다 — 템플릿 본문에 JSON 스키마 예시(`{ "category": ... }`)가
    # 그대로 포함되어 있어, format()이 그 중괄호까지 자리표시자로 오인해 깨진다.
    # 대신 `<<placeholder>>` 토큰을 단순 치환한다 (prompts/classify_prompt.md 참고).
    replacements = {
        "<<test_name>>": failure.get("test_name", ""),
        "<<test_code_snippet>>": failure.get("test_code_snippet", ""),
        "<<stack_trace>>": failure.get("stack_trace", ""),
        "<<history_length>>": str(len(history)),
        "<<recent_history>>": json.dumps(history),  # [true, false, ...] — 프롬프트 표기(true/false)와 일치
        "<<retry_passed>>": json.dumps(failure.get("retry_passed")),
    }
    for token, value in replacements.items():
        body = body.replace(token, value)
    return body


def classify_with_llm(failure: dict) -> Optional[TriageResult]:
    try:
        import anthropic  # type: ignore
    except ImportError:
        print("[warn] anthropic 패키지가 설치되어 있지 않아 규칙 기반으로 폴백합니다.", file=sys.stderr)
        return None

    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[warn] ANTHROPIC_API_KEY가 설정되지 않아 규칙 기반으로 폴백합니다.", file=sys.stderr)
        return None

    prompt = build_prompt(failure)
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # 모델이 코드펜스로 감싸 응답하는 경우를 대비한 방어적 파싱
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[1] if "\n" in text else text
        data = json.loads(text)
        return TriageResult(
            category=data["category"],
            confidence=float(data["confidence"]),
            evidence=data["evidence"],
            suggested_owner=data["suggested_owner"],
            suggested_fix=data["suggested_fix"],
            draft_comment=data["draft_comment"],
            source="llm",
        )
    except Exception as e:  # noqa: BLE001 — 데모 목적의 넓은 예외 처리, 실서비스에서는 세분화 필요
        print(f"[warn] LLM 응답 파싱 실패 ({e}), 규칙 기반으로 폴백합니다.", file=sys.stderr)
        return None


def triage(failure: dict, use_llm: bool) -> TriageResult:
    if use_llm:
        llm_result = classify_with_llm(failure)
        if llm_result is not None:
            return llm_result
    return rule_based_classify(failure)


def route(result: TriageResult) -> str:
    if result.confidence < CONFIDENCE_THRESHOLD:
        return "사람 확인 필요 (신뢰도 낮음, 자동 라우팅 보류)"
    return f"자동 라우팅 → {result.suggested_owner} 채널"


def main():
    parser = argparse.ArgumentParser(description="Flaky 테스트 실패 원인 자동 트리아지")
    parser.add_argument("input_json", type=Path, help="실패 레코드 목록 JSON 파일")
    parser.add_argument("--use-llm", action="store_true", help="Claude API로 분류 (키 없으면 자동 폴백)")
    parser.add_argument("--json-out", type=Path, help="결과를 JSON 파일로도 저장")
    args = parser.parse_args()

    failures = load_failures(args.input_json)
    results = []

    for failure in failures:
        result = triage(failure, use_llm=args.use_llm)
        results.append({"test_name": failure["test_name"], **asdict(result)})

        print("=" * 80)
        print(f"테스트           : {failure['test_name']}")
        print(f"분류 방식        : {result.source}")
        print(f"카테고리         : {result.category} (신뢰도 {result.confidence:.0%})")
        print(f"근거             : {result.evidence}")
        print(f"제안 조치        : {result.suggested_fix}")
        print(f"라우팅 결정      : {route(result)}")
        print(f"코멘트 초안      : {result.draft_comment}")

    print("=" * 80)
    print(f"총 {len(results)}건 처리 완료.")

    if args.json_out:
        args.json_out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"결과 저장: {args.json_out}")


if __name__ == "__main__":
    main()
