# CyanBridge AI3 persistence patch

Patch local do projeto AI3 para o CyanBridge upstream, fixado no commit
`d7e726e923943b94ae32cd1e42c20b3ee6343bd7`.

Corrige os dois sintomas observados no W-AI3 Pro:

- o `Hey Cyan` deixa de responder depois de algum tempo;
- botão físico e wake word deixam de funcionar quando a Activity do CyanBridge é encerrada.

A correção adiciona um foreground service persistente, mantém um listener de hardware fora
da MainActivity, rearma periodicamente `aiVoiceWake(true, true)`, preserva o BLE/reconnect e
encaminha o evento AI `0x03` diretamente para `com.cprieto.ai3voicebridge`.

O serviço mostra uma notificação de baixa prioridade:
`CyanBridge • AI3 ativo`.

Force-stop manual do CyanBridge continua interrompendo o serviço por regra do Android.
