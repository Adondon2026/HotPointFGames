package com.chuanmahjong.nearby

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.view.WindowManager
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import org.json.JSONObject

class GameActivity : Activity() {
    private lateinit var webView: WebView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val port = intent.getIntExtra("port", 8000)
        val bootstrap = "http://127.0.0.1:$port/__android_account"
        val token = CloudAccounts.localToken().orEmpty()
        webView = WebView(this).apply {
            setBackgroundColor(Color.rgb(255, 248, 241))
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            webChromeClient = WebChromeClient()
            webViewClient = object : WebViewClient() {
                override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                    if (!request.isForMainFrame || request.url.toString() != bootstrap) return null
                    val page = """
                        <!doctype html><meta charset="utf-8"><script>
                        const token = ${JSONObject.quote(token)};
                        if (token !== (localStorage.getItem('gh_account_token') || '')) {
                            for (const key of Object.keys(localStorage)) {
                                if (key.startsWith('gh_token') || key.startsWith('gh_player_id') || key.startsWith('gh_room_claim')) {
                                    localStorage.removeItem(key);
                                }
                            }
                            if (token) localStorage.setItem('gh_account_token', token);
                            else localStorage.removeItem('gh_account_token');
                        }
                        location.replace('/');
                        </script>
                    """.trimIndent()
                    return WebResourceResponse("text/html", "utf-8", page.byteInputStream())
                }

                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    val host = request.url.host.orEmpty()
                    return host != "127.0.0.1" && host != "localhost"
                }

                override fun onReceivedError(
                    view: WebView,
                    request: WebResourceRequest,
                    error: android.webkit.WebResourceError,
                ) {
                    if (request.isForMainFrame) {
                        Toast.makeText(this@GameActivity, "游戏页面暂时无法连接，请返回后重试", Toast.LENGTH_LONG).show()
                    }
                }
            }
            loadUrl(bootstrap)
        }
        setContentView(webView)
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }

    override fun onDestroy() {
        webView.stopLoading()
        webView.destroy()
        super.onDestroy()
    }
}
