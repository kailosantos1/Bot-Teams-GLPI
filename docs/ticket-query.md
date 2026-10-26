> Atualização da etapa 5: a seleção agora abre detalhes autorizados, conversa pública e resposta textual com confirmação. Ver [ticket-conversation.md](ticket-conversation.md) para o comportamento atual e a migração SQLite v2; os registros abaixo descrevem a entrega da etapa 4 e sua correção.

# Etapa 4 — consulta dos próprios chamados

Implementada localmente em 26/10/2026, com APIs simuladas. Não homologada no Teams/GLPI real.

## Autorização e composição

`main.py` compõe um único BotFrameworkAdapter com SimpleCredentialProvider explícito. O endpoint chama `IdentityIngress.dispatch` uma vez e preserva sua resposta. O callback disponibiliza o resolver somente durante a atividade. Menu e abertura não pedem vínculo; a autorização legada continua exclusiva da abertura. `bot/ticket_consult.py` intercepta a consulta antes de interpretar payloads/respostas do menu, somente sem formulário em andamento e em conversa pessoal Teams. O formulário mantém a confirmação explícita de interrupção já existente.

Cada listagem, atualização, paginação e seleção resolve novamente a identidade: autenticação habilitada e claims do adapter, configuração válida, tenant permitido, remetente conferido via TeamsInfo, vínculo administrativo ativo em SQLite e usuário GLPI ativo/não excluído. Não há criação automática de vínculos nem fallback por nome/e-mail/UPN. A leitura GLPI e SQLite ocorre em `asyncio.to_thread`, sem transação SQLite durante HTTP. TeamsInfo tem timeout de dez segundos.

Configurações existentes necessárias: `MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`, `MICROSOFT_APP_TENANT_ID`, `IDENTITY_ALLOWED_TENANT_ID`, `IDENTITY_DB_PATH`, `GLPI_URL`, `GLPI_APP_TOKEN`, `GLPI_USER_TOKEN`. Ver [identity.md](identity.md) para inicialização e administração dos vínculos. O banco deve ser previamente inicializado e ter vínculo aprovado pelo administrador; o servidor não cria banco/vínculos automaticamente. Um banco ausente ou inválido nega acesso.

Para desativar somente a consulta, deixar `IDENTITY_ALLOWED_TENANT_ID` vazio e reiniciar. O menu continua mostrando a opção, que responde com acesso não confirmado. Não remover as credenciais da abertura. O novo mecanismo não torna segura a identificação legada da abertura.

## Contrato adotado

API REST v1 do **GLPI 10.0.18** como referência fixa; a versão implantada permanece desconhecida. Fontes oficiais consultadas:

