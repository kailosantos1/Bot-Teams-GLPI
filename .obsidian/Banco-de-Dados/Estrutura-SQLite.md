# Banco de Dados - SQLite (Identity)

## Localização

Padrão: `data/identity.sqlite3` (configurável via `IDENTITY_DB_PATH`)

## Esquema

O banco gerenciado por `identity/store.py` evoluiu através de migrações transacionais. Versão atual: **v4**.

### Tabela `identity_links`

Armazena vínculos entre identidade Teams e usuário GLPI.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | ID interno |
| `tenant_id` | TEXT NOT NULL | Tenant ID do Microsoft Entra |
| `object_id` | TEXT NOT NULL | Object ID (identificador estável) do usuário no Entra |
| `glpi_user_id` | INTEGER NOT NULL | ID do usuário no GLPI |
| `status` | TEXT NOT NULL | `active`, `revoked`, etc. |
| `revision` | INTEGER NOT NULL | Revisão para controle de invalidação |
| `source` | TEXT | Origem do vínculo (manual, auto-link) |
| `created_at` | INTEGER NOT NULL | Timestamp Unix |
| `updated_at` | INTEGER NOT NULL | Timestamp Unix |
| `revoked_at` | INTEGER | Timestamp Unix quando revogado |
| `revoked_by` | TEXT | Quem revogou |

**Constraints:**
- Um usuário GLPI não pode ter dois vínculos ativos no mesmo tenant
- Chave lógica (tenant_id, object_id)

### Tabela `identity_audit`

Auditoria de todas as operações com vínculos.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | ID interno |
| `action` | TEXT NOT NULL | Tipo de ação (create, replace, revoke, auto-link) |
| `tenant_id` | TEXT | Tenant relacionado |
| `object_id` | TEXT | Object ID relacionado |
| `glpi_user_id` | INTEGER | Usuário GLPI relacionado |
| `actor` | TEXT | Quem executou a ação |
| `details` | TEXT | Detalhes JSON |
| `created_at` | INTEGER NOT NULL | Timestamp Unix |

### Tabela `reply_operations`

Controla operações de resposta a chamados com envio atômico.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | TEXT PRIMARY KEY | UUID da operação |
| `tenant_id` | TEXT NOT NULL | Tenant do remetente |
| `object_id` | TEXT NOT NULL | Object ID do remetente |
| `glpi_user_id` | INTEGER NOT NULL | Usuário GLPI do remetente |
| `ticket_id` | INTEGER NOT NULL | ID do ticket |
| `conversation_ref` | TEXT | Referência da conversa |
| `activity_id` | TEXT | ID da atividade Teams (adicionado na v4) |
| `status` | TEXT NOT NULL | `ready`, `reserved`, `submitting`, `sent`, `uncertain`, `cancelled`, `expired` |
| `body_temp` | TEXT | Corpo da resposta temporário (criptografado em uso) |
| `followup_id` | INTEGER | ID do ITILFollowup criado após envio |
| `lease_until` | INTEGER | Lease para worker/processo |
| `attempts` | INTEGER DEFAULT 0 | Número de tentativas |
| `created_at` | INTEGER NOT NULL | Timestamp de criação |
| `updated_at` | INTEGER NOT NULL | Timestamp de atualização |
| `expires_at` | INTEGER NOT NULL | Expiração absoluta (15 min) |

**Índices:**
- Índice único parcial por `(ticket_id, binding_key, activity_id)` para deduplicação por atividade
- Índices por status, lease_until, expires_at

### Tabela `notification_references`

Referências para captura de notificações por destinatário.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | TEXT PRIMARY KEY | ID da referência |
| `tenant_id` | TEXT NOT NULL | Tenant |
| `object_id` | TEXT NOT NULL | Object ID |
| `glpi_user_id` | INTEGER NOT NULL | Usuário GLPI |
| `revision` | INTEGER NOT NULL | Revisão do vínculo |
| `generation` | INTEGER NOT NULL | Geração para invalidação |
| `status` | TEXT NOT NULL | `active`, `disabled`, `paused` |
| `last_seen_at` | INTEGER | Última captura autenticada |
| `created_at` | INTEGER NOT NULL | Timestamp |
| `updated_at` | INTEGER NOT NULL | Timestamp |

### Tabela `notification_events`

Fila de eventos de notificação.

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | TEXT PRIMARY KEY | ID do evento |
| `reference_id` | TEXT NOT NULL | FK para notification_references |
| `ticket_id` | INTEGER NOT NULL | ID do ticket |
| `followup_id` | INTEGER NOT NULL | ID do ITILFollowup |
| `status` | TEXT NOT NULL | `pending`, `reserved`, `submitting`, `sent`, `uncertain` |
| `lease_until` | INTEGER | Lease do worker |
| `attempts` | INTEGER DEFAULT 0 | Tentativas |
| `created_at` | INTEGER NOT NULL | Timestamp |
| `updated_at` | INTEGER NOT NULL | Timestamp |

### Tabela `notification_baselines`

Linha de base para evitar envio de histórico.

| Campo | Tipo | Descrição |
|---|---|---|
| `reference_id` | TEXT NOT NULL | FK |
| `ticket_id` | INTEGER NOT NULL | ID do ticket |
| `max_followup_id` | INTEGER NOT NULL | Maior ID de followup visto |
| `generation` | INTEGER NOT NULL | Geração |
| PRIMARY KEY (reference_id, ticket_id) | | |

## Migrações

As migrações são transacionais e preservam dados existentes:
- **v1 → v2**: Adiciona `reply_operations`
- **v2 → v3**: Adiciona tabelas de notificações
- **v3 → v4**: Adiciona `activity_id` em `reply_operations` com índice único parcial

## Observações

- Banco não versionado no git (`data/` e `*.sqlite3` em `.gitignore`)
- Deve ser protegido com permissões do sistema
- Premissa: instância única com disco persistente
- Não compatível com múltiplas réplicas compartilhando o mesmo arquivo
