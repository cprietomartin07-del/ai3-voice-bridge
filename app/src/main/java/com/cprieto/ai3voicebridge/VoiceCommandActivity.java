package com.cprieto.ai3voicebridge;

import android.app.Activity;
import android.os.Bundle;

public class VoiceCommandActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        VoiceSignal.post(this);
        finish();
        overridePendingTransition(0, 0);
    }
}
