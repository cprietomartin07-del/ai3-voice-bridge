#!/usr/bin/env python3
from pathlib import Path

ROOT = Path("upstream")

def replace(path, old, new):
    p = ROOT / path
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"pattern not found in {path}: {old[:120]!r}")
    p.write_text(s.replace(old, new, 1))

path = "android/CyanBridge/app/src/main/java/com/fersaiyan/cyanbridge/ui/AutoPairManager.kt"
replace(path,
"""    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    @Volatile
    private var started = false
""",
"""    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    @Volatile
    private var started = false

    @Volatile
    private var lastHeyCyanWakeArmAtMs = 0L
""")

replace(path,
"""                if (connected && selectedClass == DeviceClass.HEY_CYAN) {
                    scheduleHeyCyanMaximumDurations()
                    backoffMs = 5_000L
                    delay(20_000L)
                    continue
                }
""",
"""                if (connected && selectedClass == DeviceClass.HEY_CYAN) {
                    scheduleHeyCyanMaximumDurations()
                    rearmHeyCyanWakeWord(force = false)
                    backoffMs = 5_000L
                    delay(20_000L)
                    continue
                }
""")

insert_anchor = """    private fun scheduleHeyCyanMaximumDurations() {
"""
p = ROOT / path
s = p.read_text()
if insert_anchor not in s:
    raise SystemExit("AutoPairManager insertion anchor not found")
helpers = r'''    fun keepHeyCyanReady(context: Context) {
        if (DeviceProfileStore.selectedClass(context) != DeviceClass.HEY_CYAN) return
        val manager = BleOperateManager.getInstance()
        if (!manager.isConnected) {
            requestConnect(context, reason = "heycyan_keepalive")
            return
        }
        rearmHeyCyanWakeWord(force = false)
    }

    fun rearmHeyCyanWakeWord(force: Boolean = false) {
        if (!BleOperateManager.getInstance().isConnected) return
        val now = android.os.SystemClock.elapsedRealtime()
        if (!force && now - lastHeyCyanWakeArmAtMs < HEY_CYAN_WAKE_REARM_MS) return

        lastHeyCyanWakeArmAtMs = now
        runCatching {
            LargeDataHandler.getInstance().aiVoiceWake(true, true) { _, response ->
                if (!response.isOpen) {
                    lastHeyCyanWakeArmAtMs = 0L
                }
                Log.i(TAG, "Hey Cyan wake word re-armed=${response.isOpen}")
            }
        }.onFailure {
            lastHeyCyanWakeArmAtMs = 0L
            Log.w(TAG, "Unable to re-arm Hey Cyan wake word", it)
        }
    }

    private fun scheduleHeyCyanWakeArm() {
        scope.launch {
            repeat(60) {
                if (BleOperateManager.getInstance().isConnected) {
                    rearmHeyCyanWakeWord(force = true)
                    return@launch
                }
                delay(100L)
            }
        }
    }

'''
p.write_text(s.replace(insert_anchor, helpers + insert_anchor, 1))

replace(path,
"""        mgr.connectDirectly(mac)
        if (profile?.selectedClass == DeviceClass.HEY_CYAN) scheduleHeyCyanMaximumDurations()
        return true
""",
"""        mgr.connectDirectly(mac)
        if (profile?.selectedClass == DeviceClass.HEY_CYAN) {
            scheduleHeyCyanMaximumDurations()
            scheduleHeyCyanWakeArm()
        }
        return true
""")

replace(path,
"""        mgr.connectDirectly(mac)
        if (DeviceProfileStore.selectedClass(context) == DeviceClass.HEY_CYAN) {
            scheduleHeyCyanMaximumDurations()
        }
        return true
""",
"""        mgr.connectDirectly(mac)
        if (DeviceProfileStore.selectedClass(context) == DeviceClass.HEY_CYAN) {
            scheduleHeyCyanMaximumDurations()
            scheduleHeyCyanWakeArm()
        }
        return true
""")

replace(path,
"""    private const val HEY_CYAN_MAX_VIDEO_SECONDS = 720
""",
"""    private const val HEY_CYAN_WAKE_REARM_MS = 45_000L
    private const val HEY_CYAN_MAX_VIDEO_SECONDS = 720
""")

