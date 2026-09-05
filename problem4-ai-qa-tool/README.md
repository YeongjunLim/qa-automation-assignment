# 문제4. AI 생성 코드 검증 자동화 — 제안: Flaky 테스트 실패 원인 자동 트리아지 어시스턴트

## 왜 이 아이디어인가

문제1(Flaky 대응 정책)과 문제3(간헐적 실패 원인 추적)에서 공통적으로 등장한 병목은 **"실패했을 때 원인을 사람이 매번 처음부터 눈으로 분류해야 한다"**는 점이다. 로그, 스크린샷, 최근 이력을 사람이 매번 훑어보는 1차 분류(triage) 작업은 반복적이고 패턴화되어 있어 LLM이 가장 잘 도와줄 수 있는 영역이라 판단했다. 그래서 "기획서 기반 TC 자동 생성"이나 "Self-healing 셀렉터"보다, **QA 조직이 매일 실제로 반복하는 고통(Flaky 원인 분류)을 줄이는 도구**를 제안한다.

## 도구 개요: Flaky Triage Assistant

CI에서 테스트가 실패하면, 실패 로그·스택트레이스·최근 N회 pass/fail 이력·재시도 결과를 모아 LLM에 넘기고, "환경 이슈 / 타이밍 이슈 / 테스트 코드 결함 / 데이터 이슈 / 실제 제품 버그" 중 하나로 분류 + 신뢰도 + 근거 + 제안 조치 + 초안 코멘트를 자동 생성한다. **최종 판단과 게시는 항상 사람이 확인** — 오탐이 프로세스를 오염시키는 것을 막기 위해 완전 자동화가 아니라 "1차 분류를 대신 해주는 어시스턴트"로 설계했다.

## 동작 구조

```
 ① CI 실패 발생 (GitHub Actions / Jenkins)
        │  webhook
        ▼
 ② 수집기 (Collector)
    - 실패 로그, 스택트레이스, 스크린샷 경로, 테스트 코드 스니펫 수집
    - 테스트 이력 DB에서 "최근 N회 pass/fail" 조회
    - 재시도(retry) 결과 포함 여부 확인
        │
        ▼
 ③ 정규화 (Normalizer)
    - 노이즈 제거(타임스탬프/컨테이너ID 등), 스택트레이스 상위 K줄만 추출
    - 위 정보를 고정 스키마의 JSON으로 통일 (LLM 입력 표준화)
        │
        ▼
 ④ 분류기 (Classifier) — LLM 호출
    - prompts/classify_prompt.md 템플릿에 정규화된 데이터를 채워 프롬프트 구성
    - 출력: {category, confidence, evidence, suggested_owner, suggested_fix, draft_comment}
    - (신뢰도가 낮거나 API 미가용 시 규칙 기반 폴백 분류기로 대체 — prototype 참고)
        │
        ▼
 ⑤ 라우터 (Router)
    - REAL_BUG/DATA_ISSUE → 개발팀 채널 + 티켓 초안
    - TIMING_ISSUE/TEST_CODE_DEFECT → QA 채널, 테스트 코드 수정 후보로 표시
    - ENV_ISSUE → 인프라/DevOps 채널
    - confidence < 임계값 → "사람 확인 필요" 큐로 (자동 라우팅 보류)
        │
        ▼
 ⑥ 리포터 (Reporter)
    - Slack/Jira에 "초안" 코멘트 게시 (사람이 검토 후 확정 — human-in-the-loop)
        │
        ▼
 ⑦ 피드백 루프 (Feedback loop)
    - 사람이 분류를 확정/정정하면 그 결과를 라벨링 데이터로 누적
    - 누적 데이터는 향후 few-shot 예시 강화, quarantine 자동화 규칙 튜닝에 사용
```

## 신뢰성 확보 방안 (환각/오탐 대응)

- **출력 스키마 고정 + 구조화 파싱**: LLM 응답을 JSON 스키마로 강제하고, 파싱 실패나 필수 필드 누락 시 규칙 기반 폴백으로 전환한다.
- **근거(evidence) 필수화**: 분류 카테고리만이 아니라 "어떤 로그 라인/이력 패턴을 근거로 판단했는지"를 함께 출력하게 해, 사람이 근거를 보고 바로 신뢰 여부를 판단할 수 있게 한다.
- **자동 게시 금지**: 코멘트는 항상 "초안"이며, 실제 게시/티켓 생성은 사람이 승인해야 한다.
- **신뢰도 낮으면 보수적으로**: confidence가 임계값 미만이면 카테고리를 확정하지 않고 "사람 확인 필요"로만 표시한다.
- **비용/속도 고려**: 모든 실패에 즉시 LLM을 호출하지 않고, quarantine 후보(최근 재발 빈도가 임계치를 넘은 테스트)부터 우선 처리하는 배치 방식도 병행할 수 있게 설계한다.

## 프로토타입

`prototype/flaky_triage.py` — 실행 가능한 데모.

```bash
cd problem4-ai-qa-tool/prototype
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# ANTHROPIC_API_KEY가 없으면 규칙 기반 폴백 분류기로 동작 (키 없이도 실행 가능)
python flaky_triage.py sample_failures.json

# 실제 LLM 분류를 사용하려면:
export ANTHROPIC_API_KEY=sk-...       # Windows: $env:ANTHROPIC_API_KEY="sk-..."
python flaky_triage.py sample_failures.json --use-llm
```

`sample_failures.json`에는 이번 과제의 문제2(B마트 동시성)·문제3(E2E Thread.sleep) 시나리오에서 있을 법한 실패 사례를 넣어, 과제 전체가 하나의 이야기로 이어지도록 구성했다.

프롬프트 설계는 [`prototype/prompts/classify_prompt.md`](prototype/prompts/classify_prompt.md) 참고.

## AI 도구 활용 내역
[최상위 README](../README.md#ai-도구-활용-내역)에 통합 기재.
