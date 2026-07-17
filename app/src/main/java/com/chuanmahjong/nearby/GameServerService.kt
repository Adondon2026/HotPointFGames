package com.chuanmahjong.nearby

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import com.chaquo.python.Python
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class GameServerService : Service() {
    companion object {
        private const val ACTION_START = "com.chuanmahjong.nearby.START"
        private const val ACTION_STOP = "com.chuanmahjong.nearby.STOP"
        private const val CHANNEL_ID = "game_server"
        private const val NOTIFICATION_ID = 6200

        fun start(context: Context) {
            ServerPrefs.setDesired(context, true)
            val intent = Intent(context, GameServerService::class.java).setAction(ACTION_START)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            ServerPrefs.setDesired(context, false)
            val intent = Intent(context, GameServerService::class.java).setAction(ACTION_STOP)
            context.startService(intent)
        }
    }

    private val worker = Executors.newSingleThreadExecutor()
    private val operating = AtomicBoolean(false)
    private val stopRequested = AtomicBoolean(false)
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP || !ServerPrefs.read(this).desired) {
            stopRequested.set(true)
            startForeground(NOTIFICATION_ID, notification("正在停止服务器…"))
            stopServer()
        } else {
            stopRequested.set(false)
            startForeground(NOTIFICATION_ID, notification("正在启动服务器…"))
            startServer()
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startServer() {
        if (!operating.compareAndSet(false, true)) return
        ServerPrefs.setStarting(this)
        worker.execute {
            try {
                val raw = Python.getInstance().getModule("android_bridge")
                    .callAttr("start_server", 8000, 8010)
                    .toJava(String::class.java)
                val result = JSONObject(raw)
                if (result.optBoolean("running")) {
                    if (stopRequested.get() || !ServerPrefs.read(this).desired) {
                        Python.getInstance().getModule("android_bridge").callAttr("stop_server", true)
                        ServerPrefs.setStopped(this)
                        stopForeground(STOP_FOREGROUND_REMOVE)
                        stopSelf()
                        return@execute
                    }
                    val port = result.getInt("port")
                    ServerPrefs.setRunning(this, port)
                    acquireWakeLock()
                    updateNotification("服务器运行中 · 端口 $port")
                } else {
                    val error = result.optString("error", "服务器启动失败")
                    ServerPrefs.setDesired(this, false)
                    ServerPrefs.setStopped(this, error)
                    updateNotification(error)
                    stopForeground(STOP_FOREGROUND_REMOVE)
                    stopSelf()
                }
            } catch (error: Throwable) {
                val message = "服务器启动失败：${error.message ?: error.javaClass.simpleName}"
                ServerPrefs.setDesired(this, false)
                ServerPrefs.setStopped(this, message)
                updateNotification(message)
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            } finally {
                operating.set(false)
            }
        }
    }

    private fun stopServer() {
        if (!operating.compareAndSet(false, true)) return
        worker.execute {
            try {
                Python.getInstance().getModule("android_bridge").callAttr("stop_server", true)
                ServerPrefs.setStopped(this)
            } catch (error: Throwable) {
                ServerPrefs.setStopped(this, "停止服务器时发生错误：${error.message.orEmpty()}")
            } finally {
                releaseWakeLock()
                operating.set(false)
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
    }

    private fun acquireWakeLock() {
        if (wakeLock?.isHeld == true) return
        val powerManager = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "$packageName:game-server",
        ).apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    private fun releaseWakeLock() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "局域网游戏服务器",
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = "服务器运行期间保持显示，避免锁屏后游戏中断"
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun notification(text: String): Notification {
        val openIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stopIntent = PendingIntent.getService(
            this,
            1,
            Intent(this, GameServerService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle("热点游戏厅")
            .setContentText(text)
            .setContentIntent(openIntent)
            .setOngoing(true)
            .setCategory(Notification.CATEGORY_SERVICE)
            .addAction(Notification.Action.Builder(null, "停止", stopIntent).build())
            .build()
    }

    private fun updateNotification(text: String) {
        getSystemService(NotificationManager::class.java)
            .notify(NOTIFICATION_ID, notification(text))
    }

    override fun onDestroy() {
        releaseWakeLock()
        worker.shutdownNow()
        super.onDestroy()
    }
}
