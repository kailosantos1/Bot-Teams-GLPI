# Notificações públicas do suporte — etapa 6

Implementação opt-in, **desabilitada por padrão**, sem homologação real. Mantém abertura/Formcreator, consulta, conversa e resposta das etapas anteriores. Não instala aplicativos nem começa conversas com pessoas desconhecidas. Precisa de conversa pessoal válida com o bot, vínculo administrativo aprovado, usuário GLPI ativo e uma resolução segura bem-sucedida na consulta existente. Apenas falar “oi” ou abrir chamado pela identificação legada não habilita notificações.

## Autorização e autores

`IdentityIngress` continua usando uma única passagem pelo adapter. O resolver guarda o resultado somente durante essa atividade; chamadas repetidas compartilham a mesma validação. Somente um resultado seguro `ok`, incluindo a revisão do vínculo revalidado, pode registrar a referência obtida pelo SDK da atividade autenticada. Nenhum dado de texto/botão informa service URL, destinatário ou conversa. Guardam-se aplicação, tenant, object ID, usuário GLPI, revisão, geração aleatória e referência pessoal. Nomes e activity ID são removidos. HTTPS é obrigatório. Nome de exibição, e-mail digitado e correspondência parcial não são usados.

Falha de registro não impede menu/abertura; tenta desabilitar e remover a referência daquele destinatário. Se o próprio banco estiver indisponível, a falha de armazenamento também impede o worker de autorizar envios pelo banco. Não se promete gravar uma revogação enquanto o disco não aceita escritas; restaure o armazenamento antes de retomar o processo. O caminho legado não ganha prova de identidade nova.

A política de autores usa **IDs exatos de grupos GLPI**, em `NOTIFICATIONS_SUPPORT_GROUP_IDS`. O autor deve ter associação atual e direta a pelo menos um grupo configurado; nomes de grupos não são usados na decisão. Não há busca parcial ou inclusão de subgrupos. A variável antiga `NOTIFICATIONS_SUPPORT_IDS` era uma lista de usuários: foi removida de Settings e não é reinterpretada, exigida ou convertida em grupos. Somente a lista antiga não habilita notificações. A configuração nova precisa ser válida e não vazia.

`NOTIFICATIONS_INTEGRATION_IDS` permanece uma lista obrigatória de **usuários** da integração/automações, incluindo a conta de `GLPI_USER_TOKEN`. Integrações nunca geram avisos, mesmo se integrarem grupos permitidos; o destinatário e acompanhamentos com recibo em `reply_operations` também são excluídos antes de consultar grupos. A exclusão não depende de texto “Origem: Teams”. IDs numéricos de grupo e usuário são namespaces distintos; coincidência numérica entre as duas listas não é conflito. Os grupos qualificam **somente os autores**: não autorizam destinatários nem substituem requerente individual, identidade, vínculo, revisão, conversa pessoal e demais revalidações.

São elegíveis apenas acompanhamentos `ITILFollowup` do ticket exato, `itemtype=Ticket`, `items_id` exato, `is_private` inteiro 0 ou string "0", autor permitido e não excluído. Bool, ausência e privacidade desconhecida não são públicos. Se existir `is_deleted`, deve ser explicitamente zero. Registro excluído por DELETE/404 não é enviado. Não se usam tarefas, logs, anexos, timeline bruta ou mudanças de status como gatilhos.

Antes de enviar, o worker consulta usuário ativo/não excluído, ticket e relações completas `Ticket_User`, exigindo requerente individual type=1 e status 1–4/não excluído; técnico, observador e grupo não concedem acesso. Reconsulta `/ITILFollowup/{id}` e verifica tipo, pai, publicidade, autor e exclusões, além de consultar novamente a associação autor → grupos. Depois da preparação do conector Teams, repete essas leituras, incluindo a associação do autor a grupos, imediatamente antes do envio e verifica novamente referência, vínculo/revisão/geração e lease. A transição durável para `submitting` também confere o vínculo no SQLite. Indisponibilidade nunca concede acesso. Existe a janela inerente entre a última leitura e a ação externa; GLPI/SQLite/Teams não formam transação distribuída.

O worker usa vínculos/referências persistidos e `continue_conversation` do SDK com a aplicação configurada, sem fabricar uma atividade recebida autenticada nem chamar o resolver de atividades em segundo plano. O contexto de continuação do próprio SDK é exclusivamente de saída.

