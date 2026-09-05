package com.baemin.qa.e2e.pageobjects

import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import com.baemin.qa.e2e.support.Timeouts
import com.baemin.qa.e2e.support.UiWaitUtils

/** 주문 상태(실시간 주문 현황) 화면. */
class OrderStatusPage(device: UiDevice) : BasePage(device) {

    private val statusBadgeSelector = By.res(PACKAGE_NAME, "text_order_status")

    /**
     * 주문 상태 배지의 텍스트가 [expectedStatus]와 **정확히 일치**하고, 실제로 화면에
     * 보이는 상태(isVisibleToUser)인지까지 확인한다.
     *
     * 원본의 `Assert.assertNotNull(statusText)`는 "textContains로 뭔가를 찾았다"만 증명할 뿐,
     * 그게 진짜 주문 상태 배지인지/정확한 문구인지는 증명하지 못했다 (리뷰 3-1 대응).
     */
    fun assertStatus(expectedStatus: String) {
        step("주문 상태 확인: 기대값=$expectedStatus")
        val badge = UiWaitUtils.waitForVisible(device, statusBadgeSelector, Timeouts.UI_TRANSITION_MS)

        check(badge.isVisibleToUser) { "상태 배지가 화면상에서 실제로 보이지 않음 (다른 뷰에 가려졌을 가능성)" }
        check(badge.text == expectedStatus) {
            "주문 상태 불일치. 기대: '$expectedStatus', 실제: '${badge.text}'"
        }
    }
}
