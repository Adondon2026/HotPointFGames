package com.chuanmahjong.nearby

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.chaquo.python.Python
import org.json.JSONObject
import java.net.URL
import java.security.KeyStore
import java.security.MessageDigest
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

object CloudAccounts {
    private const val ALIAS = "hotpoint-cloud-v1"
    private val worker = Executors.newSingleThreadScheduledExecutor()
    private lateinit var context: Context
    @Volatile var status = ""
        private set
    @Volatile private var saved = JSONObject()

    val address: String get() = saved.optString("address")
    val name: String get() = saved.optString("name")
    val loggedIn: Boolean get() = saved.has("id")
    val admin: Boolean get() = saved.optBoolean("admin")

    fun init(app: Context) {
        context = app.applicationContext
        saved = runCatching { load() }.getOrDefault(JSONObject())
        worker.scheduleWithFixedDelay({
            if (ServerPrefs.read(context).desired) sync()
        }, 30, 30, TimeUnit.SECONDS)
    }

    private fun digest(text: String) = MessageDigest.getInstance("SHA-256")
        .digest(text.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it.toInt() and 255) }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        return (store.getKey(ALIAS, null) as? SecretKey) ?: KeyGenerator
            .getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
                init(KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .build())
            }.generateKey()
    }

    private fun prefs() = context.getSharedPreferences("cloud_identity", Context.MODE_PRIVATE)

    private fun load(): JSONObject {
        val encoded = prefs().getString("settings", null) ?: return JSONObject()
        val data = Base64.decode(encoded, Base64.NO_WRAP)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, data, 0, 12))
        return JSONObject(cipher.doFinal(data, 12, data.size - 12).toString(Charsets.UTF_8))
    }

    private fun save(state: JSONObject) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val data = cipher.iv + cipher.doFinal(state.toString().toByteArray())
        check(prefs().edit().putString("settings", Base64.encodeToString(data, Base64.NO_WRAP)).commit())
        saved = state
    }

    fun execute(onResult: (Result<String>) -> Unit, task: () -> String) {
        worker.execute { onResult(runCatching(task)) }
    }

    fun configure(input: String, password: String): String {
        val base = GameRelay.baseAddress(input)
        require(base.startsWith("https://")) { "云服务需要 HTTPS" }
        require(password.isNotBlank() && password.length <= 128) { "请输入转发密码" }
        val token = digest("hotpoint-access-v1:" + password)
        val state = if (base == address) JSONObject(saved.toString()) else JSONObject()
        state.put("address", base).put("relayToken", token)
        save(state)
        sync()
        return "服务器设置已保存"
    }

    fun relayToken(): String = saved.optString("relayToken")

    private fun call(state: JSONObject, body: JSONObject): JSONObject {
        val base = state.optString("address")
        require(base.isNotEmpty()) { "请先设置服务器" }
        val reply = GameRelay.request(URL("$base/cloud/account"), "POST", body.toString().toByteArray(),
            mapOf("Authorization" to "Bearer " + state.getString("relayToken")))
        val result = runCatching { JSONObject(reply.body.toString(Charsets.UTF_8)) }.getOrDefault(JSONObject())
        check(reply.code == 200) {
            result.optString("error", when (reply.code) {
                403 -> "转发密码不正确"
                429 -> "尝试次数过多，请稍后再试"
                else -> "云服务暂时不可用（${reply.code}）"
            })
        }
        return result
    }

    fun authenticate(name: String, password: String, code: String?): String {
        val old = saved
        val body = JSONObject().put("action", if (code == null) "login" else "register")
            .put("name", name).put("password", password)
        if (code != null) body.put("code", code.trim())
        val account = call(old, body)
        for (field in listOf("address", "relayToken")) account.put(field, old.getString(field))
        val localToken = digest("hotpoint-local-session-v1:" + account.getString("token"))
        module().callAttr("prepare", account.getString("id"), account.getString("name"), localToken)
        save(account)
        sync()
        return "已登录 ${account.getString("name")}"
    }

    fun invite(): String = call(saved, JSONObject().put("action", "invite")
        .put("token", saved.getString("token"))).getString("code")

    fun signOut(): String {
        sync()
        val state = saved
        localToken()?.let { module().callAttr("forget_session", it) }
        save(JSONObject().put("address", address).put("relayToken", relayToken()))
        runCatching { call(state, JSONObject().put("action", "logout").put("token", state.getString("token"))) }
        status = ""
        return "已退出云账号"
    }

    fun localToken(): String? = saved.optString("token").takeIf { it.isNotBlank() }
        ?.let { digest("hotpoint-local-session-v1:" + it) }

    fun syncSoon() { worker.execute { sync() } }

    private fun module() = Python.getInstance().getModule("cloud_game_data")

    private fun sync() {
        val state = saved
        val uid = state.optString("id")
        if (uid.isEmpty()) return
        status = "正在同步…"
        try {
            repeat(12) {
                val batch = JSONObject(module().callAttr("pending", uid).toString())
                val sentSettings = batch.remove("localSettings").let { if (it == JSONObject.NULL) null else it as? String }
                batch.put("action", "sync").put("token", state.getString("token"))
                val reply = call(state, batch)
                module().callAttr("apply", uid, sentSettings, reply.toString())
                if (!reply.getBoolean("more") && batch.getJSONArray("results").length() < 100) {
                    status = "已同步"
                    return
                }
            }
            status = "同步进行中"
        } catch (err: Exception) {
            status = if (err.message?.contains("重新登录") == true) "云登录已过期，请重新登录"
            else "同步暂未完成，本机数据会保留"
        }
    }
}
