# Etapa 5 — detalhes, conversa pública e resposta

> Revisão atual: texto válido é enviado diretamente. A antiga tela de
> prévia/Enviar/Editar registrada historicamente neste documento não faz mais
> parte da experiência; seus botões antigos são inertes.

## Fluxo direto atual

```text
✍️ Digite sua resposta para o chamado #1028.
Ao enviar a mensagem, ela será registrada no chamado.
[Cancelar resposta]
```

Após recibo 201 com ID válido:

```text
✅ Resposta enviada!
[1 — Ver conversa]
[4 — Voltar ao chamado]
```

`activity.id` é persistido com a operação e tem unicidade no escopo exato de
identidade, conversa e ticket. Reentrega reutiliza a operação e não repete POST
confirmado ou incerto. O schema SQLite v4 acrescenta a coluna nullable e índice
único parcial sem apagar vínculos, notificações ou operações anteriores.

## Autoria apresentada

Um acompanhamento só recebe o nome do requerente quando seu `followup_id`
confirmado existe em `reply_operations` no mesmo vínculo/conversa/ticket. O nome
vem da leitura exata do usuário GLPI validado. Somente com essa prova o primeiro
cabeçalho de origem, no formato estritamente conhecido, é ocultado. Prefixos
parecidos sem recibo comprovado permanecem integrais e não alteram autoria.

```text
💬 Mensagem mais recente

João Silva:
Minha resposta
```

Datas ficam ocultas na apresentação padrão, mas continuam validadas e usadas na
ordenação/paginação. A autoria e o conteúdo armazenados no GLPI não são alterados.

Implementação local com APIs simuladas. Não homologada no Teams/GLPI real. Esta etapa substitui a mensagem temporária de seleção da etapa 4. Notificações proativas e anexos de consulta/resposta não foram implementados.

## Fluxo e exemplos

Selecionar um item da página válida revalida a identidade e o requerente no GLPI e apresenta:

```text
🎫 Chamado #1234 — Impressora não imprime
Situação: Em atendimento

📝 Solicitação inicial (1/1):
A impressora do financeiro não imprime desde hoje cedo.

1 — Ver conversa
2 — Responder chamado
3 — Voltar aos meus chamados
0 — Menu principal
```

Descrições maiores oferecem `9 — Ver mais` e `7 — Trecho anterior`, com posição/total de trechos. Conversa pública:

```text
💬 Conversa pública do chamado #1234
Mais recentes primeiro.

Página 1/2
Autor: Maria Silva
Data: 2026-01-01 10:00:00 (horário do GLPI)
Trecho 1/1:
Pode informar se a impressora está ligada?

4 — Voltar ao chamado
8 — Atualizar conversa
3 — Meus chamados
0 — Menu principal
9 — Mensagens anteriores / ver mais
```

A data vem do GLPI, sem presumir seu fuso. Ordenação por data decrescente, desempate por ID decrescente. Uma mensagem/trecho por página; mensagens longas continuam antes da próxima mensagem. Autor é nome obtido por leitura exata do usuário GLPI, sem classificação automática como técnico. Falha de nome usa “Autor não identificado”. Não há timeline bruta, tarefas, documentos, soluções ou logs internos. Ausência de registros públicos retorna “Este chamado ainda não tem mensagens públicas.”; falha de API retorna erro temporário.

Resposta:

```text
✍️ Digite a mensagem que deseja enviar ao chamado #1234.

Você poderá conferir antes de enviar. Somente texto, até 2000 caracteres.
Para cancelar, use o botão ou digite /cancelar-resposta.
Palavras e números digitados nesta tela serão parte da mensagem.
```

Uma mensagem como `Sim, a impressora está ligada.` cria um rascunho, sem POST:

```text
Confira sua mensagem:
Sim, a impressora está ligada.

A prévia oculta endereços e neutraliza formatação; o texto digitado será registrado integralmente.
Deseja enviar?
Digite enviar, editar ou /cancelar-resposta.
O autor nativo no GLPI será a conta da integração; o texto identificará a origem Teams.
```

Há botões Enviar/Editar/Cancelar vinculados à versão da tela e ao rascunho. Na captura, `sim`, `não`, `menu`, `0`, `1` e `Enviar` são texto, não comandos. Os comandos reservados são `/cancelar-resposta` e `/tentar-novamente` (recuperação de erro); botões reconhecidos também têm precedência. Na confirmação, somente `enviar`, `editar` ou `/cancelar-resposta` têm essas ações. Payload inválido nunca vira texto acompanhante. Editar cancela logicamente a operação anterior e pede uma nova mensagem completa. Cancelar volta ao chamado; uma operação já reservada/em envio não é apresentada como cancelada.

