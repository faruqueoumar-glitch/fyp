package com.pharmaaudit.os

import android.annotation.SuppressLint
import android.os.Bundle
import android.text.TextUtils
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private val localUrl = "http://127.0.0.1:8765"

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.databaseEnabled = true
            settings.allowFileAccess = true
            webViewClient = WebViewClient()
            webChromeClient = WebChromeClient()
        }
        setContentView(webView)

        showHtml(
            "<h2>Starting PharmaAudit OS...</h2>" +
            "<p>Initializing local database and server. Please wait a few seconds.</p>"
        )

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack()
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })

        thread(start = true, isDaemon = true) {
            try {
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(applicationContext))
                }
                val py = Python.getInstance()
                py.getModule("android_boot").callAttr("start", filesDir.absolutePath)
            } catch (t: Throwable) {
                val trace = TextUtils.htmlEncode(t.stackTraceToString())
                runOnUiThread {
                    showHtml(
                        "<h2 style='color:#b91c1c'>PharmaAudit OS Startup Error</h2>" +
                        "<pre style='white-space:pre-wrap;font-size:12px;'>$trace</pre>"
                    )
                }
            }
        }

        thread(start = true, isDaemon = true) {
            if (waitForServer(localUrl)) {
                runOnUiThread {
                    webView.loadUrl(localUrl)
                }
            }
        }
    }

    private fun showHtml(body: String) {
        val html = "<html><body style='font-family:sans-serif;padding:24px;'>$body</body></html>"
        webView.loadDataWithBaseURL(null, html, "text/html", "utf-8", null)
    }

    private fun waitForServer(targetUrl: String, timeoutMs: Long = 35000L): Boolean {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            try {
                val conn = URL(targetUrl).openConnection() as HttpURLConnection
                conn.connectTimeout = 1000
                conn.readTimeout = 1000
                if (conn.responseCode < 500) {
                    conn.disconnect()
                    return true
                }
                conn.disconnect()
            } catch (_: Exception) {
                Thread.sleep(300)
            }
        }
        return false
    }
}
