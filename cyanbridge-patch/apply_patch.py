#!/usr/bin/env python3
from pathlib import Path

ROOT = Path("upstream")

# GitHub-hosted runners can intermittently fail against repo.maven.apache.org.
# Add Google's Maven Central mirror before building, without removing upstream repositories.
for rel in ["android/CyanBridge/settings.gradle.kts", "heycyan-core/settings.gradle.kts"]:
    p = ROOT / rel
    s = p.read_text()
    needle = "repositories {\\n        google()\\n        mavenCentral()"
    repl = "repositories {\\n        google()\\n        maven { url = uri(\\\"https://maven-central.storage-download.googleapis.com/maven2\\\") }\\n        mavenCentral()"
    # settings files each have pluginManagement and dependencyResolution repositories blocks.
    s = s.replace(needle, repl)
    p.write_text(s)

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
import com.oudmon.ble.base.communication.bigData.resp.GlassesDeviceNotifyRsp
import com.oudmon.ble.base.communication.bigData.resp.GlassesDeviceNotifyListener
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
            notifyAi3VoiceBridge()
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

    private fun notifyAi3VoiceBridge() {
        val intent = Intent(AI3_BRIDGE_TRIGGER_ACTION).apply {
            setPackage(AI3_BRIDGE_PACKAGE)
        }
        runCatching {
            sendBroadcast(intent)
            Log.i(TAG, "AI3 Voice Bridge trigger broadcast sent")
        }.onFailure {
            Log.e(TAG, "Unable to notify AI3 Voice Bridge", it)
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
        private const val AI3_BRIDGE_TRIGGER_ACTION = "com.cprieto.ai3voicebridge.TRIGGER"

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


# AI3-only build: replace Meta DAT integration with compile-safe stubs when the private
# Meta Wearables GitHub package is unavailable. This does not affect HeyCyan/AI3 paths.
meta_manager = ROOT / "android/CyanBridge/app/src/main/java/com/fersaiyan/cyanbridge/devices/metarayban/MetaRaybanManager.kt"
meta_manager.write_text(r'''package com.fersaiyan.cyanbridge.devices.metarayban

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import java.io.File
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * AI3 build stub. Meta DAT requires a private GitHub package token and is intentionally
 * unavailable in this dedicated W-AI3 Pro build.
 */
class MetaRaybanManager private constructor(private val context: Context) {
    companion object {
        private const val META_DISABLED = "Meta DAT disabled in CyanBridge AI3 build"
        @Volatile private var instance: MetaRaybanManager? = null
        fun getInstance(context: Context): MetaRaybanManager =
            instance ?: synchronized(this) {
                instance ?: MetaRaybanManager(context.applicationContext).also { instance = it }
            }
    }

    private val _isInitialized = MutableStateFlow(false)
    val isInitialized: StateFlow<Boolean> = _isInitialized.asStateFlow()
    private val _registrationState = MutableStateFlow(RegistrationState.UNAVAILABLE)
    val registrationState: StateFlow<RegistrationState> = _registrationState.asStateFlow()
    private val _metaAccessState = MutableStateFlow(MetaAccessState.FAILED)
    val metaAccessState: StateFlow<MetaAccessState> = _metaAccessState.asStateFlow()
    private val _availableDeviceCount = MutableStateFlow(0)
    val availableDeviceCount: StateFlow<Int> = _availableDeviceCount.asStateFlow()
    private val _selectedDeviceName = MutableStateFlow<String?>(null)
    val selectedDeviceName: StateFlow<String?> = _selectedDeviceName.asStateFlow()
    private val _selectedDeviceIsDisplayCapable = MutableStateFlow(false)
    val selectedDeviceIsDisplayCapable: StateFlow<Boolean> = _selectedDeviceIsDisplayCapable.asStateFlow()
    private val _deviceSessionState = MutableStateFlow(DeviceSessionState.IDLE)
    val deviceSessionState: StateFlow<DeviceSessionState> = _deviceSessionState.asStateFlow()
    private val _streamState = MutableStateFlow(StreamState.STOPPED)
    val streamState: StateFlow<StreamState> = _streamState.asStateFlow()
    private val _isStreaming = MutableStateFlow(false)
    val isStreaming: StateFlow<Boolean> = _isStreaming.asStateFlow()
    private val _lastCapturedPhoto = MutableStateFlow<CapturedPhoto?>(null)
    val lastCapturedPhoto: StateFlow<CapturedPhoto?> = _lastCapturedPhoto.asStateFlow()
    private val _isDisplayActive = MutableStateFlow(false)
    val isDisplayActive: StateFlow<Boolean> = _isDisplayActive.asStateFlow()
    private val _lastError = MutableStateFlow<String?>(META_DISABLED)
    val lastError: StateFlow<String?> = _lastError.asStateFlow()
    private val _debugMockEnabled = MutableStateFlow(false)
    val debugMockEnabled: StateFlow<Boolean> = _debugMockEnabled.asStateFlow()

    fun isDebugMockEnabled(): Boolean = false
    fun setDebugMockEnabled(enabled: Boolean) { _debugMockEnabled.value = false }
    fun initialize() { _lastError.value = META_DISABLED }
    fun startRegistration(activity: Activity) { _lastError.value = META_DISABLED }
    fun startUnregistration(activity: Activity) { _lastError.value = META_DISABLED }
    fun isRegistered(): Boolean = false
    fun isCameraReady(): Boolean = false
    suspend fun awaitCameraReady(timeoutMs: Long = 10_000L): Boolean = false
    fun refreshRegistrationState() { _registrationState.value = RegistrationState.UNAVAILABLE }
    fun handleRegistrationCallback(intent: Intent): Boolean = false

    fun checkCameraPermission(
        onGranted: () -> Unit,
        onRequestNeeded: () -> Unit,
        onError: (String) -> Unit,
    ) = onError(META_DISABLED)

    fun startSession(onSuccess: () -> Unit, onError: (String) -> Unit) = onError(META_DISABLED)
    fun stopSession() { _deviceSessionState.value = DeviceSessionState.IDLE }
    fun startStreaming(
        onFrame: (Bitmap) -> Unit,
        onSuccess: () -> Unit,
        onError: (String) -> Unit,
    ) = onError(META_DISABLED)
    fun stopStreaming() {
        _isStreaming.value = false
        _streamState.value = StreamState.STOPPED
    }

    fun capturePhoto(onSuccess: (CapturedPhoto) -> Unit, onError: (String) -> Unit) =
        onError(META_DISABLED)

    suspend fun capturePhotoOnce(timeoutMs: Long = 20_000L): CapturedPhoto =
        throw IllegalStateException(META_DISABLED)

    suspend fun savePhotoForProcessing(photo: CapturedPhoto, namePrefix: String): File =
        throw IllegalStateException(META_DISABLED)

    fun startDisplay(onSuccess: () -> Unit, onError: (String) -> Unit) = onError(META_DISABLED)
    fun stopDisplay() { _isDisplayActive.value = false }
    fun reportExternalError(operation: String, message: String): String =
        "$operation: $message"
    fun diagnosticsSnapshot(): String = META_DISABLED
    fun registrationGuidance(): String? = META_DISABLED
    fun installedMetaAiPackageName(): String? = null
    fun isMetaAiInstalled(): Boolean = false
    fun destroy() { instance = null }

    data class CapturedPhoto(
        val bytes: ByteArray,
        val mimeType: String,
        val uri: Uri?,
    )

    enum class RegistrationState {
        UNAVAILABLE, AVAILABLE, REGISTERED, REGISTERING, UNREGISTERING,
    }

    enum class DeviceSessionState {
        IDLE, STARTING, STARTED, PAUSED, STOPPING, STOPPED,
    }

    enum class StreamState {
        STOPPED, STARTING, STARTED, STREAMING, STOPPING, PAUSED, CLOSED,
    }

}
''')

# Keep the class name referenced by navigation/manifest without pulling private Meta SDK types.
meta_pairing = ROOT / "android/CyanBridge/app/src/main/java/com/fersaiyan/cyanbridge/ui/MetaPairingActivity.kt"
meta_pairing.write_text(r'''package com.fersaiyan.cyanbridge.ui

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MetaPairingActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(TextView(this).apply {
            text = "Meta Ray-Ban support is disabled in this W-AI3 Pro build."
            textSize = 18f
            setPadding(48, 72, 48, 48)
        })
    }
}
''')

# Community plugins are not part of the dedicated AI3 runtime. Keep the navigation target.
community = ROOT / "android/CyanBridge/app/src/main/java/com/fersaiyan/cyanbridge/ui/CommunityPluginsActivity.kt"
community.write_text(r'''package com.fersaiyan.cyanbridge.ui

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class CommunityPluginsActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(TextView(this).apply {
            text = "Community plugins are disabled in this dedicated W-AI3 Pro build."
            textSize = 18f
            setPadding(48, 72, 48, 48)
        })
    }
}
''')

# MainActivity has only one direct Meta permission contract; route it through the stub manager.
main_path = ROOT / "android/CyanBridge/app/src/main/java/com/fersaiyan/cyanbridge/MainActivity.kt"
main_text = main_path.read_text()
main_text = main_text.replace("import com.meta.wearable.dat.core.Wearables\\n", "")
main_text = main_text.replace("import com.meta.wearable.dat.core.types.Permission\\n", "")
main_text = main_text.replace("import com.meta.wearable.dat.core.types.PermissionStatus\\n", "")
start = main_text.find("    private val metaWearablePermissionLauncher =")
end_marker = '    // Transcription UI moved to the "Transcriptions & recordings" section'
if start >= 0:
    end = main_text.find(end_marker, start)
    if end < 0:
        raise SystemExit("Meta permission launcher end marker not found")
    main_text = main_text[:start] + main_text[end:]
main_text = main_text.replace(
    """                onRequestNeeded = {
                    pendingMetaCameraAction = action
                    metaWearablePermissionLauncher.launch(Permission.CAMERA)
                },""",
    """                onRequestNeeded = {
                    pendingMetaCameraAction = null
                    showMetaError(
                        "DAT camera permission",
                        "Meta Ray-Ban support is disabled in this W-AI3 Pro build",
                    )
                },""",
)
main_path.write_text(main_text)

print("AI3 persistence patch applied successfully")