Texto vazio, invisível, caracteres de controle indevidos e texto acima de 2000 caracteres são rejeitados, sem truncamento. Quebras CRLF/CR viram LF antes de gravar/exibir o rascunho. Anexos retornam “Somente texto é aceito. Nenhum anexo foi enviado.”, sem baixar/enviar arquivos. Depois de sucesso confirmado:

```text
✅ Sua mensagem foi enviada ao chamado #1234.
1 — Atualizar conversa
4 — Voltar ao chamado
0 — Menu principal
```

## Autorização e isolamento

A entrada continua usando uma única passagem pelo adapter compartilhado e o resolver temporário de IdentityIngress. Cada atividade de leitura/resposta resolve novamente identidade autenticada, tenant permitido, conversa pessoal, membro Teams, vínculo ativo e usuário GLPI ativo/não excluído. Não há fallback por nome/e-mail/UPN.

O backend centraliza a autorização do ticket em `TicketQuery.checked`, reutilizado por `TicketConversation.authorize`: requerente individual exato, status 1–4 e exclusão desativada, com todas as páginas de Ticket_User verificadas. Detalhes, histórico e envio não confiam na autorização anterior da lista. Técnico, observador ou membro de grupo não basta. A autorização é repetida após paginação do histórico e imediatamente antes do POST. Durante reserva e antes do POST, o SQLite também confere vínculo ativo, usuário vinculado e revisão administrativa (`updated_at`) do vínculo usado na criação do rascunho. Revogação/reaprovação invalida a operação antiga.

Ticket é escolhido exclusivamente entre IDs da página atual e guardado pelo servidor; nenhum ID de ticket ou itemtype é aceito livremente em botões. Estado em memória associa tenant/object ID/usuário GLPI/conversa/remetente, ticket, tela, posição, versão aleatória e referência opaca de rascunho. Não guarda descrição/histórico nem corpo do rascunho. Mudança de identidade/conversa, expiração ou botão antigo nega a seleção. Copiar payload/rascunho para outro usuário não concede leitura/envio.

A sessão de consulta expira após cinco minutos sem interação; o rascunho tem prazo absoluto de quinze minutos, sem extensão por cliques. Expiração/reinício exige retornar à lista; operações antigas não são reativadas automaticamente. Falhas recuperáveis na sessão preservam a referência e oferecem tentar novamente/cancelar. Voltar à lista refaz a pesquisa. Formulários continuam tendo precedência, com suas respostas/anexos preservados e confirmação de interrupção existente.

Negação não informa existência, título ou conteúdo de outro chamado: “Esse chamado não está disponível para consulta. Atualize a lista.” Falha de identidade mantém a mensagem da etapa 4.

## Contrato GLPI e autoria

Referência fixa: **GLPI 10.0.18, API REST v1**; versão implantada ainda desconhecida. Fontes oficiais:

