package com.cprieto.ai3voicebridge;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class VoiceTriggerReceiver extends BroadcastReceiver {
    public static final String ACTION_TRIGGER = "com.cprieto.ai3voicebridge.TRIGGER";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !ACTION_TRIGGER.equals(intent.getAction())) return;
        VoiceSignal.post(context);
    }
}
