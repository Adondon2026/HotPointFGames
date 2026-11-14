package com.chuanmahjong.nearby

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
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
import android.os.Process
import android.net.Uri
import com.chaquo.python.Python
import org.json.JSONObject
import java.io.File
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
    private lateinit var gameSourceText: TextView
    private lateinit var importButton: Button
    private lateinit var restoreButton: Button
    private var importing = false
    private lateinit var updateButton: Button
    private lateinit var updateStatus: TextView
    private var checkingUpdate = false
    private var availableUpdate: GameUpdates.Available? = null
    private var versionLabel = ""
    private var updateMessage = "检查更新需要联网，联机游戏可离线"

    companion object {
        private const val PICK_GAME = 6201
        private const val MAX_GAME_BYTES = 4 * 1024 * 1024
    }

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
        checkUpdates(false)

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
            text = "热点游戏厅 · ZMZ v1.4.0"
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
        content.addView(enterButton, matchWrap(bottom = 18))

        gameSourceText = TextView(this).apply {
            textSize = 13f
            setTextColor(Color.DKGRAY)
            gravity = Gravity.CENTER
        }
        content.addView(gameSourceText, matchWrap(bottom = 6))

        updateStatus = TextView(this).apply {
            textSize = 13f
            gravity = Gravity.CENTER
            setTextColor(Color.DKGRAY)
        }
        content.addView(updateStatus, matchWrap(bottom = 4))
        updateButton = Button(this).apply {
            text = "检查更新"
            setOnClickListener {
                val update = availableUpdate
                if (update == null) checkUpdates(true) else confirmUpdate(update)
            }
        }
        content.addView(updateButton, matchWrap(bottom = 10))

        importButton = Button(this).apply {
            text = "导入新版游戏文件"
            setOnClickListener { chooseGameFile() }
        }
        content.addView(importButton, matchWrap(bottom = 6))

        restoreButton = Button(this).apply {
            text = "恢复内置游戏"
            setOnClickListener {
                AlertDialog.Builder(this@MainActivity)
                    .setTitle("恢复内置游戏？")
                    .setMessage("保留游戏存档，移除导入的版本。完成后需重新打开 APP。")
                    .setNegativeButton("取消", null)
                    .setPositiveButton("恢复") { _, _ -> changeGame(null) }
                    .show()
            }
        }
        content.addView(restoreButton, matchWrap())

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
                hintText.text = state.error.ifBlank { "可以锁屏或切到其他应用；请保留“游戏服务器”通知。" }
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
        val stopped = !state.running && !state.desired && !importing
        val imported = File(filesDir, "gamehall_import.py").isFile
        gameSourceText.text = "游戏版本：" + versionLabel.ifBlank { if (imported) "本地导入版" else "APP 内置版" }
        updateStatus.text = updateMessage
        updateButton.text = when {
            importing -> "正在更新…"
            checkingUpdate -> "正在检查…"
            availableUpdate != null -> "下载并更新"
            else -> "检查更新"
        }
        updateButton.isEnabled = !checkingUpdate && !importing
        importButton.isEnabled = stopped
        restoreButton.visibility = if (imported) View.VISIBLE else View.GONE
        restoreButton.isEnabled = stopped
        if (importing) startStopButton.isEnabled = false
        updateAddresses(state)
    }

    private fun checkUpdates(manual: Boolean) {
        if (checkingUpdate || importing) return
        checkingUpdate = true
        updateMessage = "正在检查 ZMZ 专属游戏更新…"
        refreshUi()
        Thread {
            var found: GameUpdates.Available? = null
            var message: String
            var label = ""
            try {
                label = GameUpdates.current(this)?.version.orEmpty()
                found = GameUpdates.check(this)
                message = if (found == null) "未发现可用更新" else "发现新版本：${found.info.version}"
            } catch (e: Exception) {
                message = if (manual) "检查失败：${e.message.orEmpty()}" else "暂时无法联网检查，可离线游戏"
            }
            runOnUiThread {
                if (isFinishing || isDestroyed) return@runOnUiThread
                checkingUpdate = false
                availableUpdate = found
                versionLabel = label
                updateMessage = message
                refreshUi()
            }
        }.start()
    }

    private fun confirmUpdate(update: GameUpdates.Available) {
        val state = ServerPrefs.read(this)
        if (state.running || state.desired) {
            AlertDialog.Builder(this).setTitle("请先停止游戏厅")
                .setMessage("更新不会自动结束正在进行的游戏。请在所有房间结束后停止服务器，再点击下载并更新。")
                .setPositiveButton("知道了", null).show()
            return
        }
        AlertDialog.Builder(this).setTitle("更新游戏")
            .setMessage("版本：${update.info.version}\n大小：${(update.info.size + 1023) / 1024} KB\n\n${update.notes}\n\n保留账户和积分；更新后需重新打开 APP。")
            .setNegativeButton("取消", null)
            .setPositiveButton("更新") { _, _ -> installUpdate(update) }.show()
    }

    private fun installUpdate(update: GameUpdates.Available) {
        val state = ServerPrefs.read(this)
        if (state.running || state.desired || importing) return
        importing = true
        updateMessage = "正在下载并校验新版…"
        refreshUi()
        Thread {
            val pending = File(filesDir, "gamehall_import.pending")
            var error: String? = null
            try {
                GameUpdates.download(update, pending)
                val raw = Python.getInstance().getModule("android_bridge").callAttr("install_game", filesDir.absolutePath).toJava(String::class.java)
                val result = JSONObject(raw)
                require(result.optBoolean("ok")) { result.optString("error", "安装失败") }
                // Version metadata is advisory: an installed file is always identified by its actual hash.
                runCatching { GameUpdates.record(this, update.info) }
            } catch (e: Throwable) {
                error = e.message ?: "更新失败"
            } finally { pending.delete() }
            runOnUiThread {
                if (isFinishing || isDestroyed) return@runOnUiThread
                if (error != null) {
                    importing = false
                    updateMessage = "更新失败，原版本未更换"
                    refreshUi()
                    AlertDialog.Builder(this).setTitle("更新失败").setMessage(error)
                        .setPositiveButton("知道了", null).show()
                } else {
                    updateMessage = "已更新，重新打开 APP 后生效"
                    refreshUi()
                    AlertDialog.Builder(this).setTitle("更新完成")
                        .setMessage("APP 将关闭。重新打开即可使用新版游戏。")
                        .setCancelable(false)
                        .setPositiveButton("关闭 APP") { _, _ ->
                            finishAffinity()
                            Process.killProcess(Process.myPid())
                        }.show()
                }
            }
        }.start()
    }

    private fun chooseGameFile() {
        val state = ServerPrefs.read(this)
        if (state.running || state.desired || importing) return
        AlertDialog.Builder(this)
            .setTitle("导入新版游戏")
            .setMessage("请选择自己从 HotPointFGames 构建的可信 .py 或 .txt 文件。导入的 Python 文件会在本机执行代码。完成后重新打开 APP 即可使用。")
            .setNegativeButton("取消", null)
            .setPositiveButton("选择文件") { _, _ ->
                val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "*/*"
                }
                startActivityForResult(intent, PICK_GAME)
            }
            .show()
    }

    @Deprecated("Uses Android document picker for API 24 compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == PICK_GAME && resultCode == RESULT_OK) {
            data?.data?.let { changeGame(it) }
        }
    }

    private fun changeGame(uri: Uri?) {
        val state = ServerPrefs.read(this)
        if (state.running || state.desired || importing) return
        importing = true
        refreshUi()
        val directory = filesDir
        Thread {
            var error: String? = null
            val pending = File(directory, "gamehall_import.pending")
            try {
                val bridge = Python.getInstance().getModule("android_bridge")
                val result = if (uri != null) {
                    contentResolver.openInputStream(uri).use { input ->
                        requireNotNull(input) { "无法读取文件" }
                        pending.outputStream().use { output ->
                            val buffer = ByteArray(8192)
                            var total = 0
                            while (true) {
                                val count = input.read(buffer)
                                if (count < 0) break
                                total += count
                                require(total <= MAX_GAME_BYTES) { "游戏文件不能超过 4 MB" }
                                output.write(buffer, 0, count)
                            }
                        }
                    }
                    bridge.callAttr("install_game", directory.absolutePath)
                } else {
                    bridge.callAttr("restore_builtin", directory.absolutePath)
                }
                val response = JSONObject(result.toJava(String::class.java))
                if (!response.optBoolean("ok")) error = response.optString("error", "操作失败")
            } catch (e: Throwable) {
                error = e.message ?: "操作失败"
            } finally {
                pending.delete()
            }
            runOnUiThread {
                if (isFinishing || isDestroyed) return@runOnUiThread
                if (error != null) {
                    importing = false
                    refreshUi()
                    AlertDialog.Builder(this)
                        .setTitle("未更换游戏文件")
                        .setMessage(error)
                        .setPositiveButton("知道了", null)
                        .show()
                } else {
                    // A new process prevents old Python module state / daemon threads being reused.
                    AlertDialog.Builder(this)
                        .setTitle(if (uri == null) "已恢复内置版" else "新版已导入")
                        .setMessage("APP 将关闭。重新点击桌面图标，再启动游戏厅，即可使用新版。")
                        .setCancelable(false)
                        .setPositiveButton("关闭 APP") { _, _ ->
                            finishAffinity()
                            Process.killProcess(Process.myPid())
                        }
                        .show()
                }
            }
        }.start()
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
