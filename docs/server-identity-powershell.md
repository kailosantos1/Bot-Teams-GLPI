> Alternativa nova e opcional ao cadastro individual pela CLI: [vínculo automático e PowerShell](identity-auto-link.md). `IDENTITY_AUTO_LINK_ENABLED=false` mantém o comportamento manual deste roteiro.

# Homologação: identidade no servidor e apresentação no Teams

Procedimento para execução humana no servidor. Nenhum comando desta página foi
executado contra Teams/GLPI reais nesta entrega. Use a conta, o diretório de
trabalho, o interpretador e as configurações efetivamente usados pelo serviço.
Uma sessão PowerShell interativa pode ter variáveis diferentes das do serviço.
A inspeção dessa sessão não comprova a configuração do processo em execução.
Não copie `.env`, cabeçalhos, tokens, dados de membros ou referências de conversa
para logs, tickets ou transcrições de PowerShell.

## 1. Diagnóstico local, sem rede

Ajuste apenas os caminhos de exemplo, que não representam o servidor real:

```powershell
$Project = 'C:\Bots\Bot-Teams-GLPI'
$Python = Join-Path $Project 'venv\Scripts\python.exe'
Set-Location -LiteralPath $Project
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Selecione o executavel Python que inicia o bot.'
}
& $Python -m tools.inspect_identity_sdk
if ($LASTEXITCODE -ne 0) { throw 'Inspecao do SDK falhou.' }
& $Python -m tools.inspect_identity_configuration
if ($LASTEXITCODE -ne 0) { throw 'Configuracao indisponivel; revise o ambiente sem imprimir seus valores.' }
$Db = & $Python -m tools.inspect_identity_configuration --db-path
if ($LASTEXITCODE -ne 0) { throw 'Caminho do banco indisponivel.' }
$Db = [string]$Db
Write-Host ('Banco resolvido: ' + $Db)
Write-Host ('Arquivo existente: ' + (Test-Path -LiteralPath $Db -PathType Leaf))
```

`inspect_identity_sdk` inspeciona bibliotecas locais. O novo
`inspect_identity_configuration` carrega Settings como a aplicação e imprime
apenas nomes e estados, sem valores de credenciais; `--db-path` imprime somente
o caminho resolvido. Nenhum deles consulta Teams ou GLPI. O segundo não faz
busca por nome, não imprime vínculos, não inicializa nem migra SQLite.
Ele verifica presença de:

- `MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`, `MICROSOFT_APP_TENANT_ID`;
- `IDENTITY_ALLOWED_TENANT_ID`, `IDENTITY_DB_PATH`;
- `GLPI_URL`, `GLPI_APP_TOKEN`, `GLPI_USER_TOKEN`.

Para os IDs de aplicação/tenant, também informa se a sintaxe UUID é válida,
sem exibir o UUID. Presença não comprova validade do segredo, permissões ou
registro do aplicativo. Settings usa `.env` no diretório atual; variáveis de
ambiente têm precedência. `IDENTITY_DB_PATH` relativo é resolvido contra a raiz
do projeto, independentemente do diretório de trabalho.

Interpretação do banco:

| Resultado | Ação |
| --- | --- |
| `schema_current` | Versão 3 e tabelas esperadas presentes; confira ACL e conta do serviço. Não precisa executar init. Não comprova integridade completa ou existência do vínculo. |
| `missing` | Primeiro confira o caminho e o disco persistente. Não crie outro banco para contornar caminho errado. Inicialize somente se for de fato uma instalação nova. |
| `schema_upgrade_required` | Schema 1/2 encontrado. Faça backup consistente e programe migração incremental com a CLI existente. |
| `schema_incomplete`, `unsupported_schema`, `unavailable` | Pare para diagnóstico de arquivo/permissões/esquema. Não apague, substitua nem inicialize um arquivo danificado. |
| `path_missing`, `configuration_unavailable` | Corrija a configuração do serviço antes de prosseguir. Erros de Settings são ocultados para não imprimir entradas sensíveis. |

Conferência opcional da ACL, somente local, sem alterar permissões:

```powershell
if (Test-Path -LiteralPath $Db -PathType Leaf) {
    Get-Acl -LiteralPath $Db | Select-Object -ExpandProperty Access
}
```

A saída da ACL contém nomes de contas administrativas; mantenha-a restrita.
Confira também permissão no diretório para SQLite criar seus auxiliares. Use
uma instância com disco local persistente, sem réplicas nem pasta de rede.

## 2. Conferir os três identificadores

