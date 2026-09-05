package com.baemin.qa.e2e

import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import com.baemin.qa.e2e.pageobjects.BasePage.Companion.PACKAGE_NAME
import com.baemin.qa.e2e.pageobjects.HomePage
import com.baemin.qa.e2e.support.ScreenshotOnFailureRule
import org.junit.Before
import org.junit.Rule
import org.junit.Test

/**
 * 리팩토링된 주문 플로우 E2E 테스트.
 *
 * REVIEW.md에서 정리한 5가지 핵심 문제에 대응한 변경점
 *  1. Page Object로 화면별 책임 분리, 셀렉터를 각 클래스에 응집 (문제 1)
 *  2. 대기시간을 `Timeouts` 상수 하나로 통합 (문제 2)
 *  3. `Thread.sleep` 전면 제거 → 폴링 기반 명시적 대기 (문제 3)
 *  4. 이 함수의 Given/When/Then 주석으로 검증 시나리오를 명시 (문제 4)
 *  5. 상태 검증을 "존재 여부"가 아니라 "정확한 문구 + 실제 가시성"으로 강화 (문제 5)
 *
 * 추가로 반영한 방어적 장치 (핵심 5개 문제와는 별도 — REVIEW.md 하단 참고)
 *  - 클릭 가능한 상태까지 확인 후 클릭 (`waitForClickable`)
 *  - 결제 성공/실패 다이얼로그 분기 (`waitForAny`)
 *  - 실패 시 스크린샷/hierarchy 덤프 자동 수집 (`ScreenshotOnFailureRule`)
 *  - 사전 조건(홈 화면 진입)을 `@Before`에서 명시적으로 보장
 */
class OrderFlowTest {

    @get:Rule
    val screenshotOnFailureRule = ScreenshotOnFailureRule()

    private lateinit var device: UiDevice

    @Before
    fun launchAppToHomeScreen() {
        device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
        device.pressHome()
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val launchIntent = context.packageManager.getLaunchIntentForPackage(PACKAGE_NAME)
            ?: error("앱 launch intent를 찾을 수 없음: $PACKAGE_NAME (설치 여부 확인 필요)")
        context.startActivity(launchIntent)
        device.wait(androidx.test.uiautomator.Until.hasObject(androidx.test.uiautomator.By.pkg(PACKAGE_NAME).depth(0)), 5_000)
    }

    /**
     * Given 홈 화면에서 "치킨" 카테고리의 "후라이드" 메뉴를
     * When  주문하고 결제하면
     * Then  주문 상태가 "접수 대기"로 표시된다.
     *
     * TODO(테스트 데이터 정리 — 핵심 5개 문제에는 포함하지 않았으나 논의했던 사항, PROCESS.md 참고):
     * 이 테스트는 실제로 주문 1건을 생성한다.
     * 이상적으로는 테스트 서버 환경에 "테스트 계정 주문 자동 초기화" 배치가 있거나,
     * 백엔드에 테스트 전용 정리 API가 있어야 한다. 현재 UI만으로는 결제 완료된 주문을
     * 되돌릴 방법이 없으므로, 이 스위트는 반드시 격리된 테스트 계정/환경에서만 실행하고
     * 정기적으로 데이터를 리셋하는 것을 전제로 한다 (README에 명시).
     */
    @Test
    fun 치킨_후라이드_주문시_접수대기_상태로_전환된다() {
        val homePage = HomePage(device)

        val menuPage = homePage.selectCategory("치킨")
        val orderSummaryPage = menuPage.selectMenuItem("후라이드")
        val paymentPage = orderSummaryPage.clickOrder()
        val orderStatusPage = paymentPage.completePayment()

        orderStatusPage.assertStatus(expectedStatus = "접수 대기")
    }
}
