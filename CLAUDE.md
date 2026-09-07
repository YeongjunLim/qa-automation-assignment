# CLAUDE.md — 이 과제를 진행하며 계속 기억해야 할 것들

이 파일은 우아한형제들 Senior QA Engineer(Test Automation Specialist) 사전과제를 사용자와 함께
진행하면서, 세션이 바뀌거나 대화가 길어져도 잊으면 안 되는 맥락을 적어둔 작업 메모리다.
새로 이 작업을 이어받으면 이 파일을 먼저 읽는다.

## 과제 원본
- `../우아한형제들_QA_사전과제.pdf` — 문제1(서술) + 문제2~4(코드 필수)
- 제출 형식 요구사항(중요, 계속 지켜야 함):
  - GitHub/GitLab 저장소 링크 또는 압축파일로 제출
  - README에 **실행 방법, 설계 의도, 사용한 도구(AI 도구 포함)** 를 반드시 명시
  - AI 코딩 도구 사용은 허용되나 **어디에 어떻게 활용했는지 README에 기재 필수**

## 작업 방식 (2026-09-05, 사용자와 합의) — 가장 중요
- 사용자가 "문제 하나씩 같이 수행하자"고 요청함. **한 번에 4문제를 다 만들고 끝내는 방식이 아니라**,
  문제별로:
  1. Claude가 어떻게 풀었는지/왜 그렇게 설계했는지 사용자에게 설명
  2. 사용자와 논의, 필요하면 방향 수정
  3. 최종 결과는 각 문제 폴더의 `README.md`(제출용 최종 산출물)에
  4. **사용자와 함께 풀어나간 과정은 각 문제 폴더의 `PROCESS.md`에 별도로 기록** — README와 섞지 않는다
- `CLAUDE.md`와 각 `PROCESS.md`는 **제출물에도 포함**하기로 사용자와 합의함 (내부 기록이 아니라
  "AI와 어떻게 협업해 문제를 풀었는지"를 투명하게 보여주는 것 자체가 AI 활용 역량 평가에 도움이 된다고 판단).
  → git에 커밋 대상, `.gitignore`로 제외하지 않는다.

## 언어/도구 선택 (이미 확정, 재논의 불필요)
- 문제2, 4: Python (Flask + pytest) — mock 서버의 동시성 lock 구현/검증에 적합해서 선택
- 문제3: Kotlin 유지 — 원본 코드가 Kotlin + UIAutomator라서 언어를 바꾸지 않음

## 검증 원칙 (중요 — 코드 문제는 반드시 실제 실행 확인)
- 문제2: pytest TC-01~TC-25(25개 케이스, 블랙박스 설계기법 4종 기반), 실제 로컬 실행으로 전부 통과
  확인 완료 (`.venv`는 매번 재생성 후 삭제, git에는 포함하지 않음 — `.gitignore` 참고)
- 문제4: 최종 아이디어는 "테스트케이스 자산화 플랫폼(TestLedger)" — 1단계(실패 분류, `flaky_triage.py`)는
  실제 실행 검증 완료(실행 중 `str.format()`/JSON스키마 중괄호 충돌 버그 발견·수정). 2단계(TC
  설계·작성, Generator/Critic)는 실제 Claude Code sub-agent를 2라운드 호출해 검증(`.claude/agents/
  tc-generator.md`, `tc-critic.md`, 원본 기록은 `problem4-ai-qa-tool/prototype/subagent_demo_coupon.md`).
  **커스텀 sub-agent 타입이 세션 재시작 전엔 인식되지 않는다는 실제 제약을 발견**해 `general-purpose`
  로 우회 실행 — 이 한계를 정직하게 문서화함. 3단계(수정 코드 제안, 서비스 등록/자산관리)는 실제 동작
  코드 없이 설계 + `testledger.html` UI 목업으로만 표현하기로 사용자와 합의(2026-09-05).
- 문제3: Android 실행 환경(SDK/에뮬레이터)이 없어 실제 실행은 불가 — README에 이 한계를 명시했고,
  "컴파일 가능한 완성된 소스" 수준으로 검증함 (요구사항이 이를 허용: "실행 환경이 없어도 무방").

## 각 문제 진행 상태

| 문제 | 산출물(README/코드) | 사용자와 논의(PROCESS.md) |
|---|---|---|
| 1. 테스트 자동화 전략 | 완료 | 완료 (2026-09-05) |
| 2. B마트 재고 API | 완료, TC-01~TC-25(25개) 테스트 통과 확인 | 완료 (2026-09-05) — 설계기법 4종(상태전이/경계값/동등분할/결정테이블) 적용 |
| 3. E2E 리뷰/리팩토링 | 완료, 핵심 문제 5개로 압축 확정 | 완료 (2026-09-05) |
| 4. AI 활용 QA 도구 | 완료 — 아이디어가 6번 바뀐 끝에 "테스트케이스 자산화 플랫폼"으로 수렴, TestLedger 목업 발행 | 완료 (2026-09-05) |

## GitHub 저장소 (2026-09-05 확정, push는 4문제 완료 후로 보류)
- 계정: `YeongjunLim`, 저장소명: `qa-automation-assignment`, **Public**
- 이 머신엔 `gh` CLI가 없어 저장소는 사용자가 GitHub 웹에서 직접 생성(빈 저장소, README/gitignore 미초기화) → Claude가 `git push` (Git Credential Manager가 브라우저 로그인 팝업 처리)
- **사용자가 "저장소 생성은 4문제 다 끝나고 하자"고 결정함 (2026-09-05)** — 지금 당장 저장소 생성/push를 재촉하지 말 것. 로컬에는 이미 CI 워크플로우까지 커밋되어 있어 push만 하면 되는 상태.
- GitHub Actions는 **문제2(pytest TC-01~TC-25)만** 대상 — `.github/workflows/problem2-tests.yml`, `problem2-bmart-stock-api/**` 변경 시에만 트리거
- 문제4 프로토타입(`flaky_triage.py`, `testledger.html`)은 "테스트 스위트가 아니라 데모/목업"이라는 이유로 CI 스모크테스트 추가하지 않기로 사용자와 확정
- 문제1(서술)·문제3(Kotlin/Android, 에뮬레이터 필요)은 CI 대상 아님
- README 상단에 Actions 배지 추가 완료 (최상위 README.md, problem2 README.md)

## 파일 구조 참고
```
submission/
├── CLAUDE.md                 # 이 파일
├── README.md                 # 전체 개요 (회사 제출용)
├── .claude/agents/{tc-generator.md, tc-critic.md}   # 문제4 sub-agent 정의 (실제 호출됨)
├── .github/workflows/{problem2-tests.yml}
├── problem1-test-strategy/{README.md, PROCESS.md}
├── problem2-bmart-stock-api/{README.md, TEST_DESIGN.md, TEST_CASES.md, PROCESS.md, requirements.txt, src/, tests/}
├── problem3-e2e-refactor/{README.md, REVIEW.md, PROCESS.md, src/}
└── problem4-ai-qa-tool/{README.md, PROCESS.md, prototype/{flaky_triage.py, testledger.html, subagent_demo_coupon.md, ...}}
```
