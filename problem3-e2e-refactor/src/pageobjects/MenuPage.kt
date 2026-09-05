package com.baemin.qa.e2e.pageobjects

import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import com.baemin.qa.e2e.support.Timeouts
import com.baemin.qa.e2e.support.UiWaitUtils

/** 메뉴 목록 화면: 특정 카테고리의 상품 리스트. */
class MenuPage(device: UiDevice) : BasePage(device) {

    fun selectMenuItem(menuName: String): OrderSummaryPage {
        step("메뉴 선택: $menuName")
        val menuSelector = By.res(PACKAGE_NAME, "menu_item_name").text(menuName)
        val item = UiWaitUtils.waitForClickable(device, menuSelector, Timeouts.UI_TRANSITION_MS)
        item.click()
        return OrderSummaryPage(device)
    }
}
