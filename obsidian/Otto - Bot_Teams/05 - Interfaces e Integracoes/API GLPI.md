# Integração REST do GLPI

[[obsidian/05 - Interfaces e Integracoes/Indice|← Interfaces]] · [[obsidian/Inicio|Início]]

## Contrato de referência

Os serviços indicam GLPI **10.0.18 REST v1**. A versão real instalada neste projeto/servidor não é conhecida; endpoints, códigos de status, cabeçalhos, entidades, paginação e permissões precisam ser homologados.

Autenticação usa `initSession`, `App-Token` e `user_token`, então a requisição usa `Session-Token` e ao final chama `killSession`. Leitura de conteúdo do ticket/conversa pede `X-GLPI-Sanitized-Content: false` e sanitiza localmente.

## Abertura

- Formcreator: `POST /PluginFormcreatorFormanswer` com ID do formulário e campos `formcreator_field_<id>`.
- Descoberta do ticket: `GET /PluginFormcreatorFormAnswer/{formanswer_id}/Item_Ticket`.
- Requerente: relação `POST /Ticket/{ticket_id}/Ticket_User` tipo requerente; remoção posterior pode retirar atores do bot.
- Documentos: `POST /Document`, depois `POST /Document_Item` para ligar ao Ticket.
- Acompanhamento de origem Teams: `POST /ITILFollowup`.

Operações após o FormAnswer são efeitos separados; não existe rollback distribuído se uma delas falhar.

## Consulta, conversa e resposta

- Pesquisa de tickets: `/search/Ticket`, criteria de requerente (opção 4), status (opção 12) e `is_deleted=0`; ticket individual `/Ticket/{id}`.
- Revalidação requer todos os registros de `/Ticket/{id}/Ticket_User` e `type=1`.
- Histórico: `/Ticket/{id}/ITILFollowup`, público apenas quando `is_private` é explicitamente inteiro/string `0`.
- Resposta: `POST /ITILFollowup`, `itemtype=Ticket`, ID obtido do estado autorizado, `is_private=0`, `_no_reopen=true`; `users_id` não é definido pelo bot. O autor nativo é a conta do token GLPI.

Status usados no fluxo de consulta: 1 Novo; 2 e 3 Em atendimento; 4 Pendente. Outros estados são excluídos pelo conjunto codificado. Isso deve ser conferido contra as opções/status da instalação.

## Notificações

Worker lê `/Ticket/{id}/ITILFollowup`, confirma cada registro pelo ID `/ITILFollowup/{id}` e verifica associação direta do autor por `/User/{author_id}/Group_User`. Para classificar associação, valida todas as páginas; nome de grupo ou subgrupo não é usado.

## Limites do cliente

`TicketQuery`: até 200 registros por coleção, 500 chamadas e orçamento cooperativo de 60 s por sessão; leituras com timeout de até 5 s e sem redirecionamento. O timeout de Requests não é prazo absoluto contra corpo lento. Notificações acrescentam orçamento por ciclo. Respostas podem ser parciais na abertura e não são uma transação.

Código: [services/ticket_query.py](../../../services/ticket_query.py#L19), [services/ticket_conversation.py](../../../services/ticket_conversation.py#L18), [notifications/glpi.py](../../../notifications/glpi.py#L9), [services/glpi_service.py](../../../services/glpi_service.py#L16).
