package com.baemin.qa.e2e.pageobjects

import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import com.baemin.qa.e2e.support.Timeouts
import com.baemin.qa.e2e.support.UiWaitUtils

/** 주문 확인(장바구니) 화면: "주문하기" 버튼이 있는 화면. */
class OrderSummaryPage(device: UiDevice) : BasePage(device) {

    private val orderButtonSelector = By.res(PACKAGE_NAME, "btn_place_order")

    fun clickOrder(): PaymentPage {
        step("주문하기 클릭")
        val orderBtn = UiWaitUtils.waitForClickable(device, orderButtonSelector, Timeouts.UI_TRANSITION_MS)
        orderBtn.click()
        return PaymentPage(device)
    }
}
