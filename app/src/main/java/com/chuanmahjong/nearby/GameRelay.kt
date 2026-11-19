package com.chuanmahjong.nearby

import android.util.Base64
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.SecureRandom
import java.util.concurrent.ConcurrentHashMap

/** One relay session within the game server foreground service. */
object GameRelay {
    @Volatile var status = ""
        private set
    @Volatile var invitation = ""
        private set
    @Volatile private var worker: Thread? = null
    fun active() = worker != null

    private const val LIMIT = 4 * 1024 * 1024
    private val remoteSeatOwners = ConcurrentHashMap<String, String>()
    internal data class Reply(val code: Int, val type: String, val body: ByteArray)

    internal fun request(url: URL, method: String, data: ByteArray?, headers: Map<String, String> = emptyMap()): Reply {
        val connection = url.openConnection() as HttpURLConnection
        try {
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 5000
            connection.readTimeout = 16_000
            connection.requestMethod = method
            headers.forEach { (name, value) -> connection.setRequestProperty(name, value) }
            if (data != null) {
                connection.doOutput = true
                if (!headers.containsKey("Content-Type")) connection.setRequestProperty("Content-Type", "application/json")
                connection.setFixedLengthStreamingMode(data.size)
                connection.outputStream.use { it.write(data) }
            }
            val code = connection.responseCode
            val input = if (code >= 400) connection.errorStream else connection.inputStream
            val body = input?.use {
                val bytes = java.io.ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                while (true) {
                    val n = it.read(buffer)
                    if (n < 0) break
                    require(bytes.size() + n <= LIMIT * 2)
                    bytes.write(buffer, 0, n)
                }
                bytes.toByteArray()
            } ?: ByteArray(0)
            return Reply(code, connection.contentType ?: "application/octet-stream", body)
        } finally {
            connection.disconnect()
        }
    }

    internal fun baseAddress(input: String): String {
        val address = input.trim().trimEnd('/')
        require(address.isNotEmpty()) { "请输入公网 IP 和端口" }
        val base = if (address.contains("://")) address else "https://$address"
        val url = runCatching { URL(base) }.getOrElse { throw IllegalArgumentException("地址格式应为 IP:端口") }
        require((url.protocol == "https" || url.protocol == "http" && url.host == "127.0.0.1")
            && url.host.isNotBlank() && url.userInfo == null && url.path.isEmpty() &&
            url.query == null && url.ref == null && (url.port == -1 || url.port in 1..65535)) { "请填写 HTTPS 地址或公网 IP:端口" }
        return base
    }

    @Synchronized fun start(address: String, key: String, port: Int) {
        require(worker == null) { "请等待上一条中继连接关闭" }
        val base = baseAddress(address)
        require(key.matches(Regex("[a-f0-9]{64}"))) { "房主密钥应为 64 位十六进制字符" }
        val nonce = ByteArray(24).also { SecureRandom().nextBytes(it) }.joinToString("") { "%02x".format(it) }
        val headers = mapOf("Authorization" to "Bearer $key", "X-Game-Invite" to nonce)
        fun relay(path: String, data: ByteArray = ByteArray(0)) = request(URL("$base/relay/$path"), "POST", data, headers)
        status = "正在连接中继…"
        val thread = Thread {
            val current = Thread.currentThread()
            try {
                while (!current.isInterrupted) {
                    try {
                        val reply = relay("poll")
                        if (current.isInterrupted) break
                        if (reply.code in listOf(400, 403, 409)) {
                            status = "中继拒绝连接（${reply.code}）"
                            break
                        }
                        check(reply.code == 200 || reply.code == 204)
                        invitation = "$base/invite/$nonce"
                        status = "中继已连接"
                        if (reply.code == 204) continue
                        val job = JSONObject(reply.body.toString(Charsets.UTF_8))
                        val path = job.getString("path")
                        val method = job.getString("method")
                        require(path.startsWith("/") && !path.startsWith("//") && !path.contains('\\'))
                        val identity = job.getJSONObject("identity")
                        val uid = identity.getString("id")
                        val nickname = identity.getString("name")
                        require(uid.matches(Regex("[a-f0-9]{32}")) && nickname.isNotBlank())
                        val response = runCatching {
                            require(method == "GET" || method == "POST")
                            require(path.substringBefore('?') != "/api/account") {
                                "远程用户只能使用云账号"
                            }
                            val incoming = if (method == "POST")
                                Base64.decode(job.getString("body"),Base64.DEFAULT) else null
                            val endpoint = path.substringBefore('?')
                            val join = endpoint == "/api/rooms" ||
                                Regex("/r/[A-Fa-f0-9]{6}/api/join").matches(endpoint)
                            val payload = if (join && method == "POST") {
                                val body = JSONObject(incoming!!.toString(Charsets.UTF_8))
                                // A browser-supplied name/accountToken is untrusted.
                                // Only the Node relay can authenticate this cloud identity.
                                body.put("name",nickname)
                                body.put("accountToken",CloudAccounts.prepareRemotePlayer(uid,nickname))
                                body.toString().toByteArray(Charsets.UTF_8)
                            } else incoming
                            val protected = Regex("/r/[A-Fa-f0-9]{6}/api/(state|action|siege)").matches(endpoint)
                            if (protected) {
                                val token = if (method == "GET") {
                                    val query = path.substringAfter('?', "")
                                    query.split('&').firstNotNullOfOrNull {
                                        if (it.startsWith("token=")) java.net.URLDecoder.decode(it.substring(6),"UTF-8") else null
                                    } ?: ""
                                } else JSONObject(payload!!.toString(Charsets.UTF_8)).optString("token")
                                require(remoteSeatOwners[token] == uid) { "请重新通过房间链接加入" }
                            }
                            val answer = request(URL("http://127.0.0.1:$port$path"),method,payload)
                            if (join && answer.code == 200) {
                                val joined = JSONObject(answer.body.toString(Charsets.UTF_8))
                                if (joined.optBoolean("ok")) {
                                    if (remoteSeatOwners.size > 512) remoteSeatOwners.clear()
                                    remoteSeatOwners[joined.getString("token")] = uid
                                }
                            }
                            answer
                        }.getOrElse { err ->
                            val body = JSONObject().put("ok",false)
                                .put("error",err.message ?: "远程账户未验证").toString()
                            Reply(403,"application/json",body.toByteArray(Charsets.UTF_8))
                        }
                        val result = JSONObject().put("id", job.getInt("id")).put("status", response.code)
                            .put("type", response.type).put("body", Base64.encodeToString(response.body, Base64.NO_WRAP))
                        relay("reply", result.toString().toByteArray())
                    } catch (_: Exception) {
                        invitation = ""
                        if (current.isInterrupted) break
                        status = "中继暂时不可用，正在重试…"
                        Thread.sleep(2000)
                    }
                }
            } catch (_: InterruptedException) {
            } finally {
                Thread.interrupted()
                runCatching { relay("close") }
                synchronized(this) {
                    invitation = ""
                    worker = null
                }
            }
        }
        worker = thread
        thread.start()
    }

    @Synchronized fun stop() {
        remoteSeatOwners.clear()
        invitation = ""
        status = ""
        worker?.interrupt()
    }
}
