# Módulos Principais

## Estrutura de Diretórios

```
Bot-Teams-GLPI/
├── main.py              # Entrada FastAPI/Bot
├── config.py            # Configurações
├── config/
│   └── forms.yaml       # Definição dos formulários
├── bot/                 # Lógica do bot
├── identity/            # Sistema de identidade
├── services/            # Integração GLPI
├── notifications/       # Worker de notificações
├── tools/               # Ferramentas CLI administrativas
└── tests/               # Testes
```

## Módulo `bot/`

| Arquivo | Responsabilidade |
|---|---|
| `dialogs.py` | Processador dinâmico, roteamento, fluxo de formulários |
| `state.py` | Estados (ConversationState, UserState, NavState, TicketQueryState, etc.) |
| `cards.py` | Geração de HeroCards |
| `auth.py` | Autorização legada por domínio/grupos |
| `glpi_auth.py` | Consultas GLPI para autenticação |
| `ticket_consult.py` | Consulta de chamados próprios |
| `ticket_detail.py` | Detalhes, histórico, resposta |
| `ticket_presentation.py` | Formatação visual |
| `notification_actions.py` | Ações de clique em notificações |
| `attachments.py` | Download/classificação de anexos |
| `activity_attachments.py` | Classificação de anexos em atividades |
| `utils.py` | Utilitários de formatação |
| `dialog_constants.py` | Constantes |

## Módulo `identity/`

| Arquivo | Responsabilidade |
|---|---|
| `ingress.py` | Interceptação e resolução de identidade |
| `service.py` | Lógica de resolução de identidade |
| `store.py` | Persistência SQLite com migrações |
| `glpi.py` | Leitura de usuários GLPI |
| `email_lookup.py` | Busca automática por e-mail |
| `notifications.py` | Referências para notificações |
| `replies.py` | Gerenciamento de operações de resposta |
| `diagnostics.py` | Diagnósticos seguros |

## Módulo `services/`

| Arquivo | Responsabilidade |
|---|---|
| `glpi_service.py` | Criação de FormAnswer/tickets, documentos |
| `ticket_query.py` | Consulta filtrada por requerente |
| `ticket_conversation.py` | Histórico ITILFollowup público, envio de resposta |
| `ticket_content.py` | Sanitização HTML/texto |
| `reply_sender.py` | Envio atômico com controle de estado |

## Módulo `notifications/`

| Arquivo | Responsabilidade |
|---|---|
| `worker.py` | Worker dedicado |
| `policy.py` | Política de autores por grupos |
| `glpi.py` | Detecção de novos followups |
| `queue.py` | Gerenciamento de fila |

## Módulo `tools/`

| Arquivo | Responsabilidade |
|---|---|
| `identity_links.py` | CLI para gerenciar vínculos |
| `notifications.py` | CLI para gerenciar notificações |
| `reply_operations.py` | CLI para limpeza de respostas |
| `inspect_identity_sdk.py` | Inspeção do SDK Bot Framework |
| `inspect_identity_configuration.py` | Inspeção de configuração |
