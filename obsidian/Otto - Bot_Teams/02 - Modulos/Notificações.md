# Módulo de notificações

[[obsidian/02 - Modulos/Indice|← Módulos]] · [[obsidian/03 - Fluxos/Notificações|Fluxo completo]]

## Composição

- `notifications/policy.py`: exige configuração opt-in, grupos de autores e usuários de integração; verifica publicidade, autor e exclusões.
- `notifications/capture.py`: grava uma referência pessoal autenticada e sanitizada somente após resolução bem-sucedida.
- `notifications/glpi.py`: snapshot de tickets e acompanhamentos; valida associação direta `Group_User`.
- `notifications/worker.py`: cria baseline, classifica eventos, gerencia reserva e envia pelo adapter de saída.
- `notifications/manager.py`: inicializa worker dedicado em thread/event loop próprio nos eventos de startup/shutdown do FastAPI.
- `notifications/lifecycle.py`: drena operações em threads sem liberar lock antes de concluir.
- `tools/notifications_lock.py`: lock de sistema operacional por caminho do banco; arquivo lock persistente.

## Garantias implementadas e limites

Fila e baseline são persistidos no mesmo SQLite das identidades. O primeiro snapshot completo não envia histórico. O worker verifica usuário, requerente, status, followup e grupo de autor novamente antes de enviar. Privados e conta de integração são excluídos. Falha de classificação não vira “não membro”.

Antes do POST de saída, o estado `submitting` é gravado como fence. Timeout/falha após esse ponto pode ter enviado; vira `uncertain` e não há replay automático. Isso evita repetição cega, mas não oferece entrega exatamente uma vez nem transação entre GLPI e Teams.

O worker só envia avisos em conversas pessoais capturadas; um botão de notificação seleciona token opaco servidor-side e o ticket é reautorizado antes de abrir detalhes.

## Limites por ciclo

Constantes no `Worker`: até 10 destinatários, 50 tickets e 20 envios reservados; orçamento cooperativo de 250 chamadas e 120 segundos no ciclo. A fase de observação usa até 150 chamadas/60 segundos. Listas GLPI são limitadas a 200 itens; lease é de 15 minutos. Envio Connector tem timeout de 15 segundos e retentativa/backoff é decidido pela fila, não pelo msrest. Esses limites são de código e não são garantia de latência absoluta (Requests pode aguardar leitura do corpo).
