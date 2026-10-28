# Instalação e configuração

## Dependências
- Python 3.12.x, FastAPI, Uvicorn, Bot Framework SDK, Requests, PyYAML, python-dotenv, pydantic-settings.
- Venv recomendado: `venv/Scripts/python.exe` no Windows.

## Variáveis reais do .env
Exemplos fictícios apenas:

```env
MICROSOFT_APP_ID=00000000-0000-0000-0000-000000000000
MICROSOFT_APP_PASSWORD=exemplo
MICROSOFT_APP_TENANT_ID=11111111-1111-1111-1111-111111111111
GLPI_URL=https://glpi.exemplo.local/apirest.php
GLPI_APP_TOKEN=app-token-exemplo
GLPI_USER_TOKEN=user-token-exemplo
IDENTITY_ALLOWED_TENANT_ID=11111111-1111-1111-1111-111111111111
IDENTITY_AUTO_LINK_ENABLED=false
IDENTITY_DB_PATH=data/identity.sqlite3
NOTIFICATIONS_ENABLED=false
NOTIFICATIONS_SUPPORT_GROUP_IDS=
NOTIFICATIONS_INTEGRATION_IDS=
NOTIFICATIONS_INTERVAL=10
```

## Identidade e vínculos
- Vínculo manual: criado por `tools/identity_links.py` (`create`/`replace`), com validação GLPI.
- Vínculo automático: somente se `IDENTITY_AUTO_LINK_ENABLED=true`; exige e-mail Microsoft autenticado, coincidência exata com exatamente um usuário GLPI ativo/não excluído, tenant permitido e conversa pessoal.
- Vínculo ativo existente é revalidado a cada resolução; vínculo revogado não é recriado automaticamente.
- Tenant permitido vazio bloqueia consulta/resposta, sem bloquear abertura.
- E-mail ausente ou inválido bloqueia a associação automática; UPN não é usado como chave.

## Exceções administrativas
- `tools/identity_links.py`: init/create/get/audit/revoke/replace.
- `create`/`replace` validam GLPI antes de ativar; são afirmações administrativas.
- Revogação/reaprovação invalida rascunhos anteriores.

## Grupos de suporte e conta de integração
- `NOTIFICATIONS_SUPPORT_GROUP_IDS`: IDs exatos de grupos GLPI (autores).
- `NOTIFICATIONS_INTEGRATION_IDS`: IDs de usuários de integração, incluindo a conta do `GLPI_USER_TOKEN`.
- Listas não vazias, disjuntas por namespace (grupo vs usuário).

## SQLite e migração
- Caminho padrão `data/identity.sqlite3`, relativo à raiz do projeto/fonte ou ao diretório do executável quando congelado.
- Schema evoluiu v1→v2→v3→v4; migração transacional preserva links/auditoria/operações.
- Instância única, disco local persistente; não usar em réplicas/NFS.
- Não apagar banco para contornar caminho errado.

## Referências
- [[03 - Execução e notificações]], [[07 - Diagnóstico de problemas]], [[06 - Atualização e backup]]
