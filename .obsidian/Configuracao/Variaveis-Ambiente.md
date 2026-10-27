# Configuração - Variáveis de Ambiente

## Arquivo de Configuração

- `.env` (não versionado) - Valores reais
- `.env.example` (versionado) - Template

## Variáveis Obrigatórias (Abertura Legada)

| Variável | Tipo | Descrição |
|---|---|---|
| `MICROSOFT_APP_ID` | string | App ID da aplicação Bot Framework |
| `MICROSOFT_APP_PASSWORD` | string | App Password/Secret |
| `MICROSOFT_APP_TENANT_ID` | string | Tenant da aplicação Bot |

## Variáveis GLPI

| Variável | Tipo | Descrição |
|---|---|---|
| `GLPI_URL` | string | URL base do GLPI (ex: https://glpi.empresa.com) |
| `GLPI_APP_TOKEN` | string | Token da aplicação GLPI |
| `GLPI_USER_TOKEN` | string | Token do usuário API GLPI |

## Variáveis de Identidade

| Variável | Tipo | Padrão | Descrição |
|---|---|---|---|
| `IDENTITY_ALLOWED_TENANT_ID` | string | "" | Tenant Entra permitido (vazio desabilita consulta/resposta) |
| `IDENTITY_AUTO_LINK_ENABLED` | bool | `false` | Habilita vínculo automático por e-mail |
| `IDENTITY_DB_PATH` | string | `data/identity.sqlite3` | Caminho do banco SQLite |

## Variáveis de Notificações

| Variável | Tipo | Padrão | Descrição |
|---|---|---|---|
| `NOTIFICATIONS_ENABLED` | bool | `false` | Habilita worker de notificações |
| `NOTIFICATIONS_SUPPORT_GROUP_IDS` | string | "" | IDs de grupos GLPI separados por vírgula |
| `NOTIFICATIONS_INTEGRATION_IDS` | string | "" | IDs de usuários de integração separados por vírgula |
| `NOTIFICATIONS_INTERVAL` | int | `60` | Intervalo do worker em segundos |

## Carregamento

Configuração via `config.py` usando `pydantic-settings`. Lê `.env` automaticamente.

## Observações de Segurança

- **Nunca commitar `.env`**
- **Nunca logar tokens/credenciais**
- **Proteger banco SQLite e backups**
- **Usar HTTPS em produção**
