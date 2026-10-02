# AI3 Voice Bridge

Pequeno bridge Android para o projeto W-AI3 Pro + CyanBridge + ChatGPT.

## Objetivo

Converter o `android.intent.action.VOICE_COMMAND` enviado pelo CyanBridge em uma notificação com a palavra-chave:

`AI3_CHATGPT_VOICE`

O Samsung Modos e Rotinas detecta essa notificação e executa a ação interna `ChatGPT -> Voz`.

Fluxo alvo:

`Hey Cyan / botão AI3 -> CyanBridge -> VOICE_COMMAND -> AI3 Voice Bridge -> AI3_CHATGPT_VOICE -> Samsung Routine -> ChatGPT Voice`

## Instalação

1. Baixe o APK gerado pelo GitHub Actions.
2. Instale no Galaxy S24+.
3. Abra `AI3 Voice Bridge` uma vez.
4. Permita notificações.
5. Em Samsung Modos e Rotinas, adicione `AI3 Voice Bridge` aos aplicativos monitorados pela condição de notificação recebida.
6. Mantenha a palavra-chave `AI3_CHATGPT_VOICE` e a ação `ChatGPT -> Voz`.
7. Toque em `Enviar sinal de teste` no app e valide se o ChatGPT Voice abre.
8. Depois teste o `VOICE_COMMAND` real do CyanBridge.

## Build

O workflow `.github/workflows/build-apk.yml` executa `gradle :app:assembleDebug` e publica o APK como artifact `ai3-voice-bridge-debug`.
