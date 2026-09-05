package com.baemin.qa.e2e.pageobjects

import android.util.Log
import androidx.test.uiautomator.UiDevice

/**
 * 모든 Page Object의 공통 베이스.
 *
 * - 화면 전환 시점을 로그로 남겨(step logging), 실패 시 "어느 화면 로직에서 멈췄는지"를
 *   스택트레이스만으로 특정할 수 있게 한다. (문제3 리뷰 2-3, Flaky 원인 추적 2단계 대응)
 * - 실제 앱의 resource-id 패키지명은 알 수 없으므로 `PACKAGE_NAME`에 가정값을 두고
 *   전체 Page Object가 이를 공유하도록 했다 — 실제 프로젝트에서는 BuildConfig 등에서 주입.
 */
abstract class BasePage(protected val device: UiDevice) {

    companion object {
        // 실제 배민 앱의 패키지/리소스 ID는 알 수 없어 합리적으로 가정한 값.
        // 실제 프로젝트에서는 앱의 실제 resource-id로 교체한다.
        const val PACKAGE_NAME = "com.sampleapp.baemin"
    }

    protected fun step(description: String) {
        Log.i(javaClass.simpleName, "STEP: $description")
    }
}
