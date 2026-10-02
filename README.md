# AI3 Voice Bridge

Pequeno bridge Android para o projeto W-AI3 Pro + CyanBridge + ChatGPT.

## Objetivo

Converter o `android.intent.action.VOICE_COMMAND` enviado pelo CyanBridge em uma notificação com a palavra-chave:

`AI3_CHATGPT_VOICE`

O Samsung Modos e Rotinas detecta essa notificação e executa a ação interna `ChatGPT -> Voz`.

Fluxo alvo:

`Hey Cyan / botão AI3 -> CyanBridge -> VOICE_COMMAND -> AI3 Voice Bridge -> AI3_CHATGPT_VOICE -> Samsung Routine -> ChatGPT Voice`

## v1.0.2 - wake + dismiss trusted keyguard

A v1.0.1 provou que o trigger chegava corretamente ao ChatGPT, mas no Galaxy S24+ o Voice ainda aguardava o desbloqueio manual.

A v1.0.2:
- executa a Activity transparente acima da lock screen;
- liga a tela temporariamente com `setTurnScreenOn(true)`;
- solicita a dispensa do Keyguard somente depois de `onResume()`;
- mantém `FLAG_DISMISS_KEYGUARD` como compatibilidade adicional para One UI;
- aguarda a dispensa antes de publicar `AI3_CHATGPT_VOICE`;
- preserva fallback caso a política do Android/Samsung ainda exija autenticação.

## Instalação

1. Atualize o APK no Galaxy S24+.
2. Abra `AI3 Voice Bridge` uma vez e confirme notificações.
3. Mantenha a rotina Samsung:
   - SE: notificação do AI3 Voice Bridge com `AI3_CHATGPT_VOICE`
   - ENTÃO: `ChatGPT -> Voz`
4. Teste primeiro o botão físico com a tela bloqueada.
5. Depois teste `Hey Cyan` com a tela bloqueada.

## Build

O workflow `.github/workflows/build-apk.yml` executa `gradle :app:assembleDebug` e publica o APK como artifact `ai3-voice-bridge-debug`.