service = r'''package com.fersaiyan.cyanbridge.ui

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import com.fersaiyan.cyanbridge.R
import com.fersaiyan.cyanbridge.devices.DeviceProfileStore
import com.fersaiyan.cyanbridge.shared.devices.DeviceClass
import com.oudmon.ble.base.communication.LargeDataHandler
import com.oudmon.ble.base.communication.responseImpl.GlassesDeviceNotifyRsp
import com.oudmon.ble.base.communication.listener.GlassesDeviceNotifyListener
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class HeyCyanKeepAliveService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var loopJob: Job? = null

    private val listener = object : GlassesDeviceNotifyListener() {
        override fun parseData(cmdType: Int, response: GlassesDeviceNotifyRsp) {
            val data = response.loadData
            if (data.size <= 7) return
            if ((data[6].toInt() and 0xFF) != 0x03) return
            if ((data[7].toInt() and 0xFF) != 1) return

            val now = android.os.SystemClock.elapsedRealtime()
            synchronized(Companion) {
                if (now - lastTriggerAtMs < TRIGGER_DEBOUNCE_MS) return
                lastTriggerAtMs = now
            }

            Log.i(TAG, "HeyCyan AI trigger received in background service")
            launchAi3VoiceBridge()
        }
    }

    override fun onCreate() {
        super.onCreate()
        running = true
        createChannel()
        startForeground(NOTIFICATION_ID, buildNotification())

        runCatching {
            LargeDataHandler.getInstance().addOutDeviceListener(LISTENER_ID, listener)
        }.onFailure {
            Log.w(TAG, "Unable to register background glasses listener", it)
        }

        loopJob = scope.launch {
            while (isActive) {
                if (DeviceProfileStore.selectedClass(this@HeyCyanKeepAliveService) == DeviceClass.HEY_CYAN) {
                    AutoPairManager.keepHeyCyanReady(this@HeyCyanKeepAliveService)
                }
                delay(KEEPALIVE_INTERVAL_MS)
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        AutoPairManager.keepHeyCyanReady(this)
        return START_STICKY
    }

    private fun launchAi3VoiceBridge() {
        val intent = Intent(Intent.ACTION_VOICE_COMMAND).apply {
            setPackage(AI3_BRIDGE_PACKAGE)
            addCategory(Intent.CATEGORY_DEFAULT)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
        runCatching {
            startActivity(intent)
        }.onFailure { error ->
            Log.w(TAG, "AI3 Voice Bridge not available; falling back to generic VOICE_COMMAND", error)
            runCatching {
                startActivity(
                    Intent(Intent.ACTION_VOICE_COMMAND).apply {
                        addCategory(Intent.CATEGORY_DEFAULT)
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                )
            }.onFailure {
                Log.e(TAG, "Unable to launch any phone voice command route", it)
            }
        }
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java) ?: return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "AI3 glasses connection",
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = "Keeps W-AI3 Pro controls and Hey Cyan available in the background."
            setShowBadge(false)
        }
        manager.createNotificationChannel(channel)
    }

    private fun buildNotification(): Notification {
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            Notification.Builder(this)
        }
        return builder
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("CyanBridge • AI3 ativo")
            .setContentText("Botão físico e Hey Cyan disponíveis em segundo plano")
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .build()
    }

    override fun onDestroy() {
        running = false
        loopJob?.cancel()
        runCatching { LargeDataHandler.getInstance().removeOutDeviceListener(LISTENER_ID) }
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val TAG = "HeyCyanKeepAlive"
        private const val CHANNEL_ID = "heycyan_keepalive"
        private const val NOTIFICATION_ID = 7311
        private const val LISTENER_ID = 101
        private const val KEEPALIVE_INTERVAL_MS = 20_000L
        private const val TRIGGER_DEBOUNCE_MS = 1_500L
        private const val AI3_BRIDGE_PACKAGE = "com.cprieto.ai3voicebridge"

        @Volatile
        private var running = false

        @Volatile
        private var lastTriggerAtMs = 0L

        fun isRunning(): Boolean = running

        fun start(context: Context) {
            if (DeviceProfileStore.selectedClass(context) != DeviceClass.HEY_CYAN) return
            val intent = Intent(context, HeyCyanKeepAliveService::class.java)
            runCatching {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(intent)
                } else {
                    context.startService(intent)
                }
            }.onFailure {
                Log.w(TAG, "Unable to start HeyCyan foreground keep-alive", it)
            }
        }
    }
}
'''
servicePath = ROOT / "android/CyanBridge/app/src/main/java/com/fersaiyan/cyanbridge/ui/HeyCyanKeepAliveService.kt"
servicePath.write_text(service)

myapp = "android/CyanBridge/app/src/main/java/com/fersaiyan/cyanbridge/ui/MyApplication.kt"
replace(myapp,
"""        AutoPairManager.start(this)

        // Local Agent: ensure daily reminder schedule matches current prefs.
""",
"""        AutoPairManager.start(this)
        HeyCyanKeepAliveService.start(this)

        // Local Agent: ensure daily reminder schedule matches current prefs.
""")

main = "android/CyanBridge/app/src/main/java/com/fersaiyan/cyanbridge/MainActivity.kt"
replace(main,
"""        if (connected) {
            configureHeyCyanWakeWordIfNeeded()
            refreshHeyCyanRecordingSettings(showDisconnectedMessage = false)
""",
"""        if (connected) {
            com.fersaiyan.cyanbridge.ui.HeyCyanKeepAliveService.start(this)
            configureHeyCyanWakeWordIfNeeded()
            refreshHeyCyanRecordingSettings(showDisconnectedMessage = false)
""")

replace(main,
"""                0x03 -> {
                    if (response.loadData.size > 7 && response.loadData[7].toInt() == 1) {
                        Log.i("DeviceNotify", "AI Button Pressed - Hijacking to Phone Assistant")
                        if (isAiHijackEnabled) {
                            handleAiWakeWordActivation("heycyan")
""",
"""                0x03 -> {
                    if (response.loadData.size > 7 && response.loadData[7].toInt() == 1) {
                        if (isHeyCyanSelected() &&
                            com.fersaiyan.cyanbridge.ui.HeyCyanKeepAliveService.isRunning()
                        ) {
                            Log.d("DeviceNotify", "0x03 delegated to persistent HeyCyan service")
                            return
                        }
                        Log.i("DeviceNotify", "AI Button Pressed - Hijacking to Phone Assistant")
                        if (isAiHijackEnabled) {
                            handleAiWakeWordActivation("heycyan")
""")

manifest = "android/CyanBridge/app/src/main/AndroidManifest.xml"
replace(manifest,
"""        <service android:name=".devices.meizumyvu.MeizuMyvuConnectionService" android:exported="false" android:foregroundServiceType="connectedDevice" />
""",
"""        <service android:name=".devices.meizumyvu.MeizuMyvuConnectionService" android:exported="false" android:foregroundServiceType="connectedDevice" />
        <service android:name=".ui.HeyCyanKeepAliveService" android:exported="false" android:foregroundServiceType="connectedDevice" />
""")

print("AI3 persistence patch applied successfully")
