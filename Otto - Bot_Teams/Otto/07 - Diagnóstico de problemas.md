# Diagnóstico de problemas

## Códigos de falha de identidade
- `identity_unavailable`, `identity_missing`
- `email_missing`, `email_invalid`, `email_no_match`, `email_ambiguous`, `email_changed`, `link_conflict`, `link_revoked`, `auto_link_unavailable`

## Falhas de consulta/resposta/notificações
- Consulta negada: vínculo ausente/inválido, tenant não permitido, usuário GLPI inativo/excluído, status fora de 1-4.
- Resposta: texto vazio/invisível/controles, limite 2000, anexo real, operação incerta.
- Notificações: referência ausente, lease ocupado, política inválida, grupo não configurado.

## Paths, permissões, imports, certificados, porta
- Verificar `IDENTITY_DB_PATH` resolvido, ACL da conta do serviço, existência do banco.
- Usar interpretador que inicia o bot para inspeção.
- Porta 3000 ocupada: verificar processo/serviço.
- Certificados: validar no ambiente Windows real.

## Comandos PowerShell (somente leitura)
```powershell
$Project = 'C:\Automacoes\Bot-Teams-GLPI'
Set-Location -LiteralPath $Project
python -m tools.inspect_identity_sdk
python -m tools.inspect_identity_configuration
python -m tools.inspect_identity_configuration --db-path
# Alternativa, se o servidor usar venv:
# .\venv\Scripts\python.exe -m tools.inspect_identity_sdk
```

## Boas práticas
- Não apagar banco nem recriar vínculos em massa.
- Não reenviar operações incertas cegamente.
- Não expor segredos em logs/tickets.
