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
    private boolean dismissRequested = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
        } else {
            getWindow().addFlags(
                    WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                            | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
                            | WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
            );
        }

        // Samsung builds are more reliable when the activity is actually resumed
        // before the keyguard-dismiss request is made.
        getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                        | WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
        );
    }

    @Override
    protected void onResume() {
        super.onResume();

        if (dismissRequested || signalSent) return;
        dismissRequested = true;

        handler.postDelayed(this::dismissKeyguardThenSignal, 250L);
    }

    private void dismissKeyguardThenSignal() {
        KeyguardManager keyguard =
                (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);

        if (keyguard == null || !keyguard.isKeyguardLocked()) {
            handler.postDelayed(this::signalAndFinish, 250L);
            return;
        }

        try {
            keyguard.requestDismissKeyguard(
                    this,
                    new KeyguardManager.KeyguardDismissCallback() {
                        @Override
                        public void onDismissSucceeded() {
                            // Give One UI a moment to fully remove the keyguard
                            // before Samsung Modes & Routines launches ChatGPT Voice.
                            handler.postDelayed(
                                    VoiceCommandActivity.this::signalAndFinish,
                                    500L
                            );
                        }

                        @Override
                        public void onDismissCancelled() {
                            // Keep the old behavior as fallback: ChatGPT is still called,
                            // but Android may wait for manual unlock.
                            handler.postDelayed(
                                    VoiceCommandActivity.this::signalAndFinish,
                                    500L
                            );
                        }

                        @Override
                        public void onDismissError() {
                            handler.postDelayed(
                                    VoiceCommandActivity.this::signalAndFinish,
                                    500L
                            );
                        }
                    }
            );

            // Vendor fallback if no callback arrives.
            handler.postDelayed(this::signalAndFinish, 2500L);
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
        }, 250L);
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }
}
