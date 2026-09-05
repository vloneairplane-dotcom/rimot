package com.example.remotemanager

import android.os.Bundle
import android.os.Build
import android.provider.Settings
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.*
import okhttp3.*
import org.json.JSONObject

class MainActivity : AppCompatActivity() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val server = "wss://android-remote-manager-api-production-a8e5.up.railway.app"
    private lateinit var deviceId: String

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
        // Pair the device through POST /devices/pair, then connect using the returned server-side ID.
        // This starter keeps pairing explicit; no hidden background enrollment is performed.
    }

    fun connect(serverDeviceId: String) {
        val client = OkHttpClient()
        val request = Request.Builder().url("$server/ws/device/$serverDeviceId").build()
        client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                sendStatus(ws)
            }
            override fun onMessage(ws: WebSocket, text: String) {
                val msg = JSONObject(text)
                if (msg.optString("event") == "command") handleCommand(ws, msg)
            }
        })
    }

    private fun sendStatus(ws: WebSocket) {
        val data = JSONObject()
            .put("android_version", Build.VERSION.RELEASE)
            .put("model", Build.MODEL)
        ws.send(JSONObject().put("event","status").put("data",data).toString())
    }

    private fun handleCommand(ws: WebSocket, msg: JSONObject) {
        val type = msg.optString("type")
        val result = JSONObject().put("event","command_result")
            .put("command_id", msg.optString("command_id"))
            .put("type", type)
            .put("ok", type in setOf("get_device_info","get_status","sync_status"))
        ws.send(result.toString())
    }
}
