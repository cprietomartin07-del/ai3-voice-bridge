package com.cprieto.ai3voicebridge;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int REQ_NOTIFICATIONS = 1001;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(48, 72, 48, 48);
        root.setGravity(Gravity.CENTER_HORIZONTAL);

        TextView title = new TextView(this);
        title.setText("AI3 Voice Bridge");
        title.setTextSize(28f);
        root.addView(title, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView info = new TextView(this);
        info.setText("Captura android.intent.action.VOICE_COMMAND e publica AI3_CHATGPT_VOICE para o Samsung Modos e Rotinas.");
        info.setTextSize(17f);
        LinearLayout.LayoutParams infoParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        infoParams.setMargins(0, 48, 0, 48);
        root.addView(info, infoParams);

        Button permission = new Button(this);
        permission.setText("Permitir notificações");
        permission.setOnClickListener(v -> requestNotifications());
        root.addView(permission, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        Button test = new Button(this);
        test.setText("Enviar sinal de teste");
        LinearLayout.LayoutParams testParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        testParams.setMargins(0, 24, 0, 0);
        test.setOnClickListener(v -> {
            if (!VoiceSignal.canNotify(this)) {
                Toast.makeText(this, "Primeiro permita as notificações.", Toast.LENGTH_SHORT).show();
                requestNotifications();
                return;
            }
            boolean posted = VoiceSignal.post(this);
            Toast.makeText(this, posted ? VoiceSignal.KEYWORD : "Falha ao publicar notificação", Toast.LENGTH_SHORT).show();
        });
        root.addView(test, testParams);

        setContentView(root);
        if (!VoiceSignal.canNotify(this)) requestNotifications();
    }

    private void requestNotifications() {
        if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQ_NOTIFICATIONS);
        } else {
            Toast.makeText(this, "Notificações já permitidas.", Toast.LENGTH_SHORT).show();
        }
    }
}
