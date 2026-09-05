package com.baemin.qa.e2e.support

import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import org.junit.rules.TestWatcher
import org.junit.runner.Description
import java.io.File

/**
 * 실패 시 스크린샷 + 현재 화면의 view hierarchy 덤프를 남기는 JUnit Rule.
 *
 * 문제3 리뷰에서 지적한 "실패해도 디버깅 정보가 없다"를 해결한다.
 * CI 아티팩트로 이 폴더를 업로드해두면, Flaky 원인 추적 3단계("아티팩트 확인")를
 * 재현 없이 바로 수행할 수 있다.
 */
class ScreenshotOnFailureRule : TestWatcher() {

    private val device: UiDevice by lazy {
        UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
    }

    override fun failed(e: Throwable?, description: Description) {
        val outputDir = File(
            InstrumentationRegistry.getInstrumentation().targetContext.getExternalFilesDir(null),
            "e2e-failure-artifacts"
        ).apply { mkdirs() }

        val testName = "${description.className}.${description.methodName}"
        val screenshotFile = File(outputDir, "$testName.png")
        val hierarchyFile = File(outputDir, "$testName.uix")

        runCatching { device.takeScreenshot(screenshotFile) }
            .onFailure { Log.w("ScreenshotOnFailureRule", "screenshot capture failed", it) }

        runCatching { device.dumpWindowHierarchy(hierarchyFile) }
            .onFailure { Log.w("ScreenshotOnFailureRule", "hierarchy dump failed", it) }

        Log.e(
            "ScreenshotOnFailureRule",
            "[$testName] 실패. 아티팩트: ${screenshotFile.path}, ${hierarchyFile.path}. 원인: ${e?.message}"
        )
    }
}
