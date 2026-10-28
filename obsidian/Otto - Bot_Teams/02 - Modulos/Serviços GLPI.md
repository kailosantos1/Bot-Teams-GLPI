# Serviços GLPI

[[obsidian/02 - Modulos/Indice|← Módulos]] · [[obsidian/05 - Interfaces e Integracoes/API GLPI|Contratos GLPI]]

## Abertura via Formcreator

[GLPIService](../../../services/glpi_service.py#L16) inicia uma sessão, opcionalmente localiza requerente pelo e-mail recebido do caminho legado, consulta perguntas para identificar tipos, normaliza valores e cria `PluginFormcreatorFormanswer`. Em seguida procura o ticket por `Item_Ticket`; somente esse ID real é exibido.

Depois da criação, pode incluir requerente, remover ator do bot, carregar documentos, vinculá-los ao ticket e acrescentar acompanhamento público de origem Teams. Operações posteriores não são transacionais com FormAnswer: podem falhar parcialmente sem recriar a solicitação.

## Consulta e conversa

- `services/ticket_query.py`: leitura de tickets em que o usuário é requerente individual, filtros de status/exclusão e validação de todas as relações `Ticket_User`.
- `services/ticket_conversation.py`: detalhes autorizados, `ITILFollowup` público e POST de resposta.
- `services/ticket_content.py`: conversão de HTML GLPI em texto passivo, retirada de recursos ativos, redação conservadora de URLs e extração estrutural da descrição Formcreator.
- `services/reply_sender.py`: coordena a reserva persistente e o ponto de envio.

As chamadas de leitura repetem autorização de requerente e status. Grupo, observador ou atribuição técnica não substituem a condição de requerente.

## Autorização antiga

`bot/glpi_auth.py` e `bot/auth.py` são um subsistema distinto: consulta usuários e e-mails por lista/cache e tem busca parcial por nome. É usado pela validação de domínio/cadastro da abertura. Não deve ser promovido a prova de identidade para consulta.

Ver [[obsidian/03 - Fluxos/Navegação e abertura|Abertura]] · [[obsidian/03 - Fluxos/Consulta e resposta|Consulta/resposta]] · [[obsidian/05 - Interfaces e Integracoes/API GLPI|Endpoints e ressalvas]]
