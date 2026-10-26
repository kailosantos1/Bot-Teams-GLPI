> Diagnóstico atual no servidor (PowerShell), configuração segura, inicialização preservando vínculos e códigos de log: [server-identity-powershell.md](server-identity-powershell.md). Os trechos preparatórios abaixo são registros históricos.

> Etapa 5: o banco de vínculos passa a admitir schema v2, com operações persistentes de resposta, preservando links/auditoria por migração incremental. A identidade segura continua sendo resolvida a cada operação. Ver [ticket-conversation.md](ticket-conversation.md) para retenção, reserva de envio e homologação pendente.

> Atualização da etapa 4: a composição compartilhada proposta neste documento foi ligada a `main.py` para a consulta pessoal. A abertura continua usando sua autorização legada. Consulte [ticket-query.md](ticket-query.md) para funcionamento, contrato GLPI, resultados locais e pendências atuais; os trechos preparatórios abaixo registram as etapas 2/2.1.

# Etapa 2: base de identidade Teams → GLPI

A base está isolada: `main.py` não a chama. A abertura continua usando a
identificação legada e não está protegida por este mecanismo. Menu, listagem,
histórico de chamados e notificações não foram implementados.

## SDK e autenticação

Na revisão da etapa 2.1, o interpretador acessível é `/usr/bin/python3`, Python
3.12.3. Não foi encontrado ambiente virtual nas árvores acessíveis de
`/home/contratos`, `/opt`, `/srv` e `/usr/local`, nem processo visível do bot.
A busca examinou caminhos e executáveis de processos, sem ler `.env`, ambientes
de processos ou argumentos que pudessem conter credenciais. Isso não identifica
o runtime de outro servidor, contêiner ou sessão não visível.

Este interpretador não possui `botbuilder-core`, `botbuilder-schema` ou
`botframework-connector` instalados; portanto não há versão instalada a informar.
`requirements.txt` declara `botbuilder-core>=4.14.0`, sem fixar versão.
Não foram instaladas ou atualizadas dependências. Os três pacotes foram
reportados individualmente como não instalados. Não há compatibilidade confirmada.
Execute com o mesmo interpretador/ambiente que inicia o bot (ative esse ambiente
antes; não use outro Python apenas para conseguir rodar os testes):

```sh
cd /home/contratos/Documentos/VSCode/Bot-Teams-GLPI
python -m tools.inspect_identity_sdk
python -m unittest discover -s tests -v
```

Se o comando de inicialização usa `python3`, use `python3` nos dois comandos;
se usa caminho absoluto, use esse mesmo executável. A inspeção imprime versão
Python, executável, versões dos três pacotes, assinaturas e campos dos modelos,
sem importar `config` ou ler credenciais. Não instala dependências.

Interfaces conferidas no código oficial da Microsoft:

- [TeamsInfo](https://github.com/microsoft/botbuilder-python/blob/main/libraries/botbuilder-core/botbuilder/core/teams/teams_info.py):
  `await TeamsInfo.get_member(turn_context, member_id)` retorna `TeamsChannelAccount`.
- [TeamsChannelAccount](https://github.com/microsoft/botbuilder-python/blob/main/libraries/botbuilder-schema/botbuilder/schema/teams/_models_py3.py):
  `id`, `aad_object_id` (herdado), `tenant_id`, `email`, `user_principal_name`.
- [BotFrameworkAdapter](https://github.com/microsoft/botbuilder-python/blob/main/libraries/botbuilder-core/botbuilder/core/bot_framework_adapter.py):
  `process_activity(req, auth_header, logic)` autentica antes do callback,
  armazenando `ClaimsIdentity` em `BotAdapter.BOT_IDENTITY_KEY`.

Essas fontes são da branch principal, não comprovam compatibilidade da versão
instalada em produção. Conferir essa versão e homologar a integração autenticada
são pendências obrigatórias antes de ativar consultas futuras.

`IdentityIngress.dispatch(activity, authorization, logic)` é a entrada preparada
para a integração com o endpoint. Recebe um bundle composto pelo servidor com o
**mesmo adapter do endpoint**, seu credential provider e `BotAdapter.BOT_IDENTITY_KEY`.
Executa `adapter.process_activity` uma única vez e devolve a resposta original.
O callback recebe `(context, resolve_identity)`: a abertura ignora o resolver;
um futuro fluxo autorizado poderá solicitá-lo explicitamente. A configuração
inválida e a autenticação desabilitada bloqueiam apenas a resolução nova.

`IdentityIngress.process(activity, authorization)` permanece como conveniência
isolada de resolução, com verificação prévia de configuração. Sem bundle o
adapter é criado tardiamente e reutilizado. **Não chamar process ou dispatch
em callback que já passou pelo adapter**; não reprocessar a mesma atividade
em outro adapter. A entrada integrada será dispatch em lugar da chamada atual
no endpoint. Nenhuma dessas mudanças está ativada em `main.py`.

O callback emite uma capacidade interna temporária para
`IdentityService.resolve(turn)`. Contexto cru e capacidade expirada são recusados.
Essa capacidade organiza o código confiável do processo Python: não é token
serializável ou proteção contra execução arbitrária dentro do servidor.

O serviço exige canal `msteams`, conversa `personal`, tenant permitido, UUID Entra
do remetente e correspondência exata com o membro obtido pela API autenticada do
Teams. Confere `id`, `aad_object_id` e `tenant_id` do membro; ausência ou divergência
nega resolução. O tenant do token do Connector não é usado como tenant da pessoa.
E-mail e UPN são atributos distintos e nunca criam associação automaticamente.

## Interface pública e composição futura

`IdentityResult` é imutável e contém:

- `code`: `ok` ou falha estruturada, como `unauthenticated`,
  `authentication_configuration`, `authentication_disabled`, `authentication_failed`,
  `sdk_unavailable`, `wrong_channel`, `personal_only`, `tenant_denied`,
  `identity_missing`, `identity_mismatch`, `teams_unavailable`, `link_missing`,
  `link_revoked`, `link_changed`, `identity_unavailable`, `glpi_missing`,
  `glpi_inactive`, `glpi_deleted`, `glpi_incomplete` ou `glpi_unavailable`.
- `identity`: `TeamsIdentity(tenant_id, object_id, member_id, email,
  user_principal_name)` após validação Teams, inclusive quando não há vínculo.
- `glpi_user_id`: preenchido somente em `ok`; erros não expõem vínculo de outra
  pessoa, respostas HTTP ou exceções brutas.

Proposta concreta para integração futura, sem ativação nesta etapa:

1. Na composição de `main.py`, criar explicitamente um `SimpleCredentialProvider`
   e passá-lo ao **único** `BotFrameworkAdapter` no lugar da construção atual,
   mantendo as mesmas configurações Microsoft e `adapter.on_turn_error`.
2. Compor o serviço e o ingress uma vez; fornecer os mesmos objetos de adapter
   e provider. O bundle é configuração do servidor, nunca conteúdo da atividade.
3. Substituir somente a chamada do endpoint por `dispatch`, mantendo desserialização,
   header original, respostas HTTP e tratamento de erros existentes. `dispatch`
   preserva a resposta do SDK e propaga erros para os handlers existentes.
4. O roteador continua encaminhando abertura ao `logic_process_message` existente,
   com o mesmo TurnContext, UserProfile e MemoryStorage. Não resolver identidade
   em todas as mensagens e não interpretar respostas de formulário como novo fluxo.
   Uma próxima etapa definirá a seleção explícita do fluxo novo e sua precedência.

Esboço da composição (documentação; **não foi aplicado a main.py**):

```python
from botbuilder.core import BotAdapter, BotFrameworkAdapter, BotFrameworkAdapterSettings
from botframework.connector.auth import SimpleCredentialProvider
from identity.store import LinkStore
from identity.glpi import GLPIUserReader
from identity.service import IdentityService
from identity.ingress import IdentityIngress

# Substitui a construção original; não acrescenta um segundo adapter.
provider = SimpleCredentialProvider(settings.MICROSOFT_APP_ID,
                                   settings.MICROSOFT_APP_PASSWORD)
adapter = BotFrameworkAdapter(BotFrameworkAdapterSettings(
    app_id=settings.MICROSOFT_APP_ID,
    app_password=settings.MICROSOFT_APP_PASSWORD,
    channel_auth_tenant=settings.MICROSOFT_APP_TENANT_ID,
    credential_provider=provider))
adapter.on_turn_error = on_error
store = LinkStore(settings.IDENTITY_DB_PATH)  # esquema preparado previamente
reader = GLPIUserReader(settings.GLPI_URL, settings.GLPI_APP_TOKEN,
                        settings.GLPI_USER_TOKEN)
service = IdentityService(store, reader, settings.IDENTITY_ALLOWED_TENANT_ID)
ingress = IdentityIngress(settings, service,
    adapter_bundle=(adapter, provider, BotAdapter.BOT_IDENTITY_KEY))

async def route(context, resolve_identity):
    # Nesta etapa, apenas abertura. Futuro fluxo usará await resolve_identity()
    # dentro deste callback, somente após uma seleção explícita e autorizada.
    await logic_process_message(context)

# No endpoint, EM LUGAR de adapter.process_activity(...):
# response = await ingress.dispatch(activity, auth_header, route)
```

O resolver verifica configuração Microsoft, Bearer original, provider com
`is_authentication_disabled()` falso, vínculo do contexto ao adapter, claims
autenticadas e audiência do aplicativo, antes de emitir a capacidade interna.
Não infere autenticação pela presença de tenant/object ID no JSON. A capacidade
é invalidada ao concluir a resolução; o resolver expira ao sair do callback,
inclusive em exceções. Não guardar o resolver para tarefas de fundo ou notificações.
As verificações de claims complementam a autenticação do SDK, não a substituem.

`ok` identifica a pessoa vinculada, mas não autoriza um chamado específico.
A próxima etapa deverá validar requerente, status e privacidade por recurso e
no momento da operação.

## Configurações

Novas variáveis em `Settings`:

| Nome | Padrão | Finalidade |
| --- | --- | --- |
| `IDENTITY_ALLOWED_TENANT_ID` | vazio | UUID do tenant da pessoa explicitamente permitido; vazio bloqueia o novo caminho |
| `IDENTITY_DB_PATH` | `data/identity.sqlite3` | Caminho absoluto ou relativo à raiz do projeto, independente do diretório de execução |

Exemplos fictícios: `IDENTITY_ALLOWED_TENANT_ID=11111111-1111-4111-8111-111111111111`
e `IDENTITY_DB_PATH=/srv/byte-bot-data/identity.sqlite3`.
São necessárias também `MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`,
`MICROSOFT_APP_TENANT_ID`, `GLPI_URL`, `GLPI_APP_TOKEN` e `GLPI_USER_TOKEN`.
Não imprimir seus valores. Tenant de autenticação do aplicativo e tenant permitido
da pessoa são configurações distintas. O `.env` legado continua relativo ao
diretório atual; somente o caminho do banco recebe resolução relativa à raiz.

## Administração local

Execute na raiz, com o interpretador da aplicação. Exemplos fictícios abaixo.
**Create/replace consultam o GLPI real se executados com configuração real**;
não foram executados contra serviços reais nesta entrega.

```sh
python3 -m tools.identity_links --db data/identity.sqlite3 init
python3 -m tools.identity_links --db data/identity.sqlite3 create --tenant 11111111-1111-4111-8111-111111111111 --object-id 22222222-2222-4222-8222-222222222222 --glpi-user-id 42 --operator admin-exemplo --reference aprovacao-123
python3 -m tools.identity_links --db data/identity.sqlite3 get --tenant 11111111-1111-4111-8111-111111111111 --object-id 22222222-2222-4222-8222-222222222222
python3 -m tools.identity_links --db data/identity.sqlite3 revoke --tenant 11111111-1111-4111-8111-111111111111 --object-id 22222222-2222-4222-8222-222222222222 --expected-user-id 42 --operator admin-exemplo --reference revogacao-124
python3 -m tools.identity_links --db data/identity.sqlite3 replace --tenant 11111111-1111-4111-8111-111111111111 --object-id 22222222-2222-4222-8222-222222222222 --expected-user-id 42 --glpi-user-id 43 --operator admin-exemplo --reference aprovacao-125
python3 -m tools.identity_links --db data/identity.sqlite3 audit --tenant 11111111-1111-4111-8111-111111111111 --object-id 22222222-2222-4222-8222-222222222222
```

O operador deve conferir Directory/Tenant ID e Object ID do usuário no Microsoft
Entra do tenant correto, confirmar a conta efetivamente usada no Teams e conferir
o ID exato em Administração/Usuários no GLPI. IDs do aplicativo, bot ou grupo
não substituem Object ID da pessoa. Nomes semelhantes, e-mails e UPNs não
comprovam a correspondência. A aprovação deve referenciar procedimento
administrativo verificável. IDs fornecidos na CLI não provam identidade;
`operator` é afirmação local do administrador, não assinatura autenticada.

Antes de create/replace, a CLI consulta exatamente `GET /User/{id}`, iniciando
e encerrando sessão GLPI. Exige ID coincidente, `is_active=1` e `is_deleted=0`.
Não altera usuários nem chamados. A resolução repete a consulta sem cache e nega
falhas ou respostas incompletas. O serviço usa threads para operações bloqueantes.
Uma segunda leitura recusa mudanças do vínculo durante a revalidação; isso não
constitui transação distribuída ou garantia contra mudança posterior no GLPI.

## Persistência e conflitos

`init` cria esquema versão 1 (`PRAGMA user_version`) em transação; é idempotente
e recusa versões desconhecidas. Cada operação abre/fecha conexão. Alterações
usam `BEGIN IMMEDIATE`, timeout de bloqueio de 10 segundos e SQL parametrizado.
Falha de auditoria reverte a alteração. A chave primária é tenant/object ID;
há índice único de usuário GLPI por tenant entre vínculos ativos.

Create não sobrescreve vínculos, inclusive revogados. Replace exige ID anterior
e aprovação explícita, inclusive para reativar. Revoke também exige ID anterior.
Duas identidades no mesmo tenant não podem apontar ativamente ao mesmo GLPI;
revogue primeiro a associação anterior. Tenants diferentes são namespaces
independentes. Flexibilizar essa política exige análise própria.

Vínculos guardam status, datas UTC, criador, último operador, aprovação e referência.
Auditoria registra criação/revogação/substituição, IDs anterior/novo, operador,
data e referência. Não inserir segredos nos metadados. Auditoria transacional
não é imutável contra quem pode escrever diretamente no SQLite: proteja arquivo,
diretório e CLI com permissões do sistema operacional. Faça backup consistente
pela API SQLite ou com processo parado.

Premissa de implantação: **uma instância com disco local persistente**. Não usar
disco efêmero, compartilhamento de rede ou réplicas distribuídas. Bloqueio SQLite
atende concorrência local moderada. Banco, backups e auxiliares não devem ser
versionados; `.gitignore` cobre extensões usuais, mas confira backups com outros
nomes. Não há persistência de formulários, referências de conversa ou notificações.

## Testes, pendências e remoção

```sh
python3 -m unittest discover -s tests -v
```

Resultado local da etapa 2.1: **21 testes aprovados e 5 testes de SDK pulados**
por ausência dos pacotes. Nenhum skip conta como compatibilidade aprovada.
`tests/test_identity.py` cobre lógica com mocks e SQLite temporário, incluindo
uma passagem pelo adapter, retorno original, abertura sem resolução, bloqueio do
caminho novo e expiração do resolver.

`tests/test_identity_sdk.py` usa classes reais quando os três pacotes estão
instalados: adapter/provider, modelos desserializados, ClaimsIdentity e chave no
turn_state, assinatura/delegação de TeamsInfo.get_member e pipeline real. Apenas
a autenticação e transporte do pipeline são simulados; **não verifica JWT real**.
Com SDK instalado, incompatibilidades de importação/contrato falham em vez de skip.
Ambas as suítes bloqueiam HTTP, DNS e conexões externas e usam bancos temporários. Scripts antigos não foram executados ou modificados.
O sandbox deste ambiente travou o despertar do loop assíncrono pelas threads;
a execução fora dele passou com os mesmos bloqueios de rede da suíte.

Pendente homologar versão instalada, autenticação JWT/adapter, registro do app,
tenant permitido, permissões e atributos efetivos de TeamsInfo (incluindo
convidados), além do contrato/permissões da API GLPI real. Atributo ausente
continua resultando em recusa. Mocks não comprovam integração ou produção.

Não foi identificada/corrigida incompatibilidade do SDK instalado, pois ele
não está acessível. A adaptação corrigiu a composição arquitetural: a proposta
anterior não definia o reaproveitamento do único adapter do endpoint.

Para desativar, não compor IdentityIngress na futura integração e manter
`IDENTITY_ALLOWED_TENANT_ID` vazio. Nesta etapa nenhum fluxo o chama. Para remover,
retire `identity/`, os utilitários/testes específicos e os dois campos novos em
Settings; arquive banco/auditoria conforme política administrativa. Isso não exige
alterar abertura, YAML, UserProfile ou MemoryStorage.

## Verificação local com SDK 4.17.1 — correção da etapa 4

Executado `venv/bin/python -m tools.inspect_identity_sdk` no venv local do usuário: Python 3.12.3; botbuilder-core, botbuilder-schema e botframework-connector 4.17.1; aiohttp 3.14.5; msrest 0.7.1. `python -m pip check` nesse venv não encontrou requisitos quebrados. aiohttp foi declarado explicitamente em requirements.txt; não houve instalação/atualização nesta revisão.

No SDK instalado, `ConversationAccount(tenant_id=...)` corresponde ao JSON `tenantID`, enquanto `TeamsChannelAccount.tenant_id` corresponde a `tenantId`. A fixture anterior usava o nome errado na conversa. Corrigida a fixture, o código de produção permaneceu intacto: tenant válido em channelData e membro Teams é obrigatório; tenant da conversa é opcional e, quando presente, deve concordar. Novos testes negam ausência da fonte obrigatória e divergências, e verificam a construção/desserialização reais.

Dez testes SDK passaram sem skips, incluindo pipeline real do adapter com JWT/Teams simulados e envios bloqueados. As 21 verificações de identidade também passaram; discovery completo: 87 aprovados, zero falhas/erros/pulados. Ver [ticket-query.md](ticket-query.md) e seção 14 do AGENTS.md para os defeitos de isolamento corrigidos nos testes, resultados separados e execução em ordem inversa. Homologação de autenticação e integração reais continua pendente; este venv não foi confirmado como runtime de produção.


## Atualização da etapa 6

Notificações públicas opt-in foram implementadas após esta etapa. Consulte [notifications.md](notifications.md) para captura autenticada, migração SQLite v3, políticas de autores, fila, execução dedicada, retenção e pendências de homologação. Afirmações anteriores neste documento sobre notificações futuras são registros da etapa anterior. Permanecem desabilitadas por padrão, sem validação externa real.
