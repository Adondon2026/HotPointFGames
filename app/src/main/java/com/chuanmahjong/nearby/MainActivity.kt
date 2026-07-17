package com.chuanmahjong.nearby

import android.Manifest
import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {
    private lateinit var statusText: TextView
    private lateinit var hintText: TextView
    private lateinit var addressText: TextView
    private lateinit var addressSpinner: Spinner
    private lateinit var qrImage: ImageView
    private lateinit var startStopButton: Button
    private lateinit var enterButton: Button
    private lateinit var copyButton: Button
    private lateinit var shareButton: Button

    private val handler = Handler(Looper.getMainLooper())
    private var currentUrls: List<String> = emptyList()
    private var selectedUrl: String? = null
    private var lastQrUrl: String? = null

    private val refreshTask = object : Runnable {
        override fun run() {
            refreshUi()
            handler.postDelayed(this, 1500)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        requestNotificationPermissionIfNeeded()

        val state = ServerPrefs.read(this)
        if (state.desired) {
            GameServerService.start(this)
        }
    }

    override fun onResume() {
        super.onResume()
        handler.removeCallbacks(refreshTask)
        handler.post(refreshTask)
    }

    override fun onPause() {
        handler.removeCallbacks(refreshTask)
        super.onPause()
    }

    private fun buildUi() {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(22), dp(26), dp(22), dp(30))
            setBackgroundColor(Color.rgb(255, 248, 241))
        }

        content.addView(TextView(this).apply {
            text = "热点游戏厅"
            textSize = 30f
            setTextColor(Color.rgb(90, 20, 16))
            gravity = Gravity.CENTER
            typeface = android.graphics.Typeface.DEFAULT_BOLD
        }, matchWrap(bottom = 8))

        content.addView(TextView(this).apply {
            text = "手动打开手机热点，然后启动服务器。朋友连接热点后扫码进入。"
            textSize = 16f
            setTextColor(Color.DKGRAY)
            gravity = Gravity.CENTER
        }, matchWrap(bottom = 18))

        statusText = TextView(this).apply {
            textSize = 20f
            gravity = Gravity.CENTER
            setPadding(dp(12), dp(12), dp(12), dp(12))
        }
        content.addView(statusText, matchWrap(bottom = 6))

        hintText = TextView(this).apply {
            textSize = 14f
            gravity = Gravity.CENTER
            setTextColor(Color.DKGRAY)
        }
        content.addView(hintText, matchWrap(bottom = 14))

        startStopButton = Button(this).apply {
            textSize = 18f
            setOnClickListener {
                val state = ServerPrefs.read(this@MainActivity)
                if (state.running || state.desired) {
                    GameServerService.stop(this@MainActivity)
                } else {
                    GameServerService.start(this@MainActivity)
                }
                refreshUi()
            }
        }
        content.addView(startStopButton, matchWrap(bottom = 14))

        qrImage = ImageView(this).apply {
            adjustViewBounds = true
            contentDescription = "朋友访问地址二维码"
            visibility = View.GONE
        }
        content.addView(qrImage, LinearLayout.LayoutParams(dp(280), dp(280)).apply {
            gravity = Gravity.CENTER_HORIZONTAL
            bottomMargin = dp(10)
        })

        addressText = TextView(this).apply {
            textSize = 17f
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(70, 30, 25))
            setTextIsSelectable(true)
        }
        content.addView(addressText, matchWrap(bottom = 6))

        addressSpinner = Spinner(this).apply {
            visibility = View.GONE
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    if (position in currentUrls.indices) {
                        selectedUrl = currentUrls[position]
                        showSelectedUrl()
                    }
                }

                override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            }
        }
        content.addView(addressSpinner, matchWrap(bottom = 8))

        val shareRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        copyButton = Button(this).apply {
            text = "复制地址"
            setOnClickListener { copyAddress() }
        }
        shareButton = Button(this).apply {
            text = "分享地址"
            setOnClickListener { shareAddress() }
        }
        shareRow.addView(copyButton, LinearLayout.LayoutParams(0, dp(52), 1f).apply { marginEnd = dp(5) })
        shareRow.addView(shareButton, LinearLayout.LayoutParams(0, dp(52), 1f).apply { marginStart = dp(5) })
        content.addView(shareRow, matchWrap(bottom = 10))

        enterButton = Button(this).apply {
            text = "房主进入游戏"
            textSize = 18f
            setOnClickListener {
                val state = ServerPrefs.read(this@MainActivity)
                if (state.running) {
                    startActivity(Intent(this@MainActivity, GameActivity::class.java).putExtra("port", state.port))
                }
            }
        }
        content.addView(enterButton, matchWrap())

        setContentView(ScrollView(this).apply {
            isFillViewport = true
            addView(content)
        })
    }

    private fun refreshUi() {
        val state = ServerPrefs.read(this)
        when {
            state.running -> {
                statusText.text = "● 服务器运行中"
                statusText.setTextColor(Color.rgb(22, 110, 55))
                hintText.text = "可以锁屏或切到其他应用；请保留“游戏服务器”通知。"
                startStopButton.text = "停止服务器"
                startStopButton.isEnabled = true
            }
            state.desired -> {
                statusText.text = "正在启动服务器…"
                statusText.setTextColor(Color.rgb(160, 90, 0))
                hintText.text = "首次启动需要加载内置 Python，请稍候。"
                startStopButton.text = "正在启动…"
                startStopButton.isEnabled = false
            }
            state.error.isNotBlank() -> {
                statusText.text = "服务器未启动"
                statusText.setTextColor(Color.rgb(180, 35, 30))
                hintText.text = state.error
                startStopButton.text = "重新启动"
                startStopButton.isEnabled = true
            }
            else -> {
                statusText.text = "服务器未启动"
                statusText.setTextColor(Color.DKGRAY)
                hintText.text = "请先在系统设置中打开热点。"
                startStopButton.text = "启动游戏厅"
                startStopButton.isEnabled = true
            }
        }

        enterButton.isEnabled = state.running
        updateAddresses(state)
    }

    private fun updateAddresses(state: ServerPrefs.Snapshot) {
        if (!state.running) {
            currentUrls = emptyList()
            selectedUrl = null
            lastQrUrl = null
            qrImage.visibility = View.GONE
            addressSpinner.visibility = View.GONE
            addressText.text = "启动后将在这里显示扫码地址"
            copyButton.isEnabled = false
            shareButton.isEnabled = false
            return
        }

        val candidates = NetworkUtils.localIpv4Candidates()
        val newUrls = candidates.map { "http://${it.address}:${state.port}/" }
        if (newUrls != currentUrls) {
            val previous = selectedUrl
            currentUrls = newUrls
            selectedUrl = previous?.takeIf { it in newUrls } ?: newUrls.firstOrNull()
            addressSpinner.adapter = ArrayAdapter(
                this,
                android.R.layout.simple_spinner_dropdown_item,
                candidates.map { "${it.address}（${it.interfaceName}）" },
            )
            addressSpinner.visibility = if (newUrls.size > 1) View.VISIBLE else View.GONE
            val selectedIndex = newUrls.indexOf(selectedUrl).coerceAtLeast(0)
            if (newUrls.isNotEmpty()) addressSpinner.setSelection(selectedIndex)
        }

        if (newUrls.isEmpty()) {
            selectedUrl = null
            qrImage.visibility = View.GONE
            addressSpinner.visibility = View.GONE
            addressText.text = "服务器已运行，但未检测到热点地址\n请确认手机热点已经开启"
            hintText.text = "打开热点后，此页面会自动刷新地址。"
            copyButton.isEnabled = false
            shareButton.isEnabled = false
        } else {
            showSelectedUrl()
        }
    }

    private fun showSelectedUrl() {
        val url = selectedUrl ?: return
        addressText.text = url
        copyButton.isEnabled = true
        shareButton.isEnabled = true
        if (lastQrUrl != url) {
            qrImage.setImageBitmap(QrCode.create(url, 720))
            qrImage.visibility = View.VISIBLE
            lastQrUrl = url
        }
    }

    private fun copyAddress() {
        val url = selectedUrl ?: return
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("热点游戏厅地址", url))
        Toast.makeText(this, "地址已复制", Toast.LENGTH_SHORT).show()
    }

    private fun shareAddress() {
        val url = selectedUrl ?: return
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, "连接我的手机热点后打开热点游戏厅：$url")
        }
        startActivity(Intent.createChooser(intent, "分享游戏地址"))
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 33)
        }
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun matchWrap(bottom: Int = 0): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            bottomMargin = dp(bottom)
        }
}
