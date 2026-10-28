# Diagnóstico

[[obsidian/07 - Operacao/Indice|← Operação]] · [[obsidian/Inicio|Início]]

## Primeiro verificar sem vazar informação

- Confirme o interpretador e diretório de trabalho do processo efetivo.
- `GET /health` comprova somente resposta do processo; `GET /api/status` contém indicadores simples, não teste GLPI/Teams.
- Use `python -m tools.inspect_identity_sdk` para inspecionar SDK no interpretador escolhido (local, sem credenciais/rede).
- Use `python -m tools.inspect_identity_configuration` para presença/schema sem imprimir valores; `--db-path` imprime apenas caminho. A inspeção lê configuração local, mas não altera/migra o banco.
- Conferir ACL, arquivo/caminho SQLite, porta 3000, imports/certificados no host efetivo.

Estes comandos foram identificados nos arquivos operacionais; não executados nesta tarefa. O comando de diagnóstico pode carregar `.env`; nunca copie sua saída sensível para tickets ou logs.

## Categorias de falha

- **Identidade:** configuração/tenant/autenticação, TeamsInfo indisponível, vínculo ausente/revogado, usuário GLPI inativo/inexistente ou auto-link ambíguo.
- **Consulta:** estado da tela expirou, autorização por requerente falhou, status excluído, limite/paginação/timeout GLPI.
- **Resposta:** texto inválido, anexo real recusado, vínculo mudou, ou resultado `uncertain` após possível envio.
- **Notificação:** opt-in/grupos incompletos, referência desativada, lease ocupado, associação de autor inconclusiva ou entrega incerta.
- **Execução:** caminho de banco, permissões, versão SDK no runtime, porta/processo, arquivos externos/onedir e shutdown.

Os logs do caminho de identidade usam códigos allowlisted; não registre token, conteúdo do ticket, anexo, referência de conversa ou saída bruta API. Logging legado de abertura ainda pode conter dados de usuário/respostas; isso é limitação de código existente e não deve ser reproduzida.

## Não fazer

- Não apagar banco, recriar vínculo ou limpar lock para contornar erro sem backup e diagnóstico.
- Não repetir cegamente uma resposta/notificação incerta.
- Não usar scripts diagnósticos de `Extensoes/` contra GLPI real como teste.
- Não interpretar 200 de `/health` como homologação.

[[obsidian/08 - Pendencias/Homologação|Roteiro de homologação]]
