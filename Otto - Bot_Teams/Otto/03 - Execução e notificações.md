# Execução e notificações

## Execução unificada
- Comando: `python -u main.py`
- FastAPI/Uvicorn na porta 3000.
- Startup inicia o manager de notificações apenas se `NOTIFICATIONS_ENABLED=true` e política válida.

## Intervalo configurável
- `NOTIFICATIONS_INTERVAL` em segundos, padrão 10.
- Worker periódico usa o mesmo código de `notifications/worker.py`.

## Worker separado para diagnóstico
- `tools/notifications.py once|run [--simulate] [--interval 60]`.
- `--simulate` não envia Teams, mas pode consultar GLPI e gravar baseline/fila reais.
- Lock singleton impede workers duplicados.
- Parar serviço antes de `pause`/`resume`/`cleanup` pela CLI.

## Locks e prevenção de duplicação
- Lock por caminho absoluto do banco: `<banco>.notifications.lock`.
- `flock` no Linux, `msvcrt.locking` no Windows.
- Arquivo persistente; não apagar.
- Lease SQLite de 15 minutos por ciclo.
- Lease e reservas recuperáveis; `submitting` abandonado vira `uncertain`.

## Interpretação dos logs
- Falhas de identidade registram apenas códigos seguros (`bot.identity`).
- Fluxo sensível não registra rascunho, exceções brutas ou conteúdo API.
- Códigos: `identity_unavailable`, `identity_missing`, `email_missing`, `email_invalid`, `email_no_match`, `email_ambiguous`, `email_changed`, `link_conflict`, `link_revoked`.

## Requisitos para receber notificações
1. Conversa pessoal válida com o bot.
2. Vínculo ativo no SQLite (criado manualmente ou automaticamente, desde que atenda às validações atuais).
3. Resolução segura bem-sucedida na consulta.
4. Captura de referência pessoal pelo SDK autenticado.
5. Usuário GLPI ativo e requerente individual de chamado com status 1-4.
6. Autor do acompanhamento em grupo configurado e não integrante da lista de integração.

## Referências
- [[02 - Instalação e configuração]], [[07 - Diagnóstico de problemas]]
