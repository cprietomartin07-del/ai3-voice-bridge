package com.cprieto.ai3voicebridge;

import android.app.Activity;
import android.app.KeyguardManager;
import android.content.Context;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.WindowManager;

public class VoiceCommandActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean signalSent = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Make this tiny transparent bridge activity eligible to run above the lock screen.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
        } else {
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED);
        }

        handler.postDelayed(this::dismissKeyguardThenSignal, 100L);
    }

    private void dismissKeyguardThenSignal() {
        KeyguardManager keyguard =
                (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);

        if (keyguard == null || !keyguard.isKeyguardLocked()) {
            signalAndFinish();
            return;
        }

        // On a trusted device (for example the AI3 configured in Extend Unlock /
        // Smart Lock), Android/Samsung can dismiss the keyguard without asking
        // for PIN/biometrics. If policy still blocks it, we keep the old fallback:
        // emit the signal and let ChatGPT wait for the user's normal unlock.
        try {
            keyguard.requestDismissKeyguard(
                    this,
                    new KeyguardManager.KeyguardDismissCallback() {
                        @Override
                        public void onDismissSucceeded() {
                            handler.postDelayed(
                                    VoiceCommandActivity.this::signalAndFinish,
                                    200L
                            );
                        }

                        @Override
                        public void onDismissCancelled() {
                            handler.postDelayed(
                                    VoiceCommandActivity.this::signalAndFinish,
                                    250L
                            );
                        }

                        @Override
                        public void onDismissError() {
                            handler.postDelayed(
                                    VoiceCommandActivity.this::signalAndFinish,
                                    250L
                            );
                        }
                    }
            );

            // Safety fallback in case a vendor build never returns a callback.
            handler.postDelayed(this::signalAndFinish, 1600L);
        } catch (Throwable ignored) {
            signalAndFinish();
        }
    }

    private void signalAndFinish() {
        if (signalSent) return;
        signalSent = true;

        VoiceSignal.post(this);

        handler.postDelayed(() -> {
            finish();
            overridePendingTransition(0, 0);
        }, 100L);
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }
}
