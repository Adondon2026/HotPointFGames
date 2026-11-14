package com.chuanmahjong.nearby

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.URL
import java.security.MessageDigest
import javax.net.ssl.HttpsURLConnection

/** Only downloads releases from the official public repository over verified HTTPS. */
object GameUpdates {
    private const val REPO = "Adondon2026/HotPointFGames"
    private const val MAX_GAME = 4 * 1024 * 1024
    private const val MANIFEST = "game-update.json"
    private const val GAME = "game_hall_lan_v6_2.py"
    private const val HOST_VERSION = 5
    private val allowedHosts = setOf("api.github.com", "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com")
    // This channel never accepts mainline game-* releases.
    private val releaseTag = if (BuildConfig.ZMZ_BUILD)
        Regex("zmz-game-v[0-9]+\\.[0-9]+\\.[0-9]+-[0-9]+-[0-9]+-[a-f0-9]{7,40}")
    else Regex("game-[0-9]+-[0-9]+-[a-f0-9]{7,40}")
    private val hashPattern = Regex("[a-f0-9]{64}")

    data class Info(val version: String, val source: String, val sourceEpoch: Long, val sha256: String, val size: Int, val minHost: Int) {
        fun json() = JSONObject().put("schema", 1).put("version", version).put("source", source)
            .put("sourceEpoch", sourceEpoch).put("sha256", sha256).put("size", size).put("minHostVersionCode", minHost)
    }
    data class Available(val tag: String, val info: Info, val notes: String)

    private fun parse(raw: String): Info {
        val obj = JSONObject(raw)
        require(obj.getInt("schema") == 1) { "更新清单格式不支持" }
        val info = Info(obj.getString("version"), obj.getString("source"), obj.getLong("sourceEpoch"),
            obj.getString("sha256"), obj.getInt("size"), obj.getInt("minHostVersionCode"))
        require(hashPattern.matches(info.sha256) && info.size in 1..MAX_GAME && info.sourceEpoch >= 0 && info.minHost > 0) { "更新清单无效" }
        return info
    }

    private fun digest(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }
    private fun digest(file: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(8192)
            while (true) { val n = input.read(buffer); if (n < 0) break; md.update(buffer, 0, n) }
        }
        return md.digest().joinToString("") { "%02x".format(it.toInt() and 255) }
    }
    private fun builtin(context: Context): Info? = runCatching {
        context.assets.open("builtin-game-info.json").bufferedReader().use { parse(it.readText()) }
    }.getOrNull()
    fun current(context: Context): Info? {
        val active = File(context.filesDir, "gamehall_import.py")
        if (!active.isFile) return builtin(context)
        // Version metadata is only valid if it describes the actual active file, including after rollback.
        val hash = digest(active)
        for (name in listOf("gamehall-update.json", "gamehall-update.previous.json")) {
            val info = runCatching { parse(File(context.filesDir, name).readText()) }.getOrNull()
            if (info?.sha256 == hash) return info
        }
        return builtin(context)?.takeIf { it.sha256 == hash } ?: Info("本地导入", "unknown", 0, hash, active.length().toInt(), 1)
    }

    private fun get(address: String, max: Int): ByteArray {
        var url = URL(address)
        repeat(6) {
            require(url.protocol == "https" && url.host in allowedHosts && url.userInfo == null && (url.port == -1 || url.port == 443)) { "拒绝非官方更新地址" }
            val conn = url.openConnection() as HttpsURLConnection
            try {
                conn.instanceFollowRedirects = false
                conn.connectTimeout = 8000
                conn.readTimeout = 15000
                conn.setRequestProperty("User-Agent", "HotPointFGames-ZMZ-Android/0.20.1")
                conn.setRequestProperty("Accept", if (url.host == "api.github.com") "application/vnd.github+json" else "application/octet-stream")
                val code = conn.responseCode
                if (code in 300..399) {
                    url = URL(url, conn.getHeaderField("Location") ?: error("更新地址无效"))
                } else {
                    require(code == 200) { "GitHub 返回 HTTP $code" }
                    require(conn.contentLength <= max) { "更新文件超过大小限制" }
                    return conn.inputStream.use { input ->
                        val output = java.io.ByteArrayOutputStream()
                        val buf = ByteArray(8192)
                        while (true) { val n = input.read(buf); if (n < 0) break; require(output.size() + n <= max) { "更新文件超过大小限制" }; output.write(buf, 0, n) }
                        output.toByteArray()
                    }
                }
            } finally { conn.disconnect() }
        }
        error("更新地址跳转过多")
    }
    private fun asset(tag: String, name: String): String {
        require(releaseTag.matches(tag) && name in setOf(MANIFEST, GAME))
        return "https://github.com/$REPO/releases/download/$tag/$name"
    }
    fun check(context: Context): Available? {
        val releases = JSONArray(get("https://api.github.com/repos/$REPO/releases?per_page=100", 2 * 1024 * 1024).toString(Charsets.UTF_8))
        val candidates = (0 until releases.length()).map { releases.getJSONObject(it) }.filter {
            !it.optBoolean("draft") && !it.optBoolean("prerelease") && releaseTag.matches(it.optString("tag_name"))
        }
        val release = candidates.maxWithOrNull(compareBy<JSONObject> {
            it.optString("tag_name").split('-')[if (BuildConfig.ZMZ_BUILD) 3 else 1].toLong()
        }.thenBy {
            it.optString("tag_name").split('-')[if (BuildConfig.ZMZ_BUILD) 4 else 2].toLong()
        }) ?: return null
        val tag = release.getString("tag_name")
        val assets = release.getJSONArray("assets")
        val names = (0 until assets.length()).map { assets.getJSONObject(it).optString("name") }
        require(MANIFEST in names && GAME in names) { "发布文件不完整" }
        val info = parse(get(asset(tag, MANIFEST), 16384).toString(Charsets.UTF_8))
        require(info.version == tag && info.source.matches(Regex("[a-f0-9]{40}")) && info.source.startsWith(tag.substringAfterLast('-'))) { "版本清单不匹配" }
        val local = current(context)
        if (local?.sha256 == info.sha256 || (local != null && local.sourceEpoch > info.sourceEpoch)) return null
        require(info.minHost <= HOST_VERSION) { "此游戏版本需要先升级 Android APP" }
        return Available(tag, info, release.optString("body").take(500))
    }
    fun download(update: Available, pending: File) {
        val data = get(asset(update.tag, GAME), MAX_GAME)
        require(data.size == update.info.size && digest(data) == update.info.sha256) { "更新文件校验失败，已保留原版本" }
        pending.outputStream().use { it.write(data); it.fd.sync() }
    }
    fun record(context: Context, info: Info) {
        val current = File(context.filesDir, "gamehall-update.json")
        val previous = File(context.filesDir, "gamehall-update.previous.json")
        if (current.isFile) current.copyTo(previous, overwrite = true)
        val temp = File(context.filesDir, "gamehall-update.tmp")
        temp.writeText(info.json().toString())
        if (!temp.renameTo(current)) { temp.delete(); error("无法写入版本记录") }
    }
}
