# Atualização e backup

## Backup consistente do SQLite
- Preferir processos parados ou API de backup.
- Arquivos relacionados: `identity.sqlite3`, `-wal`, `-shm`, lock.
- Preservar `.env`, `config/forms.yaml` e banco existente.

## Atualização do código/build
1. Backup do banco e configuração.
2. Atualizar código/build.
3. Gerar executável no Windows.
4. Parar o serviço antes da substituição.
5. Layout onefile: substituir `Otto.exe` inteiro.
6. Layout onedir (futuro): substituir executável e `_internal` juntos, vindos do mesmo build.
7. Não misturar arquivos de builds diferentes.
8. Preservar `.env`, `config/` e `data/` externos; não apagar a pasta de instalação inteira.

## Validação e retorno
- Verificar saúde (`/health`, `/api/status`).
- Testar abertura, consulta, resposta e notificação.
- Em falha, reverter executável e, se necessário, banco compatível com schema anterior.
- Migrações são incrementais; não substituir banco por vazio.

## Referências
- [[04 - Gerar executável]], [[05 - Serviço Windows NSSM]], [[09 - Validação manual]]