- [apirest.md](https://github.com/glpi-project/glpi/blob/10.0.18/apirest.md): GET de item/subitens, Content-Range, POST com input e resposta 201/id; seção Sanitized content.
- [Api/API.php](https://github.com/glpi-project/glpi/blob/10.0.18/src/Api/API.php): tratamento de conteúdo e paginação.
- [ITILFollowup.php](https://github.com/glpi-project/glpi/blob/10.0.18/src/ITILFollowup.php): itemtype/items_id, is_private, content, date, users_id; prepareInputForAdd define o autor pela sessão quando omitido; post_addItem aplica efeitos nativos.
- [Features/ParentStatus.php](https://github.com/glpi-project/glpi/blob/10.0.18/src/Features/ParentStatus.php): `_no_reopen` impede reabertura automática na inclusão de acompanhamento por API.
- [PendingReason_Item.php](https://github.com/glpi-project/glpi/blob/10.0.18/src/PendingReason_Item.php): efeitos relacionados à pendência.

Detalhes: `GET /Ticket/{id}`, sem Formcreator. Histórico: somente `GET /Ticket/{id}/ITILFollowup`, percorrendo Content-Range, rejeitando páginas incoerentes/duplicadas/incompletas e conferindo itemtype=Ticket e items_id em cada registro. Só `is_private` inteiro 0 ou string "0" é público; ausente, bool, inválido, 1 ou desconhecido não é público. Registro de outro pai/tipo invalida o resultado inteiro. Não se consulta o endpoint de timeline nem outros tipos por conveniência.

Envio: único `POST /ITILFollowup` com `input` limitado a itemtype=Ticket, items_id decidido pelo backend, is_private=0, content e `_no_reopen=true`. Não há POST Ticket/FormAnswer, PUT de status/requerente/atribuição ou impersonação. O autor nativo é a conta autenticada pelo GLPI_USER_TOKEN; não se envia users_id. O servidor acrescenta:

```text
Origem: Microsoft Teams — João Silva (requerente com identidade validada).
```

Esse nome vem de GET exato do usuário GLPI resolvido, não do nome de exibição Teams; sem nome disponível, usa rótulo neutro de requerente validado. A operação persistida vincula identidade, conversa e ticket ao recibo do acompanhamento. A autoria nativa da integração não é apresentada como autoria nativa do requerente. Efeitos normais do GLPI (date_mod, auditoria e notificações nativas conforme configuração) podem ocorrer; não foi criado mecanismo de notificação Teams.

## Conteúdo e limites

As novas leituras pedem `X-GLPI-Sanitized-Content: false`, para obter HTML decodificado pelo GLPI conforme o contrato. O HTMLParser transforma em texto e decodifica entidades de texto uma vez; esse resultado não volta a ser interpretado como HTML. Parágrafos, quebras e acentos são preservados. Scripts, estilos, imagens, iframes e outros blocos executáveis são removidos. Não há requisição a href/src ou carregamento remoto.

URLs/endereço de domínio visíveis são substituídos por marcadores; sintaxe de menções/Markdown/HTML é neutralizada. Links de API e documentos não são exibidos. A prévia do rascunho é tratada como texto literal, sem interpretar HTML digitado. O POST escapa esse texto em HTML e preserva suas quebras; não usa IA nem reescreve a mensagem. A identificação de origem é escapada separadamente.

Leitura: fonte de até 100 mil caracteres por conteúdo, trechos de até 1200 caracteres, título/nome até 120; limite de 200 registros por coleção, 500 requisições por sessão e orçamento de 60 segundos, com timeout HTTP até cinco segundos. Excesso/erro resulta em mensagem temporária de falha, sem lista parcial ou falsa ausência. Timeout Requests limita conexão/leitura e não garante prazo absoluto para um corpo entregue lentamente; permanece item de homologação. O encerramento de sessão tem timeout adicional de cinco segundos. GET/POST não seguem redirecionamentos. HTTP/SQLite síncronos executam em threads; nenhuma transação SQLite permanece aberta durante HTTP.

O corpo de resposta não é registrado em logs. O handler de erros protege o caminho sensível e não imprime exceções/conteúdo bruto; também foi removido o log de texto da atividade no handler global. As demais limitações históricas de logs da abertura não foram refatoradas.

## Operações persistentes, falhas e limpeza

O banco existente `IDENTITY_DB_PATH` recebe migração transacional **v1 → v2**, preservando links, índice e auditoria. A v2 acrescenta reply_operations: identificador aleatório, associação de identidade/conversa, ticket, revisão do vínculo, corpo temporário, estado, tentativas, reserva, datas/expiração e followup_id confirmado. A migração ocorre no init administrativo ou no primeiro acesso às operações, somente com banco existente. Banco ausente/corrompido/versão desconhecida bloqueia a resposta. Os testes só migraram bancos temporários.

Estados principais:

| Estado | Consequência |
| --- | --- |
| ready | Rascunho pode ser conferido/editado/confirmado dentro do prazo |
| reserved | Reserva atômica exclusiva; sem segunda reserva concorrente |
| submitting | Marcador persistido imediatamente antes do POST; não liberar para repetição |
| sent | Recibo 201/id confirmado; corpo removido; não repetir |
| uncertain | Pode ter gravado; sem reenvio automático e sem botão Enviar |
| cancelled / expired | Corpo removido; operação não pode ser enviada |

Falha comprovadamente anterior ao marcador submitting libera somente a reserva ready e preserva o rascunho; usuário pode tentar novamente explicitamente. Timeout, conexão interrompida, redirecionamento, erro ou resposta incompleta depois de iniciar POST são incertos. Não se usa igualdade de texto para reconciliar, não há mecanismo confiável de idempotência remota assumido e não se repete automaticamente POST. Reserva/submitting abandonados por reinício também não são liberados cegamente. Mensagem:

```text
Não recebi a confirmação do envio. Sua mensagem pode ter sido registrada.
Não vou reenviar automaticamente. Atualize a conversa para conferir.
```

Não se promete entrega exatamente uma vez nem recuperação automática de todas as respostas. Se um processo cair após o GLPI gravar e antes do recibo local, a operação permanece bloqueada para reenvio, mesmo que nenhuma mensagem de sucesso tenha chegado ao Teams. Retornar à lista/conversa é permitido; uma nova resposta é uma nova intenção explícita, não reconciliação da anterior.

Corpo removido logicamente no sucesso, cancelamento, resultado incerto ou expiração (15 minutos). Metadados conservados por sete dias desde a última transição. A limpeza é local e oportunista em operações de rascunho; **sem uso/execução do comando, não há remoção pontual garantida por relógio**. Para manutenção administrativa local:

```sh
venv/bin/python -m tools.reply_operations --db caminho/do/banco.sqlite3
```

Esse comando apenas migra/limpa o banco informado, sem HTTP. Não foi adicionado agendador. Proteger banco, disco e backups por permissões do sistema; a limpeza SQL não é garantia de apagamento físico/criptográfico de páginas ou backups. Fazer backup antes de migração no ambiente real e não usar código antigo limitado ao schema v1 após upgrade. Mantida a premissa de instância única/disco persistente; não há suporte novo a réplicas distribuídas.

## Configuração, testes e pendências

Nenhuma configuração/dependência nova. Mantidos IDENTITY_DB_PATH, IDENTITY_ALLOWED_TENANT_ID e credenciais Microsoft/GLPI existentes. Tenant permitido vazio bloqueia consulta/resposta sem exigir vínculo na abertura. Conta técnica precisa das permissões adequadas para ler os itens/relações/usuários e criar ITILFollowup público; essas permissões não substituem os filtros do backend.

No venv local: Python 3.12.3; core/schema/connector 4.17.1, aiohttp 3.14.5, msrest 0.7.1. Testes novos: `test_ticket_conversation` (10), `test_reply_operations` (11), `test_ticket_detail` (20). As 87 verificações anteriores permanecem, com a seleção temporária atualizada para detalhes reais. Total: **128 aprovados, zero falhas, zero erros, zero pulados**, no comando:

```sh
venv/bin/python -m unittest discover -s tests -v
```

Ordem inversa também aprovada: 128 testes, com restauração dos accessors verificada após a suíte e sem importação indevida de tests.test_menu pelo discovery. Mocks nas referências efetivas, SQLite temporário, HTTP/sockets/envios bloqueados. A execução assíncrona completa utiliza o ambiente fora do sandbox que trava ao encerrar executores, conforme diagnóstico anterior, sem substituir to_thread. Compilação e pip check locais também verificados. Não foram enviados acompanhamentos reais nem alterados vínculos/banco real.

Pendências de homologação: versão/contrato GLPI implantado, permissões/entidades, comportamento de `_no_reopen` e hooks/plugins locais, autoria nativa e origem, HTML/entidades/coleções vazias, tenant/JWT/TeamsInfo reais, cartões/tamanho Unicode e latência, migração/backup/rotina de limpeza, falhas/reinício e regressão real dos três formulários/anexos. Testes simulados não validam produção.

Notificações futuras deverão ter ações e roteamento próprios, sem virar texto de captura ou substituir formulário/rascunho em andamento. Essa integração foi apenas documentada; não implementada.

## Arquivos desta etapa

Criados: `bot/ticket_detail.py`, `identity/replies.py`, `services/ticket_content.py`, `services/ticket_conversation.py`, `services/reply_sender.py`, `tools/reply_operations.py`, `tests/test_ticket_conversation.py`, `tests/test_reply_operations.py`, `tests/test_ticket_detail.py` e este documento.

Alterados: `main.py` (proteção de logs), `bot/dialogs.py` (preservar caixa do texto da resposta), `bot/ticket_consult.py` (seleção/telas), `services/ticket_query.py` (autorização/coleções/sessão compartilhadas), `identity/store.py` (migração v2), `tests/test_ticket_consult.py` (expectativas da seleção), `AGENTS.md`, `docs/ticket-query.md` e `docs/identity.md`.


## Atualização da etapa 6

Notificações públicas opt-in foram implementadas após esta etapa. Consulte [notifications.md](notifications.md) para captura autenticada, migração SQLite v3, políticas de autores, fila, execução dedicada, retenção e pendências de homologação. Afirmações anteriores neste documento sobre notificações futuras são registros da etapa anterior. Permanecem desabilitadas por padrão, sem validação externa real.