## Observação, primeira linha de base e limites

Consultas periódicas usam os mesmos filtros/revalidações de requerente e status de `TicketQuery`; não há varredura da base inteira nem fallback sem filtro. Referência do contrato GLPI REST v1: **10.0.18**, como nas etapas anteriores. Leituras: usuário exato, coleção `/Ticket/{id}/ITILFollowup`, acompanhamento exato `/ITILFollowup/{id}` e associação `/User/{author_id}/Group_User`. A versão implantada, o campo `date_creation` e esses contratos ainda precisam de homologação.

A linha de base é **por destinatário, geração e ticket**. A primeira leitura completa registra o maior ID de acompanhamento, incluindo privados/autores não elegíveis, e não cria avisos. Uma leitura falha, duplicada, com pai incorreto, paginação incompleta, total inconsistente ou limite excedido não estabelece a linha de base. A classificação por grupos de todos os acompanhamentos candidatos do ticket também deve terminar antes da transação: qualquer falha deixa o marco anterior intacto, sem fila parcial. Na primeira ativação, uma falha não cria baseline; a primeira leitura completa posterior continua sem envio de histórico. Ausência confirmada de associação classifica como não elegível e permite avançar o marco. Entrar num grupo depois não reproduz eventos já classificados. Chamados novos na observação também recebem linha de base sem histórico. Uma lista completa que deixa de conter um ticket remove seu marco; se ele voltar, recebe nova linha de base.

Leituras posteriores consideram somente IDs maiores que o marco. A ordenação é por ID crescente; os IDs devem ser crescentes e não reutilizados na instância GLPI. `date_creation` é exigida/validada, mas o relógio local não decide o que é novo. Edição de acompanhamento existente e privado que vira público não geram aviso retroativo. Não há snapshot transacional do GLPI: mensagens incluídas na leitura inicial são absorvidas silenciosamente; as que só aparecem na próxima leitura, com ID maior, podem gerar aviso. Inserções concorrentes/paginação instável podem exigir nova tentativa; inserção tardia com ID menor que um marco já observado não tem garantia de detecção. Homologar especialmente importações, restaurações e eventual reutilização de IDs; não usar esse mecanismo sobre uma base restaurada mantendo marcos incompatíveis.

Fila e avanço do marco usam a **mesma transação**: todos os eventos elegíveis são inseridos de forma durável antes de avançar. Se a fila estiver cheia ou a escrita falhar, nada daquela observação é confirmado. Falha de um ticket não invalida snapshots completos de outros tickets. Autorização é refeita no envio, sem conteúdo bruto na fila.

Limites por ciclo: dez destinatários, cinquenta tickets observados, vinte reservas/envios e 250 unidades de orçamento (incluem GETs GLPI e verificações locais). Até 150 unidades/60 s para observação; orçamento total de 120 s, reservando capacidade ao envio. Destinatários alternam pela última tentativa; tickets menos recentemente observados vêm primeiro. Uma coleção/pesquisa mantém limite de 200 registros e os contratos conservadores de paginação da consulta. Sessões mantêm teto de 500 GETs/60 s e timeout Requests de até 5 s, subordinados ao orçamento menor do worker. Encerramentos de sessão têm timeout de 5 s adicional e não contam no orçamento de GETs. Requests não impõe prazo absoluto contra um corpo arbitrariamente lento; os limites de tempo são cooperativos entre chamadas. Cada tentativa Teams usa `asyncio.wait_for` de 15 s, incluindo preparação/revalidação. HTTP síncrono/SQLite ocorrem em threads; não bloqueiam diretamente o event loop.

## Fila, reinícios e entrega incerta

Migração transacional incremental SQLite v1/v2 → **v3**, sem alterar vínculos, auditoria ou operações de resposta. Exclusividade por identidade/geração/ticket/acompanhamento; revisão administrativa acompanha cada evento. Troca, revogação/reaprovação ou nova ativação invalidam a geração/revisão antiga. Não se conserva o corpo da mensagem: apenas IDs, estado, tentativas, vencimentos, reserva e recibo Teams quando disponível.

| Estado | Tratamento |
| --- | --- |
| pending | Disponível a partir de `due`; reserva atômica |
| reserved | Ainda não há envio possível; reserva vence em quinze minutos |
| submitting | Marcador persistido imediatamente antes de enviar; entrega pode ter ocorrido |
| sent | Recibo Teams confirmado; não repetir |
| uncertain | Entrega possivelmente realizada; **sem repetição automática** |
| rejected / failed / discarded | Rejeição confirmada, limite atingido ou autorização/ativação inválida |

