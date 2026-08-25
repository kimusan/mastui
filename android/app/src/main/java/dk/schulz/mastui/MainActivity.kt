package dk.schulz.mastui

import android.annotation.SuppressLint
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.ProgressBar
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.net.ServerSocket
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private var serverPort: Int = 8000
    private var isServerStarted = false

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webview)
        progressBar = findViewById(R.id.progress_bar)

        setupWebView()
        setupBackHandler()

        startPythonServer()
    }

    private fun findAvailablePort(): Int {
        return try {
            val socket = ServerSocket(0)
            val port = socket.localPort
            socket.close()
            port
        } catch (e: Exception) {
            8000
        }
    }

    private fun startPythonServer() {
        if (isServerStarted) return
        isServerStarted = true

        serverPort = findAvailablePort()
        val filesDirPath = applicationContext.filesDir.absolutePath

        thread(name = "MastuiPythonServer") {
            try {
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(applicationContext))
                }
                val py = Python.getInstance()

                // Set writable home directory and terminal env for Python
                val osModule = py.getModule("os")
                val environ = osModule.get("environ")
                environ?.callAttr("__setitem__", "HOME", filesDirPath)
                environ?.callAttr("__setitem__", "TERM", "xterm-256color")
                environ?.callAttr("__setitem__", "COLORTERM", "truecolor")

                val webModule = py.getModule("mastui.web")
                webModule.callAttr(
                    "run_server",
                    "127.0.0.1",
                    serverPort,
                    false, // open_browser = false
                    arrayOf<String>()
                )
            } catch (e: Exception) {
                android.util.Log.e("Mastui", "Error in Python thread", e)
            }
        }

        // Poll for server readiness and load url
        thread {
            var ready = false
            for (i in 1..60) {
                Thread.sleep(250)
                try {
                    val s = java.net.Socket("127.0.0.1", serverPort)
                    s.close()
                    ready = true
                    android.util.Log.d("Mastui", "Connected to Python server on port $serverPort")
                    break
                } catch (ignored: Exception) {}
            }
            runOnUiThread {
                progressBar.visibility = View.GONE
                if (ready) {
                    webView.loadUrl("http://127.0.0.1:$serverPort")
                } else {
                    android.util.Log.e("Mastui", "Python server readiness timeout on port $serverPort")
                }
            }
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        WebView.setWebContentsDebuggingEnabled(true)
        val settings: WebSettings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        settings.setSupportZoom(false)
        settings.builtInZoomControls = false
        settings.displayZoomControls = false
        settings.cacheMode = WebSettings.LOAD_NO_CACHE

        webView.webChromeClient = object : WebChromeClient() {
            override fun onConsoleMessage(consoleMessage: android.webkit.ConsoleMessage?): Boolean {
                android.util.Log.d("MastuiWeb", "${consoleMessage?.message()} (line ${consoleMessage?.lineNumber()} of ${consoleMessage?.sourceId()})")
                return true
            }
        }
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                progressBar.visibility = View.GONE
            }

            override fun onReceivedError(
                view: WebView?,
                errorCode: Int,
                description: String?,
                failingUrl: String?
            ) {
                super.onReceivedError(view, errorCode, description, failingUrl)
                progressBar.visibility = View.GONE
            }
        }
    }

    private fun setupBackHandler() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                // Send 'Escape' key event to the Web Terminal
                val js = "(function(){ if (window.term) { window.term.onData('\\x1b'); } })();"
                webView.evaluateJavascript(js, null)
            }
        })
    }

    override fun onDestroy() {
        super.onDestroy()
        webView.destroy()
    }
}
