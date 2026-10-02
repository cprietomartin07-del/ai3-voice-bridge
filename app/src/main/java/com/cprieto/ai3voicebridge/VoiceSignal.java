package com.cprieto.ai3voicebridge;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;

public final class VoiceSignal {
    public static final String KEYWORD = "AI3_CHATGPT_VOICE";
    private static final String CHANNEL_ID = "ai3_voice_bridge";
    private static final int NOTIFICATION_ID = 31017;

    private VoiceSignal() {}

    public static boolean canNotify(Context context) {
        return Build.VERSION.SDK_INT < 33 ||
                context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED;
    }

    public static boolean post(Context context) {
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager == null || !canNotify(context)) return false;

        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "AI3 ChatGPT Voice",
                    NotificationManager.IMPORTANCE_DEFAULT
            );
            channel.setDescription("Sinal para o Samsung Modos e Rotinas iniciar o ChatGPT Voice.");
            manager.createNotificationChannel(channel);
        }

        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(context, CHANNEL_ID)
                : new Notification.Builder(context);

        builder.setSmallIcon(R.drawable.ic_stat_voice)
                .setContentTitle("AI3 Voice Bridge")
                .setContentText(KEYWORD)
                .setTicker(KEYWORD)
                .setAutoCancel(true)
                .setOnlyAlertOnce(false);

        manager.notify(NOTIFICATION_ID, builder.build());

        new Handler(Looper.getMainLooper()).postDelayed(
                () -> manager.cancel(NOTIFICATION_ID),
                7000L
        );
        return true;
    }
}