- [apirest.md na tag 10.0.18](https://github.com/glpi-project/glpi/blob/10.0.18/apirest.md): initSession/killSession, search, critérios aninhados, forcedisplay e paginação de subitens.
- [CommonITILObject.php](https://github.com/glpi-project/glpi/blob/10.0.18/src/CommonITILObject.php): opções de pesquisa 2=id, 4=requerente individual (join condicionado por tipo), 12=status; constantes de status.
- [CommonITILActor.php](https://github.com/glpi-project/glpi/blob/10.0.18/src/CommonITILActor.php): REQUESTER=1, ASSIGN=2, OBSERVER=3.
- [Ticket.php](https://github.com/glpi-project/glpi/blob/10.0.18/src/Ticket.php): relação de usuários Ticket_User, separada de Group_Ticket.

`GET /search/Ticket` exige opção 4 igual ao usuário resolvido, exclusão desativada (`is_deleted=0`) e grupo OR dos quatro status permitidos (critério AND com requerente). Não há pesquisa global de fallback. Coleta todas as páginas da pesquisa filtrada antes de ordenar. Para cada candidato, `GET /Ticket/{id}` confere ID, exclusão e status; `GET /Ticket/{id}/Ticket_User` percorre todas as páginas, validando Content-Range e IDs únicos, e exige users_id exato, tickets_id exato e type=REQUESTER. Não consulta Group_Ticket, criador, FormAnswer ou origem: chamados antigos abertos pelo portal também podem aparecer.

| Código | Constante | Exibição |
| --- | --- | --- |
| 1 | INCOMING | Novo |
| 2 | ASSIGNED | Em atendimento |
| 3 | PLANNED | Em atendimento |
| 4 | WAITING | Pendente |
| 5 | SOLVED | Excluído da consulta |
| 6 | CLOSED | Excluído da consulta |

Status desconhecidos e tickets excluídos são omitidos. Respostas incompletas, falhas nas páginas e limites excedidos geram erro, sem falsa ausência/lista parcial. Na seleção, ticket removido/404 é indisponível; falhas de transporte são erro temporário.

## Navegação e limites

Até cinco chamados por página; ordem por date_mod decrescente e ID decrescente no desempate. Exibe somente número, título e situação. O título é limitado a 120 caracteres e convertido a texto com conjunto conservador de caracteres, removendo sintaxe HTML/Markdown, URLs e menções. Não se apresenta contagem total.

Exemplo:

```text
📋 Seus chamados em andamento:

1 — Impressora não imprime
Chamado #1234 · Em atendimento

9 — Próximos
8 — Atualizar
0 — Voltar ao menu
```

Itens usam 1–5; anteriores=7, próximos=9, atualizar=8; após seleção, retornar à lista=6. Há botões messageBack e palavras equivalentes anunciadas. Selecionar só informa: “Você selecionou o chamado #1234. A visualização dos detalhes será disponibilizada na próxima etapa.”

Falha de identificação: “Não consegui confirmar seu acesso aos chamados. Entre em contato com o suporte de TI.” Ausência: “✅ Você não tem chamados em aberto no momento.” Falha de API/limite: “Não consegui consultar seus chamados agora. Tente novamente em instantes.” Recurso retirado: “Esse chamado não está disponível para consulta. Atualize a lista.”

Estado `TicketQueryState` separado de UserProfile, em MemoryStorage. Guarda apenas IDs da página, offset, versão aleatória, validade de cinco minutos e associação tenant/object ID/usuário GLPI/conversa/remetente. Nenhum título ou conteúdo é persistido nesse estado. Botão exige versão atual e seleção pertence à página atual; IDs arbitrários não autorizam acesso. Sair invalida a lista; reinício perde a sessão e exige atualização. Identidade substituída, conversa diferente ou expiração invalidam seleções. A seleção refaz identidade e conferência do ticket/requerente/status.

Cada operação de navegação refaz a pesquisa filtrada. Limites: 200 candidatos, 200 relações por ticket, 500 requisições e orçamento monotônico de 60 segundos para iniciar/concluir chamadas; timeout HTTP até cinco segundos por chamada, mais até cinco para encerramento de sessão. Requests usa timeout de conexão/leitura, não um prazo absoluto para corpo transmitido lentamente; isso deve ser observado na homologação. Nenhum redirecionamento é seguido. Não há escrita de dados GLPI, apenas abertura/encerramento de sessão de API.

Premissa: instância única, disco persistente para vínculos e MemoryStorage local para navegação. Não há snapshot transacional entre chamadas GLPI: alterações simultâneas podem mudar páginas; revalidação limita acesso no momento das leituras e não promete consistência transacional. Multiworker, recuperação após reinício, detalhes, histórico, anexos da consulta, respostas e notificações ficam fora desta etapa.

## Testes e investigação do travamento

Fixtures do contrato estão em `tests/test_ticket_query.py`; navegação/estado e revalidação em `tests/test_ticket_consult.py`. Mocks de Teams/GLPI, bancos temporários nos testes de identidade, HTTP/sockets bloqueados. Não executados os utilitários antigos que podem acessar GLPI real. Os 30 testes de menu foram preservados e atualizados nas expectativas substituídas da opção 2; continuam incluindo três formulários completos simulados.

O travamento foi reproduzido dentro do sandbox com um programa mínimo, sem testes ou rede: `asyncio.run(main())`, cujo main apenas aguarda `asyncio.to_thread(lambda: 42)`. Imprime 42, mas trava ao fechar o executor. Faulthandler da suíte mostrou o loop em `Runner.close` / `_tearDownAsyncioRunner`, depois de um teste já aprovado. O mesmo programa termina com “done” fora do sandbox; a suíte original de identidade também termina e aprova 21 testes fora dele. Evidência de limitação do sandbox neste ambiente, sem atribuir uma causa interna não demonstrada. Não foram removidos testes nem substituído to_thread.

Comando da suíte completa (executado fora desse sandbox para permitir encerramento do executor):

```sh
python3 -m unittest tests.test_menu tests.test_identity tests.test_identity_sdk tests.test_ticket_query tests.test_ticket_consult -q
```

Resultados finais registrados no AGENTS.md. Os testes SDK são condicionais e não comprovam JWT real.

## Homologação pendente

Confirmar versão real do GLPI e opções de `/listSearchOptions/Ticket` com permissões do usuário técnico; formato de pesquisa, códigos de status, campos do ticket, relação Ticket_User, Content-Range e comportamento de coleção vazia/404. Conferir entidades/perfil para visibilidade de todos os chamados próprios esperados. Fixtures locais não comprovam esse contrato implantado.

Executar inspeção SDK com o interpretador de produção e homologar JWT válido/inválido, autenticação desabilitada, tenant permitido/proibido, TeamsInfo real e vínculos administrativos. Conferir renderização e messageBack no Teams, títulos adversos, expiração, operação de revogação e os três formulários/anexos reais em etapa autorizada. Validar latência e limites com dados representativos. Não foi feita chamada real a GLPI/Teams nem instalação de dependências nesta implementação.

## Correção dos testes com SDK instalado

A execução original de 82 testes sem SDK não cobria os accessors reais. No venv local do usuário (Python 3.12.3; Bot Framework core/schema/connector 4.17.1; aiohttp 3.14.5; msrest 0.7.1), a descoberta reproduziu 39 falhas e oito erros. O menu deixava TicketQueryState real receber MockTurnContext, enquanto a suíte de consulta deixava todos os accessors reais. A ausência de `turn_state` era a primeira exceção; mensagens genéricas causavam falhas secundárias, incluindo sanitização.

Foi escolhida a substituição integral dos accessors, sem tentar completar parcialmente o contexto falso. `tests/support.py` fornece estado novo por teste, compartilhado nas referências certas de dialogs/ticket_consult e restaurado com addCleanup. As duas suítes usam o helper e não importam mais outra suíte para obter fixtures. Não foi necessário alterar o bot, a sanitização ou a autorização.

A fixture SDK também confundia os nomes JSON de tenant: ConversationAccount usa `tenantID`; TeamsChannelAccount usa `tenantId`; ambos expõem `tenant_id` no Python. A fixture foi corrigida e cinco testes adicionados para construção/desserialização, ausência opcional e divergências. A autorização continua exigindo tenant válido em channelData e membro Teams, dentro do contexto autenticado; tenant da conversa, se presente, também precisa concordar.

Resultados separados: menu **30**, consulta **16**, identidade **21**, SDK **10**, serviço de consulta **10**, todos aprovados. Comando solicitado:

```sh
venv/bin/python -m unittest discover -s tests -v
```

**87 aprovados, zero falhas, zero erros, zero pulados**. Ordem inversa também aprovada, com restauração dos accessors verificada após a execução. `venv/bin/python -m pip check`: **No broken requirements found**. Nenhuma instalação ou atualização nesta correção; aiohttp, já instalado pelo usuário, foi registrado em requirements.txt com a versão mínima localmente verificada. A execução assíncrona ocorreu fora do sandbox afetado pelo travamento de encerramento já documentado, mantendo mocks e bloqueio de rede dos testes.

Isso confirma contratos locais do SDK com autenticação simulada. Não substitui homologação JWT/Teams/GLPI, confirmação do runtime de produção ou do contrato GLPI implantado. Nenhum envio ou consulta externa real foi realizado. O escopo da etapa permanece o mesmo.
