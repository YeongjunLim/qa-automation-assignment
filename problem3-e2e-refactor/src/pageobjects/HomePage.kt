package com.baemin.qa.e2e.pageobjects

import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import com.baemin.qa.e2e.support.Timeouts
import com.baemin.qa.e2e.support.UiWaitUtils

/** 홈 화면: 카테고리 목록이 노출되는 진입 화면. */
class HomePage(device: UiDevice) : BasePage(device) {

    /**
     * 카테고리를 선택해 메뉴 목록 화면으로 이동한다.
     *
     * resource-id를 우선 사용하고(문제3 리뷰 1-2 대응), 텍스트 매칭이 꼭 필요하다면
     * `textContains` 대신 정확히 일치하는 `text`를 사용해 프로모션 배너 등 다른 요소와의
     * 오매칭을 방지한다.
     */
    fun selectCategory(categoryName: String): MenuPage {
        step("카테고리 선택: $categoryName")
        val categorySelector = By.res(PACKAGE_NAME, "category_item").hasDescendant(By.text(categoryName))
        val item = UiWaitUtils.waitForClickable(device, categorySelector, Timeouts.UI_TRANSITION_MS)
        item.click()
        return MenuPage(device)
    }
}
