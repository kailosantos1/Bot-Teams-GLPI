# Entrada e camada do bot

[[obsidian/02 - Modulos/Indice|← Módulos]] · [[obsidian/Inicio|Início]]

## `main.py`

Cria a aplicação FastAPI, compõe adapter/provider, `IdentityIngress`, leitor GLPI e manager de notificações. `authenticated_message` disponibiliza um resolver temporário no contexto; `logic_process_message` verifica se a atividade é mensagem, avalia se precisa da autorização legada e encaminha o texto/payload ao processador. O resolver temporário é removido ao final do callback.

Rotas e detalhes: [[obsidian/01 - Arquitetura/Visão de arquitetura|Arquitetura]] e [[obsidian/05 - Interfaces e Integracoes/API do bot e Teams|API do bot]].

## `bot/dialogs.py`

`DynamicFormProcessor` identifica formulários por palavras-chave, verifica a confirmação inicial, monta perguntas na ordem do YAML, pula dependências não satisfeitas, valida texto/opções, lida com múltipla escolha, coleta anexos e finaliza a solicitação. Em conversa pessoal, implementa navegação; durante um formulário, menu/sair pedem confirmação antes de descartar o estado.

O handler processa payloads notificação antes de consulta e formulário. Formulários ativos têm precedência sobre entrada de consulta e mantêm as respostas/anexos em `UserProfile`. Cartões têm valores e versões validados contra etapa, remetente, canal e conversa.

## Outros componentes de `bot/`

- `state.py`: `ConversationState`/`UserState` em `MemoryStorage`; propriedades `DialogState`, `UserProfile`, `NavState`.
- `cards.py`: `HeroCard`, `messageBack`, menu, confirmação e mensagem final; escapa texto antes de serializar cartão.
- `ticket_consult.py`: seleção da lista pessoal de chamados e estado temporário de navegação.
- `ticket_detail.py`: detalhes, histórico público e captura/envio de texto.
- `notification_actions.py`: trata payloads próprios de notificação antes de formulário e resposta digitada.
- `attachments.py` e `activity_attachments.py`: download na fase de anexos do formulário e classificação conservadora de arquivos reais versus HTML técnico da Activity.
- `auth.py`/`glpi_auth.py`: autorização legada pelo domínio e busca por nome no GLPI; não confundir com a identidade segura exigida para consulta.
- `ticket_presentation.py` e `utils.py`: apresentação e nomes, sem função de autorização.

## Estado efêmero

O estado do bot fica em memória no processo. Reinício pode perder pergunta em andamento, anexos base64, tela de consulta e navegação; ver [[obsidian/04 - Dados/Persistência e modelos|Persistência]].

A autorização legada usa domínios permitidos no código e restrição de cadastro por e-mail/grupo. A busca por nome aceita correspondência parcial; nomes e grupos não são mecanismos de identidade para os novos fluxos de consulta.
