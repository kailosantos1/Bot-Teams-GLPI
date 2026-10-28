# Execução e notificações

[[obsidian/07 - Operacao/Indice|← Operação]] · [[obsidian/Inicio|Início]]

## Bot

Comando documentado no README, a partir da raiz:

```sh
venv/bin/python main.py
```

No Windows, use o interpretador do ambiente virtual ou o executável empacotado. Execução direta do módulo inicia Uvicorn em `0.0.0.0:3000`. Endpoints: `POST /api/messages`, `GET /health`, `GET /api/status`. Endpoint de saúde não valida serviços externos.

## Worker de notificações unificado

Quando `NOTIFICATIONS_ENABLED=true` e a política está completa, os eventos startup/shutdown do FastAPI iniciam e encerram o `NotificationManager`. Worker executa em thread/event loop dedicado, não no loop de mensagens do bot. Default de `NOTIFICATIONS_INTERVAL` é 10 segundos; não use `--reload` nem múltiplos workers Uvicorn com este estado local.

## CLI do worker

```sh
venv/bin/python -m tools.notifications once
venv/bin/python -m tools.notifications run --interval 60
venv/bin/python -m tools.notifications once --simulate
venv/bin/python -m tools.notifications cleanup --db data/identity.sqlite3
```

Comandos identificados em README/CLI; nenhum foi executado aqui. `--simulate` não envia Teams, mas pode consultar GLPI e gravar baseline/fila reais: não é teste offline. Em uso regular, não inicie CLI `run` em paralelo com o manager.

## Exclusividade e encerramento

Um arquivo `.notifications.lock` é mantido ao lado do banco, com lock de kernel (`flock` ou `msvcrt`). O arquivo permanece após liberar; arquivo existente não prova worker vivo. Lease SQLite e reservas controlam ciclos/eventos. Shutdown drena threads e pode aguardar o ciclo; não mate a thread Requests por timeout, nem apague lock/banco para liberar operação.

Para pausar/reiniciar uma referência, veja `tools.notifications --help` em ambiente seguro e a CLI descrita no README. Pausar descarta eventos pendentes/reservados; retomar exige nova captura autenticada e baseline nova.