Reservas `reserved` abandonadas voltam a pending; `submitting` abandonadas ficam uncertain depois de quinze minutos. Isso trata queda após envio e antes da confirmação local sem duplicar cegamente. Falhas comprovadamente anteriores à entrega recebem backoff 30/60/120/240 s, até cinco tentativas contabilizadas; 429 confirmado respeita Retry-After numérico ou data HTTP (mínimo 1 s, máximo 24 h). 400/401/403/404/410 confirmados encerram o evento; 403/404/410 também desabilitam a referência, exigindo retomada administrativa. Falhas depois do marcador, incluindo timeout, 5xx ou recibo ausente, ficam uncertain. Não há reconciliação por texto, nem comando de reenvio cego de uncertain, nem promessa de entrega exatamente uma vez. Um aviso pode não ter confirmação e pode ter sido entregue.

Somente um processo dedicado obtém o lease SQLite de quinze minutos. Outro processo retorna `busy` sem consultar GLPI/enviar. Parada normal libera o lease; após SIGKILL aguardar vencimento. Reservas têm recuperação independente. Antes de novas chamadas, de confirmar observação e de enviar, o dono precisa continuar válido. Um processo antigo preso numa leitura pode sobreviver ao vencimento, mas não recebe permissão para confirmar observação/enviar após perder o lease. Não apagar manualmente lease/reservas para forçar recuperação. Premissa: instância única, SQLite em disco local persistente, relógio operacional correto; não há suporte a réplicas distribuídas/NFS.

## Contrato de associação do autor

Referência fixa **GLPI 10.0.18 REST v1**, não uma confirmação da versão instalada:

