# AI3 Voice Bridge

Pequeno bridge Android para o projeto W-AI3 Pro + CyanBridge + ChatGPT.

## Objetivo

Converter o `android.intent.action.VOICE_COMMAND` enviado pelo CyanBridge em uma notificação com a palavra-chave:

`AI3_CHATGPT_VOICE`

O Samsung Modos e Rotinas detecta essa notificação e executa a ação interna `ChatGPT -> Voz`.

Fluxo alvo:

`Hey Cyan / botão AI3 -> CyanBridge -> VOICE_COMMAND -> AI3 Voice Bridge -> AI3_CHATGPT_VOICE -> Samsung Routine -> ChatGPT Voice`

## v1.0.1 - tela bloqueada

Antes de emitir o sinal, o bridge tenta dispensar o Keyguard usando `KeyguardManager.requestDismissKeyguard()`.

No Galaxy S24+ com o AI3 configurado como dispositivo confiável, o objetivo é permitir:

`Hey Cyan -> dispensar lock screen confiável -> Rotina Samsung -> ChatGPT Voice`

Se o Android/Samsung não permitir a dispensa, o app mantém o fallback anterior e apenas emite o sinal.

## Instalação

1. Baixe o APK gerado pelo GitHub Actions.
2. Instale/atualize no Galaxy S24+.
3. Abra `AI3 Voice Bridge` uma vez.
4. Permita notificações.
5. Em Samsung Modos e Rotinas, mantenha `AI3 Voice Bridge` nos aplicativos monitorados.
6. Mantenha a palavra-chave `AI3_CHATGPT_VOICE` e a ação `ChatGPT -> Voz`.
7. Teste primeiro pelo botão físico com a tela bloqueada.
8. Depois teste `Hey Cyan` com a tela bloqueada.

## Build

O workflow `.github/workflows/build-apk.yml` executa `gradle :app:assembleDebug` e publica o APK como artifact `ai3-voice-bridge-debug`.
