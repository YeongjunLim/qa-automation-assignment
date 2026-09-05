package com.baemin.qa.e2e.support

import androidx.test.uiautomator.By
import androidx.test.uiautomator.BySelector
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.Until
import java.util.concurrent.TimeoutException

/**
 * Thread.sleep()을 대체하는 명시적/폴링 기반 대기 유틸.
 *
 * 설계 의도
 *  - "요소가 존재한다"와 "요소를 조작할 수 있다"를 분리한다. 원본 코드는 findObject로 존재만
 *    확인하고 바로 click()을 호출했는데, 애니메이션 중이거나 아직 enabled=false인 시점에 클릭이
 *    씹히는 문제가 있었다. 여기서는 BySelector에 `.clickable(true)`를 명시해, "클릭 가능한 상태가
 *    될 때까지" 기다린 뒤 클릭한다.
 *  - 타임아웃 상수를 한 곳(Timeouts)에 모아, "CI가 느려서 전체적으로 여유를 둬야 한다" 같은 정책
 *    변경이 코드 전체에 흩어지지 않고 한 파일 수정으로 끝나게 한다.
 *  - 실패 시 어떤 셀렉터를 얼마나 기다렸는지 메시지에 남겨, 원인 추적(트리아지) 1단계인
 *    "무엇을 기다리다 실패했는가"를 로그만 보고 바로 알 수 있게 한다.
 */
object Timeouts {
    /** 화면 전환/렌더링 등 일반적인 UI 반응 대기 */
    const val UI_TRANSITION_MS = 5_000L

    /** 결제처럼 서버 왕복이 포함된 동작에 대한 대기. 원본의 고정 sleep(5000) 대신
     *  "최대 이만큼 기다리되, 끝나는 즉시 다음으로 진행"하는 상한선으로 사용한다. */
    const val PAYMENT_PROCESSING_MS = 10_000L

    /** 폴링 주기: findObject를 얼마 간격으로 재시도할지 */
    const val POLL_INTERVAL_MS = 200L
}

object UiWaitUtils {

    /** [selector]가 화면에 나타나고 클릭 가능한 상태가 될 때까지 기다린 뒤 UiObject2를 반환한다. */
    fun waitForClickable(device: UiDevice, selector: BySelector, timeoutMs: Long = Timeouts.UI_TRANSITION_MS): UiObject2 {
        val clickableSelector = selector.clickable(true)
        return device.wait(Until.findObject(clickableSelector), timeoutMs)
            ?: throw TimeoutException(
                "clickable element not found within ${timeoutMs}ms. selector=$selector " +
                    "(원인 추적: 팝업 오버레이가 떠 있거나, 화면 전환이 지연되었거나, 셀렉터가 더 이상 유효하지 않을 수 있음)"
            )
    }

    /** [selector]가 화면에 나타날 때까지 기다린다 (클릭 목적이 아닌 '존재/표시' 확인용). */
    fun waitForVisible(device: UiDevice, selector: BySelector, timeoutMs: Long = Timeouts.UI_TRANSITION_MS): UiObject2 {
        return device.wait(Until.findObject(selector), timeoutMs)
            ?: throw TimeoutException("element not visible within ${timeoutMs}ms. selector=$selector")
    }

    /**
     * '정확히 일치하는 텍스트'를 가진 요소가 나타날 때까지 기다린다.
     * 원본의 `textContains`는 부분 문자열이 우연히 다른 문구에 매치되는 위험이 있어,
     * 상태 값처럼 정확성이 중요한 검증에는 exact match(By.text)를 기본값으로 쓴다.
     */
    fun waitForExactText(device: UiDevice, exactText: String, timeoutMs: Long = Timeouts.UI_TRANSITION_MS): UiObject2 {
        return waitForVisible(device, By.text(exactText), timeoutMs)
    }

    /** [selector]가 화면에서 사라질 때까지 기다린다. (예: 로딩 스피너, 결제 처리중 오버레이) */
    fun waitForGone(device: UiDevice, selector: BySelector, timeoutMs: Long = Timeouts.PAYMENT_PROCESSING_MS): Boolean {
        return device.wait(Until.gone(selector), timeoutMs)
    }

    /**
     * 여러 셀렉터 중 '먼저 나타나는 것'을 폴링으로 찾는다.
     *
     * 원본 코드의 문제(3-2) — 결제 성공/실패를 구분하지 않고 무조건 성공 경로만 기다림 — 를
     * 해결하기 위한 헬퍼. 예: 결제 성공 지표와 에러 다이얼로그를 동시에 후보로 넘겨,
     * 어느 쪽이 먼저 뜨는지에 따라 분기 처리할 수 있게 한다.
     *
     * @return 매칭된 셀렉터의 index와 UiObject2. 타임아웃까지 아무것도 못 찾으면 예외.
     */
    fun waitForAny(device: UiDevice, timeoutMs: Long, vararg selectors: BySelector): Pair<Int, UiObject2> {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            selectors.forEachIndexed { index, selector ->
                device.findObject(selector)?.let { return index to it }
            }
            Thread.sleep(Timeouts.POLL_INTERVAL_MS)
        }
        throw TimeoutException(
            "none of the ${selectors.size} candidate selectors matched within ${timeoutMs}ms: ${selectors.toList()}"
        )
    }
}
