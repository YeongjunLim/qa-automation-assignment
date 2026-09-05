# 우아한형제들 Senior QA Engineer (Test Automation Specialist) 사전과제

[![Problem2 Tests](https://github.com/YeongjunLim/woowahan-qa-assignment/actions/workflows/problem2-tests.yml/badge.svg)](https://github.com/YeongjunLim/woowahan-qa-assignment/actions/workflows/problem2-tests.yml)

문제2(B마트 재고 API)의 TC-01~TC-25는 GitHub Actions로 매 push마다 실제 실행됩니다. 위 배지를 클릭하면 최신 실행 결과(로그 포함)를 바로 확인할 수 있습니다.

## 폴더 구조

```
submission/
├── CLAUDE.md                           # 작업 메모리 — 4문제를 풀며 계속 지킨 원칙/결정 기록
├── README.md                           # (본 파일) 전체 개요, 실행 방법, AI 활용 내역
├── problem1-test-strategy/
│   ├── README.md                       # 문제1: 테스트 자동화 전략 설계 (서술, 최종 답변)
│   └── PROCESS.md                      # 사용자와 함께 풀어나간 과정
├── problem2-bmart-stock-api/          # 문제2: B마트 재고 API 테스트 자동화 (Python/Flask/pytest)
│   ├── README.md
│   ├── TEST_DESIGN.md                  # 테스트 설계기법(상태전이/경계값/동등분할/결정테이블)
│   ├── TEST_CASES.md                   # 테스트케이스 명세 (TC-01~TC-25)
│   ├── PROCESS.md
│   ├── requirements.txt
│   ├── src/mock_server.py
│   └── tests/
├── problem3-e2e-refactor/             # 문제3: E2E 코드 리뷰 및 리팩토링 (Kotlin/UIAutomator)
│   ├── README.md
│   ├── REVIEW.md
│   ├── PROCESS.md
│   └── src/
└── problem4-ai-qa-tool/               # 문제4: AI 기반 QA 자동화 도구 제안 + 프로토타입 (Python)
    ├── README.md
    ├── PROCESS.md
    └── prototype/
```

각 문제 폴더의 `README.md`는 **최종 산출물**(설계 의도·실행 방법)이고, `PROCESS.md`는 **지원자와 AI가
함께 문제를 풀어나간 논의 과정**을 담고 있습니다 — AI 활용 방식을 투명하게 보여드리기 위해 최종
결과물과 별도로 남겼습니다. 빠른 실행은 아래를 참고하세요.

## 빠른 실행

```bash
# 문제2: B마트 재고 API 자동화 테스트 (TC-01~TC-25, 25개 케이스, 전부 통과 확인됨)
cd problem2-bmart-stock-api
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest tests/ -v

# 문제4: Flaky Triage 프로토타입 (API 키 없이 규칙 기반으로 바로 실행 가능)
cd ../problem4-ai-qa-tool/prototype
python flaky_triage.py sample_failures.json
```

문제3은 Android Instrumentation 테스트(Kotlin + UIAutomator)로, 실제 앱/에뮬레이터 없이는 실행할 수 없어 **컴파일 가능한 완성된 소스** 형태로 제출했습니다. 자세한 내용은 [problem3-e2e-refactor/README.md](problem3-e2e-refactor/README.md) 참고.

## 문제별 요약

| 문제 | 형식 | 언어/도구 | 핵심 산출물 |
|---|---|---|---|
| 1. 테스트 자동화 전략 | 서술 | - | 자동화 범위 판단 기준, 테스트 피라미드 배분, ROI 기준, CI/CD 통합, Flaky 대응 정책 |
| 2. B마트 재고 API | 코드 | Python (Flask + pytest) | 상태전이·경계값·동등분할·결정테이블 4개 설계기법 기반 TC-01~TC-25(25개, 동시성 3개 포함), 전부 통과 |
| 3. E2E 리뷰/리팩토링 | 코드 | Kotlin (UIAutomator) | 핵심 문제 5개로 압축한 분석(REVIEW.md) + Page Object 기반 리팩토링 코드 |
| 4. AI 활용 QA 도구 | 코드+설계 | Python | "Flaky Triage Assistant" 설계 + 실행 가능한 프로토타입(규칙 기반 폴백 + LLM 모드) |

## AI 도구 활용 내역

이 과제 전체를 **Claude Code(Anthropic)** 를 사용해 작성했습니다. 투명하게 활용 방식을 밝힙니다.

- **과제 PDF 분석**: PDF 원문을 읽고 4개 문제의 요구사항, 특히 문제2의 '재고 처리 규칙' 표와 '동시성 시나리오'를 정리해 테스트 케이스 설계에 반영하는 데 활용했습니다.
- **코드 초안 작성**: 문제2의 Flask mock 서버·pytest 테스트, 문제3의 Kotlin Page Object 리팩토링, 문제4의 프로토타입 스크립트 초안을 Claude Code로 작성했습니다.
- **실행 검증**: 문제2 pytest 스위트(TC-01~TC-25, 25개 테스트 전부 통과)와 문제4 프로토타입 스크립트를 실제로 로컬에서 실행해 동작을 확인했습니다. 이 과정에서 프로토타입의 프롬프트 템플릿 치환 로직에 있던 버그(JSON 스키마 예시의 중괄호가 `str.format()`과 충돌)를 실행 테스트로 직접 발견하고 수정했습니다.
- **직접 판단하고 검증한 부분**: 테스트 자동화 범위/ROI 판단 기준(문제1), 동시성 테스트를 "타이밍 하드 어서션 vs 인위적 지연으로 결정적 재현" 두 가지로 분리한 설계(문제2), 원본 E2E 코드의 문제점 목록과 우선순위(문제3), AI 도구 아이디어 선정 이유(문제4)는 실제 취업 후 QA 업무에서 겪을 트레이드오프를 기준으로 직접 판단했습니다. AI는 초안 생성과 반복 작업(보일러플레이트 코드, 문서 포맷팅)의 속도를 높이는 데 사용했고, 모든 설계 판단과 최종 코드는 검토·수정했습니다.

## 제출자 참고사항

- 각 하위 폴더는 독립적으로 실행 가능하도록 구성했습니다 (`.venv`, `__pycache__` 등은 `.gitignore`로 제외).
- 문제 2, 4는 실제로 실행하여 결과를 확인했습니다. 문제 3은 Android 실행 환경이 없어 소스 코드 리뷰 수준으로 검증했습니다.
