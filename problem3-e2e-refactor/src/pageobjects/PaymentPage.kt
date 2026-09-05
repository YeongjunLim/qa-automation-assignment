package com.baemin.qa.e2e.pageobjects

import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import com.baemin.qa.e2e.support.Timeouts
import com.baemin.qa.e2e.support.UiWaitUtils

/** 결제 화면. */
class PaymentPage(device: UiDevice) : BasePage(device) {

    private val payButtonSelector = By.res(PACKAGE_NAME, "btn_pay")
    private val paymentErrorDialogSelector = By.res(PACKAGE_NAME, "dialog_payment_error")
    // 원본의 "접수 대기" 텍스트 자체는 다음 화면(OrderStatusPage) 소관이므로,
    // 여기서는 '결제 처리가 끝나고 다음 화면으로 넘어갔는지'만 얕게 확인하는 지표를 사용한다.
    private val orderStatusScreenAnchor = By.res(PACKAGE_NAME, "order_status_root")

    /**
     * 결제를 완료한다.
     *
     * 원본의 `Thread.sleep(5000)`을 제거하고, "결제 성공 화면"과 "결제 실패 다이얼로그" 중
     * 먼저 나타나는 쪽으로 분기한다 (리뷰 3-2 대응). 결제는 서버 왕복이 있어 처리 시간이
     * 매번 달라지므로, 고정 대기가 아니라 상한선(PAYMENT_PROCESSING_MS)까지 폴링한다.
     */
    fun completePayment(): OrderStatusPage {
        step("결제하기 클릭")
        val payBtn = UiWaitUtils.waitForClickable(device, payButtonSelector, Timeouts.UI_TRANSITION_MS)
        payBtn.click()

        step("결제 처리 결과 대기 (성공/실패 분기)")
        val (matchedIndex, matchedObject) = UiWaitUtils.waitForAny(
            device,
            Timeouts.PAYMENT_PROCESSING_MS,
            paymentErrorDialogSelector,
            orderStatusScreenAnchor,
        )

        if (matchedIndex == 0) {
            val errorMessage = matchedObject.text ?: "(알 수 없는 결제 오류)"
            error("결제 실패 다이얼로그가 노출됨: $errorMessage")
        }

        return OrderStatusPage(device)
    }
}