- [API REST, Get sub items](https://github.com/glpi-project/glpi/blob/10.0.18/apirest.md#get-sub-items): `GET /User/{author_id}/Group_User`, com `range`, `get_hateoas=false` e `expand_dropdowns=false`.
- [Group_User](https://github.com/glpi-project/glpi/blob/10.0.18/src/Group_User.php): relação User/Group com chaves `users_id` e `groups_id`, sem expansão da árvore. Validam-se os IDs de relação e do autor e IDs de grupo positivos.
- [Roteamento/paginação APIRest](https://github.com/glpi-project/glpi/blob/10.0.18/src/Api/APIRest.php): subitem filtra pelo pai; coleção usa `Content-Range` e 200/206. Quando o total é zero, essa implementação omite o cabeçalho. Só `200` com lista vazia na primeira página e cabeçalho ausente ou zero explícito comprova coleção vazia.

Todas as páginas são lidas e validadas, mesmo se a primeira já contiver grupo permitido. Rejeitam-se total variável, IDs repetidos, autor divergente, campos ausentes/expandidos, página faltante, corpo inválido e mais de 200 relações. Erro HTTP, timeout, orçamento esgotado ou resposta incompleta nunca equivalem a ausência confirmada. A leitura usa sessões/timeout/orçamento/sem redirects existentes e encerra a sessão em finally. Não são feitas alterações GLPI.

Associações repetidas de um autor são reutilizadas somente dentro do mesmo snapshot completo de um ticket, para evitar repetir GETs para cada mensagem histórica. Não há cache entre tickets, ciclos, pré-validação de entrega e verificação imediatamente anterior ao envio. As leituras bloqueantes ficam em threads, sem transações SQLite durante HTTP; entram no orçamento do worker. Muitos autores/grupos podem atingir os limites e adiar o ticket inteiro, sem avançar parcialmente o marco. Não existe snapshot transacional entre páginas ou entre GLPI e Teams.

Na entrega, associação ausente confirmada descarta o evento; falha de associação, inclusive HTTP 401/403/404, mantém pending com backoff e referência preservada. Isso não é uma rejeição Teams. A reserva é devolvida atomicamente ao contador de tentativas somente antes de `submitting`; falhas de classificação não esgotam as cinco tentativas de envio. Pausa/revogação/perda de autorização continuam descartando; recibo incerto continua sem reenvio. A retenção existente é por tempo desde a última transição: retries ativos atualizam esse tempo; não há prazo absoluto novo para encerrar uma indisponibilidade persistente. Monitore pendências e restaure permissões/disponibilidade.

## Grupos: configuração e migração

1. Na interface GLPI, entre em **Administração → Grupos** e localize os nomes “T.I” e “FlexSmart”. Nomes iguais podem existir em entidades diferentes: confirme a entidade e a ficha administrativa correta.
2. Abra cada grupo e obtenha seu ID numérico interno, pela coluna ID da lista (habilite-a se necessário) ou parâmetro `id` da URL da ficha. Não use ID de usuário, perfil, entidade ou chamado. Não há valores predefinidos para esses dois grupos neste projeto.
3. Na ficha, confira as associações diretas dos autores humanos. Associação somente a subgrupo não basta: configure explicitamente o ID do subgrupo se essa for uma decisão administrativa aprovada. Associações LDAP/dinâmicas contam apenas quando presentes como relação direta em `Group_User`.
4. Durante uma janela operacional autorizada, pare o processo dedicado. Substitua a variável antiga por `NOTIFICATIONS_SUPPORT_GROUP_IDS`, com os IDs de grupos conferidos separados por vírgulas. Não copie os IDs antigos. Preserve `NOTIFICATIONS_INTEGRATION_IDS` com IDs de usuários de todas as automações e da conta do token, mesmo que sejam membros dos grupos selecionados.
5. Aplique a configuração ao bot e ao worker de forma consistente e reinicie pelo procedimento operacional existente. Não apague banco, fila, marcos ou vínculos. Não há alteração de schema nesta correção. Eventos já pendentes serão reclassificados pela política atual na entrega; eventos antigos já classificados não são reproduzidos. Uma configuração ausente bloqueia notificações, preservando abertura/consulta/resposta.
6. Homologue, em etapa autorizada, a leitura completa de `Group_User` com as permissões/entidades reais do token. A API pode limitar visibilidade; não declare ausência definitiva com base numa conta sem permissões adequadas. Este código depende de coleções completas e trata erros/formatos parciais como indisponibilidade, sem fallback por nomes.

Nenhuma chamada real foi feita para localizar os IDs. `tools.notifications once/run`, inclusive `--simulate`, consultam GLPI quando executados com configuração real; simulação apenas evita envio Teams. Não use esses comandos como teste offline.

## Configuração e comandos

Novos campos de Settings, sem dependências novas:

```dotenv
NOTIFICATIONS_ENABLED=false
NOTIFICATIONS_SUPPORT_GROUP_IDS=
NOTIFICATIONS_INTEGRATION_IDS=
NOTIFICATIONS_INTERVAL=60
```

Preencha as duas listas com os IDs reais conferidos; valores vazios mantêm o mecanismo bloqueado. Ativar exige `NOTIFICATIONS_ENABLED=true`, listas válidas e as configurações existentes: `MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`, `MICROSOFT_APP_TENANT_ID`, `IDENTITY_ALLOWED_TENANT_ID`, `IDENTITY_DB_PATH`, `GLPI_URL`, `GLPI_APP_TOKEN`, `GLPI_USER_TOKEN`. Não remover credenciais compartilhadas para pausar notificações. Nenhum valor real de segredo foi lido/documentado nesta etapa.

Após backup e homologação autorizada, configurar o servidor e o processo dedicado de forma consistente, aprovar vínculos e pedir que a pessoa consulte seus chamados em conversa pessoal. Isso captura/ativa sua referência; o ciclo seguinte estabelece linhas de base. O banco precisa existir: não se inventam vínculos nem se cria banco administrativo automaticamente no worker. A primeira operação com banco existente migra o schema.

```sh
# Um ciclo; só usar no servidor quando envio real estiver autorizado.
venv/bin/python -m tools.notifications once
# Processo dedicado; intervalo de 10 a 86400 segundos.
venv/bin/python -m tools.notifications run --interval 60
# Sem envio Teams, mas consulta GLPI e grava linhas de base/fila se configurado.
venv/bin/python -m tools.notifications once --simulate
venv/bin/python -m tools.notifications run --simulate --interval 60
```

Simulação **não é offline** e avança a observação/produz pendências reais. Não execute com configuração real apenas para teste. Antes de sair de uma simulação e habilitar envio, use pause/resume nos destinatários para descartar essas pendências se não desejar entregá-las. Nenhum desses comandos com GLPI real foi executado nesta implementação. Não iniciar worker em import, startup do FastAPI ou por worker do Uvicorn. Supervisor/systemd pode executar `run`; parar com SIGINT/SIGTERM e aguardar recuperação conservadora quando interromper envio.

Comandos exclusivamente locais (tenant/object ID abaixo fictícios):

```sh
# Suspende destinatário, remove referência e descarta pending/reserved.
venv/bin/python -m tools.notifications pause --tenant 11111111-1111-4111-8111-111111111111 --object-id 22222222-2222-4222-8222-222222222222
# Remove ativação anterior; próxima resolução autenticada cria nova geração/linha de base.
venv/bin/python -m tools.notifications resume --tenant 11111111-1111-4111-8111-111111111111 --object-id 22222222-2222-4222-8222-222222222222
# Limpeza local, sem GLPI/Teams; --db permite selecionar explicitamente outro banco.
venv/bin/python -m tools.notifications cleanup --db caminho/ficticio/identity.sqlite3
```

Pause é persistente: uma atividade normal não o desfaz. Resume não envia contato nem recupera fila antiga; exige conversa/resolução segura nova. Para revogar a identidade, usar também o comando administrativo existente `tools.identity_links revoke` conforme [identity.md](identity.md); pause não revoga acesso à consulta. Para pausa global, parar worker e desativar NOTIFICATIONS_ENABLED no servidor/processo. Apenas parar/reiniciar conserva a observação e pode entregar eventos criados durante a interrupção; para retomar **sem histórico/backlog**, pause e resume os destinatários antes de reativar e peça nova consulta pessoal. Não apagar apenas os marcos de usuários ativos nem trocar o banco sem planejamento.

## Aviso e clique durante preenchimento

```text
🔔 Nova resposta no chamado #1234
Impressora não imprime

O suporte enviou uma mensagem.
[Ver chamado]
```

Título passa por conversão HTML e sanitização existentes, limitado a 120 caracteres; sem corpo da resposta, HTML, menções e URLs internas. Payload restrito `{"notification":"token-aleatorio"}` só seleciona registro persistido, associado no servidor à identidade, revisão, geração e aplicação. Não aceita ID arbitrário de ticket. Botão copiado para outro usuário, adulterado, de geração antiga ou com mais de sete dias é negado genericamente, com acesso à lista. O clique resolve identidade novamente na atividade autenticada e revalida acesso antes de abrir os detalhes existentes.

Durante formulário:

```text
Você já tem um chamado em preenchimento (Manutenção).
[Continuar preenchimento] [Cancelar preenchimento e ir ao menu]
```

Reutiliza confirmação aleatória existente. Clique não responde pergunta nem cancela; somente confirmação atual explícita cancela. Depois de ir ao menu, clicar novamente no aviso para abrir o ticket. Botão antigo não cancela formulário novo.

Durante resposta textual:

```text
Existe uma resposta em preenchimento. Deseja continuar ou guardar
 o rascunho e ver o aviso? O prazo do rascunho continua correndo.
[Continuar resposta] [Guardar e ver chamado]
```

Continua sem capturar texto de botão. Sair exige botão de confirmação associado à versão da tela; guarda estado separado em `NotificationState`, sem cancelar/enviar a operação. Exibe `[Retomar resposta guardada]`; a retomada reautoriza o chamado original. O estado guardado conserva seu vencimento original de cinco minutos; o corpo SQLite mantém limite absoluto existente de quinze minutos. Não guarda segunda resposta sobre outra ainda válida nem substitui um formulário/rascunho novo na retomada. A navegação continua em MemoryStorage, perdida em reinício; não há promessa nova de recuperação dos rascunhos após reinício. O envio proativo não chama processador de formulário nem escreve em UserProfile, NavState ou TicketQueryState.

## Retenção e operação

Eventos/clicks: sete dias desde última transição; pendências antigas também podem expirar sem envio. `reserved/submitting` aguardam recuperação conservadora antes da remoção por retenção. Marcos da geração ativa permanecem mesmo quando eventos são limpos, para não reenviar histórico. Marcos de gerações removidas/inativas são limpos. Referência com trinta dias sem captura autenticada é desabilitada e removida logicamente, exigindo resume e nova consulta pessoal. Tombstones de pausa/IDs permanecem para não reativar usuários silenciosamente. Essas rotinas executam em cada ciclo ou pelo comando cleanup; sem execução não há remoção pontual garantida. Referências não contêm corpo, mas service URL/IDs de conversa são sensíveis: proteger banco/disco/backups com permissões locais e acesso administrativo restrito. SQL não garante apagar páginas ou backups fisicamente. Não registrar referências, tokens ou respostas brutas em logs.

## Arquivos e verificações locais

Criados: `identity/notifications.py`, `notifications/__init__.py`, `notifications/policy.py`, `notifications/capture.py`, `notifications/glpi.py`, `notifications/worker.py`, `bot/notification_actions.py`, `tools/notifications.py`, `tests/test_notifications.py`, este documento.

Alterados nesta etapa: `identity/store.py` (migração v3), `identity/service.py` (revisão no resultado), `identity/ingress.py` (reuso do resolver/captura), `services/ticket_query.py` (guard opcional de orçamento), `bot/dialogs.py` (precedência da ação), `bot/ticket_consult.py` (accessor separado), `config.py`, `tests/support.py` e `tests/test_reply_operations.py` (fixture v1/schema atual), `AGENTS.md`, `docs/identity.md`, `docs/ticket-conversation.md`. Nenhuma dependência instalada; nenhuma credencial/banco real alterado. Alterações preexistentes no workspace foram preservadas.

Testes executados com o venv/SDK instalado, SQLite temporário, mocks e bloqueio de rede. Contagem final e comandos na seção 16 do AGENTS.md. O teste do envio usa `BotFrameworkAdapter`, `ConversationReference`, `TurnContext` e `ResourceResponse` reais, com criação do conector/transporte mockados. Não comprova JWT, credenciais, instalação do bot, service URL real ou entrega no Teams.

## Homologação real pendente (somente em etapa autorizada)

- Backup/permissões/disco persistente, migração v2→v3 no servidor e rotina de limpeza; proibir processos antigos limitados a schema v2.
- Tenant/aplicação/JWT/TeamsInfo reais, vínculo único, conversa pessoal, captura, mudança da referência, app removido e reinstalado.
- Confirmar IDs dos grupos T.I/FlexSmart, entidades e associações diretas atuais de seus usuários; confirmar **todos** os IDs de usuários da integração/automações, incluindo mudanças futuras de token. Não habilitar com listas presumidas.
- GLPI implantado: versão, permissões/entidades, filtros requerente/status, coleções vazias/paginação, ITILFollowup exato, `date_creation`, ordenação/crescimento/não reutilização de IDs e exclusão/privacidade.
- Primeira linha de base e mensagens simultâneas, privado→público sem retroativo, edição sem novo aviso, chamados novos/reabertos e perda do requerente.
- Isolamento A/B e papéis técnico/observador/grupo; revogação/substituição/reaprovação; vínculo/usuário/ticket/mensagem alterados antes do envio.
- Renderização/tamanho/acentos/cartões no Teams, clique copiado/velho, formulário/anexos e captura/confirmação/retomada de resposta.
- Timeout/429/Retry-After, 403/404/410, recibo ausente, SIGKILL antes/depois do marcador e depois da entrega, lease vencido e duas instâncias; medir latência/limites com volume real.
- Regressão real dos três formulários, anexos e Formcreator; os testes locais não substituem essa validação.

O transporte dedicado também desativa explicitamente as retentativas automáticas do msrest e redirecionamentos, com timeout HTTP de 5 s, antes do marcador de envio. Isso foi conferido na configuração real do ConnectorClient em teste com envio mockado; a política da fila é a única responsável por decidir nova tentativa. A configuração não altera o adapter da abertura, pois o processo dedicado compõe seu próprio adapter.

## Verificação offline da política por grupos

Na raiz do projeto, com o venv existente:

```sh
venv/bin/python -m tests.run_offline_suite
```

O runner bloqueia globalmente Requests, DNS, conexões/sockets e aiohttp antes de descobrir os testes; os contratos usam respostas simuladas e SQLite temporário. Não use `tools.notifications --simulate` para substituir esse teste: esse comando consulta o GLPI configurado.

A revisão por grupos inclui testes de permissão/negação, múltiplos grupos e páginas, erros HTTP e respostas incompletas, marcos sem avanço em falha, revalidação e timeout antes do envio, pendências após indisponibilidade prolongada, integração no grupo permitido, exclusão de recibos do bot e isolamento A/B. Os testes anteriores são mantidos com fixtures atualizadas para IDs de grupos. Nenhuma homologação real é inferida desses testes.
