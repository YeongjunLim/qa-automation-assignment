# 문제3. E2E 자동화 코드 리뷰 및 리팩토링

- 문제점 분석: [REVIEW.md](REVIEW.md)
- 리팩토링 코드: [`src/`](src)

## 코드 구조

```
src/
  OrderFlowTest.kt                 # 리팩토링된 테스트 (Given/When/Then, Page Object 조합)
  pageobjects/
    BasePage.kt                    # 공통 로깅/상수
    HomePage.kt                    # 홈 → 카테고리 선택
    MenuPage.kt                    # 메뉴 목록 → 메뉴 선택
    OrderSummaryPage.kt            # 주문 확인 → "주문하기"
    PaymentPage.kt                 # 결제 → 성공/실패 분기
    OrderStatusPage.kt             # 상태 배지 검증
  support/
    UiWaitUtils.kt                 # Thread.sleep 대체용 폴링 대기 유틸
    ScreenshotOnFailureRule.kt     # 실패 시 스크린샷/hierarchy 자동 캡처
```

## 실행 환경에 대한 안내

이 코드는 UIAutomator2 + JUnit4 기반의 **Android Instrumentation 테스트**로, 실제로 실행하려면 Android SDK, 에뮬레이터/실기기, 그리고 배민 앱(또는 대상 앱)의 실제 `applicationId`와 View의 실제 `resource-id`가 필요하다. 과제 요구사항("실행 환경이 없어도 무방하며, 설계 의도가 드러나는 완성된 코드 형태면 충분")에 따라 **컴파일 가능한 완성된 소스 형태**로 제출하며, 실제 앱과 연결이 필요한 부분(패키지명, resource-id)은 코드 내 주석으로 가정임을 명시했다 (`BasePage.PACKAGE_NAME`, 각 Page Object의 `By.res(...)` 호출부).

실제 프로젝트에 적용한다면:
1. `PACKAGE_NAME`을 실제 앱 ID로 교체
2. 각 Page Object의 `resource-id` 문자열을 앱 실제 값으로 교체 (Android Studio Layout Inspector로 확인)
3. `build.gradle`에 `androidx.test.uiautomator:uiautomator`, `androidx.test:runner`, `junit:junit` 의존성 추가
4. `./gradlew connectedAndroidTest`로 실행

## 리팩토링 핵심 포인트 (요약)

REVIEW.md에서 확정한 **핵심 5개 문제**에 대응한 리팩토링:

| # | 원본 문제 | 리팩토링 |
|---|---|---|
| 1 | `textContains` 부분일치 셀렉터가 테스트 본문에 하드코딩 | Page Object로 화면별 책임 분리, 셀렉터를 각 클래스에 응집. `resource-id` 우선, 텍스트는 정확히 일치(`By.text`) |
| 2 | 매직 넘버(3000, 5000) 대기시간이 제각각 흩어짐 | `Timeouts` 상수 하나로 통합 |
| 3 | `Thread.sleep(5000)` 고정 대기 | `UiWaitUtils` 폴링 기반 대기, 상한선(timeout)까지만 대기하고 조건 충족 즉시 진행 |
| 4 | 어떤 요구사항을 검증하는지 알 수 있는 주석 없음 | 테스트 함수에 Given/When/Then 주석으로 시나리오 명시 |
| 5 | `assertNotNull`만으로 검증 | 정확한 문구 일치 + `isVisibleToUser` 확인 (`OrderStatusPage.assertStatus`) |

핵심 5개와는 별도로 논의했지만 "원본의 결함이라기보다 더 견고하게 만들 수 있는 지점"으로 분류해 목록엔 넣지 않은 것들도, 코드에는 방어적으로 반영했다 (근거는 [PROCESS.md](PROCESS.md)):

| 항목 | 반영 내용 |
|---|---|
| 존재 확인 후 즉시 클릭 | `.clickable(true)` 조건까지 만족해야 클릭 진행 (`waitForClickable`) |
| 결제 성공만 가정 | `waitForAny`로 성공/실패 다이얼로그를 동시에 후보로 두고 분기 |
| 실패 시 디버깅 정보 없음 | `ScreenshotOnFailureRule`로 실패 시 스크린샷 + view hierarchy 자동 저장 |
| 사전조건 암묵적 가정 | `@Before`에서 앱을 명시적으로 홈 화면까지 launch |
| 테스트 데이터 정리 없음 | 코드 내 TODO로 한계 명시 + "격리된 테스트 계정/환경 전제" 명시 |

## Flaky 원인 추적 절차

[REVIEW.md](REVIEW.md#이-테스트가-ci에서-간헐적으로-실패한다면flaky--원인-추적-순서) 참고.

## AI 도구 활용 내역
[최상위 README](../README.md#ai-도구-활용-내역)에 통합 기재.
