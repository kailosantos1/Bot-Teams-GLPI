# 01 - Visão Geral

## Sobre o Projeto

O **Byte Bot de Chamados** é um bot para Microsoft Teams que integra com o GLPI via plugin Formcreator para abertura, consulta e acompanhamento de chamados. O bot permite aos usuários abrir chamados diretamente pelo Teams, consultar seus próprios chamados, ler acompanhamentos públicos e enviar respostas textuais confirmadas.

## Objetivo

Facilitar a abertura e o acompanhamento de chamados de TI através de uma interface conversacional no Microsoft Teams, mantendo a integração com o fluxo já existente do GLPI/Formcreator.

## Stack Tecnológica

| Componente | Tecnologia | Versão/Detalhes |
|---|---|---|
| **Linguagem** | Python | 3.12 |
| **Framework Web** | FastAPI + Uvicorn | Recebe mensagens do Bot Framework em `POST /api/messages` |
| **Bot Framework** | Bot Builder SDK | `botbuilder-core`, `botbuilder-schema`, `botframework-connector` 4.17.1 |
| **HTTP Client** | Requests / aiohttp | Chamadas síncronas/assíncronas para GLPI |
| **Configuração** | pydantic-settings + python-dotenv | Carregamento de variáveis `.env` |
| **Validação** | Pydantic | Modelos de configuração |
| **Serialização** | PyYAML | Carregamento de `config/forms.yaml` |
| **Persistência** | SQLite (via módulo `identity/store.py`) | Vínculos de identidade, operações de resposta, notificações |
| **Armazenamento em Memória** | Bot Framework MemoryStorage | Estados de conversa/usuário (se perdem em reinício) |

## Status Atual

- **Abertura de chamados**: Funcionando e preservado (formulários FlexSmart, Manutenção e Cadastro de Novo Colaborador)
- **Consulta de chamados próprios**: Implementado com revalidação de identidade
- **Detalhes e acompanhamento público (ITILFollowup)**: Implementado com controle de privacidade
- **Resposta textual confirmada**: Implementado com controle de envio único
- **Notificações públicas do suporte**: Opcional, desabilitado por padrão
- **Vínculo automático por e-mail**: Opcional, desabilitado por padrão

## Arquivos Principais

| Arquivo | Função |
|---|---|
| [[../main|main.py]] | Ponto de entrada, configuração do adapter, rotas FastAPI, lógica de processamento |
| [[../config|config.py]] | Configurações, carregamento de formulários YAML |
| [[../bot/dialogs|bot/dialogs.py]] | Processador dinâmico de formulários |
| [[../bot/state|bot/state.py]] | Gerenciamento de estado (ConversationState, UserState) |
| [[../bot/glpi_auth|bot/glpi_auth.py]] | Autenticação/consulta de usuários GLPI |
| [[../services/glpi_service|services/glpi_service.py]] | Integração com Formcreator/GLPI (criação de tickets) |
| [[../identity/service|identity/service.py]] | Serviço de resolução de identidade Teams-GLPI |
| [[../identity/ingress|identity/ingress.py]] | Interceptação de atividades autenticadas |
