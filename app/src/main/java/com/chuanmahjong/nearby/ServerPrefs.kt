package com.chuanmahjong.nearby

import android.content.Context

object ServerPrefs {
    private const val FILE = "game_server"
    private const val KEY_DESIRED = "desired"
    private const val KEY_RUNNING = "running"
    private const val KEY_PORT = "port"
    private const val KEY_ERROR = "error"

    data class Snapshot(
        val desired: Boolean,
        val running: Boolean,
        val port: Int,
        val error: String,
    )

    fun read(context: Context): Snapshot {
        val prefs = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
        return Snapshot(
            desired = prefs.getBoolean(KEY_DESIRED, false),
            running = prefs.getBoolean(KEY_RUNNING, false),
            port = prefs.getInt(KEY_PORT, 8000),
            error = prefs.getString(KEY_ERROR, "") ?: "",
        )
    }

    fun setDesired(context: Context, desired: Boolean) {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_DESIRED, desired).apply()
    }

    fun setStarting(context: Context) {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit()
            .putBoolean(KEY_RUNNING, false)
            .putString(KEY_ERROR, "")
            .apply()
    }

    fun setRunning(context: Context, port: Int, warning: String = "") {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit()
            .putBoolean(KEY_RUNNING, true)
            .putInt(KEY_PORT, port)
            .putString(KEY_ERROR, warning)
            .apply()
    }

    fun setStopped(context: Context, error: String = "") {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit()
            .putBoolean(KEY_RUNNING, false)
            .putString(KEY_ERROR, error)
            .apply()
    }
}