No portal administrativo, selecione o diretório que hospeda a pessoa no Teams.
Em Microsoft Entra ID → Visão geral, confira **Tenant ID / Directory ID**.
Em Usuários → perfil da pessoa, obtenha seu **Object ID** nesse mesmo tenant.
A Microsoft documenta essas duas localizações em
[Localizar IDs do tenant e do usuário](https://learn.microsoft.com/en-us/partner-center/account-settings/find-ids-and-domain-names).
Para convidados, confira o objeto do usuário no tenant permitido, não o objeto
da organização de origem.

Confirme com a pessoa qual conta está efetivamente conectada ao Teams.
Não use Object ID da aplicação, service principal, bot ou grupo. Não deduza
Object ID a partir de nome, e-mail ou UPN. E-mail e UPN podem ser diferentes.

No GLPI, um administrador deve abrir a ficha exata em Administração → Usuários,
conferir o ID numérico interno do usuário, seus dados administrativos e que a
conta está ativa e não excluída. Não confunda com ID de chamado ou matrícula.
A correspondência entre a pessoa do Teams e a ficha GLPI exige conferência
humana documentada; sem certeza, não crie o vínculo.

## 3. Configurar o serviço sem expor credenciais

Mantenha os segredos Microsoft/GLPI no mecanismo já usado pelo serviço.
Não execute `Get-Content .env`, `Get-ChildItem Env:` nem imprima Settings inteiro.
Corrija somente os campos identificados como ausentes/inválidos pelo diagnóstico,
por editor ou gerenciador de segredos autorizado. Para senha Microsoft, use o
valor do segredo da aplicação, não o identificador do segredo.

`MICROSOFT_APP_ID` identifica a aplicação do bot; `MICROSOFT_APP_TENANT_ID` é o
tenant de autenticação da aplicação. `IDENTITY_ALLOWED_TENANT_ID` é o tenant
permitido para a pessoa; não os torne iguais por suposição. Tenant permitido
vazio bloqueia consulta sem desativar a abertura legada.

Após conferência humana, esta sessão pode receber os valores **não secretos**
a seguir. Não altere o caminho para um banco vazio quando já houver um banco de
produção. Use o caminho persistente aprovado que contém os vínculos existentes.

```powershell
$Tenant = Read-Host 'Tenant ID da pessoa, conferido no diretorio permitido'
$ObjectId = Read-Host 'Object ID Entra da pessoa nesse tenant'
$GlpiUserId = Read-Host 'ID numerico da ficha GLPI conferida'
$ParsedTenant = [guid]::Parse($Tenant)
$ParsedObject = [guid]::Parse($ObjectId)
if ($GlpiUserId -notmatch '^[1-9][0-9]*$') { throw 'ID GLPI invalido.' }
$Tenant = $ParsedTenant.ToString()
$ObjectId = $ParsedObject.ToString()
$env:IDENTITY_ALLOWED_TENANT_ID = $Tenant
$env:IDENTITY_DB_PATH = $Db
& $Python -m tools.inspect_identity_configuration
```

Essas atribuições atingem somente a sessão e seus processos filhos. Aplique as
mesmas configurações não secretas no mecanismo real de inicialização do serviço
ou no `.env` efetivo, sem trocar os segredos existentes. Recarregue/reinicie o
serviço conforme o procedimento operacional autorizado. Reinício perde
navegação e formulários em memória: agende a janela; não confunda com banco de
vínculos, que deve permanecer no disco persistente. Não há comando de reinício
automático neste roteiro.

## 4. Inicializar sem substituir banco existente

**Só para instalação nova, após confirmar que não existe banco anterior em outro
caminho:**

```powershell
if (Test-Path -LiteralPath $Db) { throw 'Banco existente: nao inicialize como instalacao nova.' }
& $Python -m tools.identity_links --db $Db init
if ($LASTEXITCODE -ne 0) { throw 'Inicializacao negada; nao remova nenhum arquivo.' }
& $Python -m tools.inspect_identity_configuration
```

Esse comando escreve somente no SQLite local, sem GLPI. A CLI atual inicializa
schema 3. Para banco versão 1/2, `init` migra incrementalmente sem apagar
links/auditoria: faça primeiro backup consistente pela API SQLite ou com os
processos que escrevem parados, valide o backup e autorize a migração na janela
operacional. Só então execute a mesma CLI `init` com o caminho existente. Não
use cópia simples de um SQLite ativo como garantia de backup consistente.
Não use `Remove-Item`, `replace`, `revoke` ou edição SQL para contornar conflitos.

## 5. Conferir e criar vínculo administrativo

Somente depois de o banco correto estar inicializado e os IDs conferidos:

```powershell
# LOCAL: le o vinculo sem consultar GLPI. O JSON contem dados administrativos.
$LinkJson = & $Python -m tools.identity_links --db $Db get --tenant $Tenant --object-id $ObjectId
if ($LASTEXITCODE -ne 0) { throw 'Leitura negada; confira banco e esquema.' }
$Link = $LinkJson | ConvertFrom-Json
if ($null -ne $Link) {
    throw 'Ja existe vinculo, ativo ou revogado. Confira-o localmente; nao sobrescreva.'
}
# LOCAL: auditoria; pode conter IDs e operadores. Nao publique esta saida.
& $Python -m tools.identity_links --db $Db audit --tenant $Tenant --object-id $ObjectId
if ($LASTEXITCODE -ne 0) { throw 'Auditoria indisponivel.' }
```

Após a conferência humana e a aprovação administrativa, execute separadamente:

```powershell
$Operator = Read-Host 'Identificacao do operador administrativo (sem segredos)'
$Reference = Read-Host 'Referencia da aprovacao humana (sem segredos)'
# CONSULTA GLPI REAL e, se aprovado, GRAVA o vinculo no SQLite local.
& $Python -m tools.identity_links --db $Db create --tenant $Tenant --object-id $ObjectId --glpi-user-id $GlpiUserId --operator $Operator --reference $Reference
if ($LASTEXITCODE -ne 0) { throw 'Criacao negada; nao tente sobrescrever o vinculo.' }
```

`create` inicia uma sessão GLPI, consulta exatamente `GET /User/{id}` e encerra
a sessão; não altera usuários/chamados GLPI. Valida conta ativa/não excluída antes
de gravar vínculo e auditoria locais. Não prova automaticamente a correspondência
humana. A CLI recusa vínculo já existente, mesmo revogado, e conflito com outro
vínculo ativo do mesmo usuário GLPI no tenant. Não use `replace` como tentativa
para fazer o teste passar. Investigue o vínculo prévio com o responsável.

`get`, `audit` e `init --db ...` são locais. `create` e a operação administrativa
existente `replace` consultam GLPI; `replace` não é necessário neste procedimento.
A seleção real “Consultar meus chamados” também consulta Teams/GLPI e deve ser
homologada separadamente pelo usuário autorizado. Não a execute como teste
local/offline.

## 6. Ler os novos logs

Exemplo seguro: `bot.identity: identity_failure code=link_missing`.
A mensagem apresentada à pessoa continua simples, sem o código interno.

| Código/evento | Conferir |
| --- | --- |
| `authentication_configuration` | Presença/sintaxe das configurações Microsoft e tenant permitido; concordância da composição do serviço. |
| `unauthenticated`, `authentication_disabled`, `authentication_failed` | Pipeline autenticado/registro da aplicação; não habilite bypass nem confie no corpo da atividade. |
| `identity_missing`, `identity_mismatch`, `tenant_denied`, `personal_only`, `wrong_channel` | Identidade autenticada, tenant permitido, Teams pessoal e correspondência com TeamsInfo. Não use nome como fallback. |
| `teams_unavailable` | Disponibilidade/permissões do acesso autenticado ao membro Teams. |
| `link_missing`, `link_revoked`, `link_changed` | Banco/caminho correto e aprovação administrativa do vínculo. Revogação não é corrigida criando vínculo automático. |
| `identity_unavailable` | Resolver ausente/exceção/código inesperado ou leitura do vínculo indisponível. A categoria é deliberadamente limitada; confira composição, SDK, banco e permissões localmente. |
| `glpi_unavailable`, `glpi_missing`, `glpi_inactive`, `glpi_deleted`, `glpi_incomplete` | Consulta exata ao usuário GLPI; configuração/permissões/disponibilidade/estado e contrato da API. |
| `ticket_query_failure code=query_unavailable` | Identidade já aceita; falha posterior na listagem/estado. Conferir API de chamados, paginação, limites e permissões. |
| `ticket_query_failure code=ticket_unavailable` | Recurso selecionado não autorizado/disponível; não revela requerentes nem conteúdo. |
| `ticket_conversation_failure code=conversation_unavailable` | Falha posterior de leitura/estado da conversa/resposta; rascunho permanece protegido. |

Não há impressão de tokens, exceções, respostas API, nomes, e-mails, IDs,
referências de conversa ou objetos IdentityResult nesses eventos. Códigos não
reconhecidos viram `identity_unavailable`, sem copiar texto arbitrário ao log.
Esses eventos exigem que a atividade alcance o consumidor. JWT recusado antes
do callback não produz IdentityResult ali e continua sujeito ao tratamento do
adapter/servidor. Os logs legados de outros fluxos não foram redesenhados.

## 7. Formatação por componente

A [documentação oficial de cartões](https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-format#html-format-for-hero-and-thumbnail-cards)
descreve HTML para Hero/Thumbnail e Markdown para campos específicos de Adaptive
Cards. Mensagens de texto têm regras próprias, descritas em
[Formatação de mensagens](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/format-your-bot-messages).

O projeto mantém HeroCards e seus botões. Os textos próprios dos HeroCards usam
texto simples: “deseja anexar algum arquivo”, sem delimitadores Markdown ou tags
de negrito. Antes do attachment, caracteres HTML de `HeroCard.text` são
codificados uma única vez; não se interpretam dados externos como HTML. Não há
conversão global Markdown→HTML, processamento de Markdown de usuário nem
segunda decodificação de entidades. A sanitização de GLPI e das prévias permanece
inalterada. Textos comuns mantêm seu Markdown anterior; `Activity.text` não
recebe cópia do corpo do cartão. Não foi introduzido Adaptive Card ou modo de
mensagem novo.

Verificar visualmente em Teams desktop/web/móvel: anexos, confirmação/troca,
perguntas, interrupção/retomada, detalhes/conversa e rascunho. Testes de payload
não comprovam a renderização real nem autenticação/JWT ou integração implantada.
