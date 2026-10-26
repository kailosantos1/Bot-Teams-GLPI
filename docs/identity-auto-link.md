# Vínculo automático por e-mail Microsoft autenticado

A opção `IDENTITY_AUTO_LINK_ENABLED=false` é o padrão. Quando habilitada, a
consulta pessoal pode criar um vínculo local no primeiro acesso seguro.
Não cria usuários nem modifica e-mails, chamados ou permissões no GLPI.
O banco existente deve estar inicializado e em disco local persistente.

## Premissas e limite de confiança

A administração confirmou que o e-mail da conta usada no Teams coincide com um
e-mail cadastrado no GLPI, e que somente a TI pode cadastrar/alterar esses
endereços. Habilitar a opção é a aprovação dessa política de associação.
Mantenha essa exclusividade efetiva também em perfis, autosserviço e integrações;
o bot não audita quem tem permissão de alterar e-mails no servidor GLPI.
Não se presume que UPN seja e-mail ou que nomes iguais provem identidade.

A resolução conserva autenticação do adapter, audiência do aplicativo, tenant
permitido, canal Teams, conversa pessoal e correspondência exata entre remetente
e membro consultado por TeamsInfo. Só o `email` retornado pela API autenticada
para esse membro validado entra na busca. E-mail ausente/inválido bloqueia a
nova associação. UPN, nome, corpo da atividade, texto digitado e botões não são
substitutos. O bot não solicita senha, e-mail, código ou ID à pessoa.

## Contrato GLPI adotado

Referência **GLPI 10.0.18 REST v1**; não é homologação da versão implantada:

- [User::rawSearchOptions](https://github.com/glpi-project/glpi/blob/10.0.18/src/User.php): opção 2 identifica o usuário; opção 5 pesquisa os filhos `glpi_useremails.email` com agrupamento por usuário. Abrange e-mails adicionais, não apenas o padrão.
- [UserEmail](https://github.com/glpi-project/glpi/blob/10.0.18/src/UserEmail.php): filho de User com chave `users_id` e campo `email`; `is_default` não restringe a associação.
- [REST v1](https://github.com/glpi-project/glpi/blob/10.0.18/apirest.md): `GET /search/User`, `GET /User/{id}` e `GET /User/{id}/UserEmail`, com paginação. `initSession`/`killSession` somente para sessão de leitura.

`GET /search/User` usa critério 5 `contains`, exibição forçada do ID na coluna 2,
ordem crescente por ID e `is_deleted=0`. É busca de candidatos; não prova a
associação, mesmo que o servidor retorne um só resultado. Todos os candidatos
e suas páginas são considerados; IDs repetidos do mesmo usuário são deduplicados.
As colunas de e-mail agregadas/formatadas da pesquisa são ignoradas.

Para cada candidato ativo e não excluído, `GET /User/{id}/UserEmail` lê todas as
páginas e valida ID da relação, pai exato e campo e-mail. O endereço é comparado
por igualdade após **somente strip e lower**, tanto no valor Microsoft quanto
no GLPI. Não se removem pontos, `+sufixos`, acentos ou partes do domínio; não
há transformação de UPN, IDNA ou endereços parecidos. O payload é solicitado
com conteúdo GLPI não sanitizado e IDs não expandidos, sem interpretar HTML ou
decodificar entidades como forma de normalização de e-mail.

Somente um usuário ativo/não excluído exato permite associação. E-mails repetidos
no mesmo usuário não são ambiguidade; dois usuários ativos são. Zero candidatos,
nenhuma igualdade, ambiguidades, campos ausentes, IDs inválidos, total variável,
página faltante, resposta inesperada e erro HTTP negam, sem escolher o primeiro.
Coleções vazias aceitam apenas 200 na primeira página com total zero explícito
ou Content-Range ausente conforme o contrato APIRest. Pesquisa não vazia exige
`count`, `totalcount` e `content-range` coerentes com a página solicitada.

Limites por busca: até 200 registros na pesquisa e em cada coleção de e-mails,
500 requisições, orçamento cooperativo de 60 segundos, timeout de conexão/leitura
até 5 segundos por GET e encerramento de sessão em finally. São reaproveitados
os limites/transportes existentes, sem retries ou redirects. Limite excedido
nega; não se considera o subconjunto como resultado completo. O acesso inicial
repete a busca exata completa para revalidar unicidade antes de persistir, além
de verificar o usuário GLPI antes/depois da gravação. Pode exigir mais tempo que
acessos seguintes. Requests não garante prazo absoluto para corpo lento.

Homologue permissões de leitura, entidades, collation/pesquisa sem distinção de
caixa, campos e paginação da instalação: uma conta com visibilidade parcial não
comprova unicidade global. Sem essas condições, mantenha a opção desabilitada e
use a CLI. Não faça buscas sem filtro ou por nome para contornar uma negação.

## Persistência, concorrência e vínculos anteriores

A chave continua `(tenant ID, object ID Entra) → usuário GLPI`. O caminho novo só
é chamado quando a primeira leitura não encontra vínculo. Antes de criar, repete
a busca e a revalidação do candidato. SQLite verifica novamente a ausência na
transação de criação e aplica o índice único de usuário GLPI por tenant.

O mesmo armazenamento e auditoria transacional são usados, sem alteração de
schema. Metadados de origem:

- `created_by`/operador: `system:teams-email-auto-link`;
- referência da política: `policy:authenticated-microsoft-email-v1`;
- ação: `create`, com IDs e datas já previstos na auditoria.

E-mail, UPN, nome, tokens e resposta de API não são acrescentados ao vínculo ou
aos logs. Esses metadados identificam decisão automática autorizada pela política,
não uma conferência humana individual nem assinatura externa.

Duas criações equivalentes podem reutilizar o único vínculo ativo resultante;
a auditoria não é duplicada. Uma criação concorrente com outro alvo, vínculo
revogado ou mesmo usuário GLPI já associado a outra identidade ativa no tenant
nega, sem substituir/reactivar nada. O vínculo retornado ainda passa pela
revalidação GLPI e comparação final com o banco.

Vínculos existentes, manuais ou automáticos, seguem o caminho anterior. E-mail
novo ou ausente não muda o alvo existente. Usuário vinculado inativo/excluído
nega e não dispara busca alternativa. Revogação nunca dispara recriação.
Correções/reativações continuam administrativas via CLI existente, com ID
anterior esperado e referência da aprovação.

Não há transação SQLite aberta durante HTTP. Não existe transação distribuída
entre Microsoft, GLPI e SQLite: mudanças posteriores à última leitura ainda têm
uma janela inerente. Antes de listar, detalhar, responder ou notificar, as
revalidações por identidade/requerente/status/publicidade continuam obrigatórias.

## Experiência, diagnóstico e notificações

Sucesso segue diretamente à lista pessoal. A associação não autoriza um ticket
por si só; a consulta reconfirma requerente individual, inclusive se uma pesquisa
GLPI devolver IDs de outros usuários. Em falha da associação:

> Não consegui vincular sua conta aos chamados. Entre em contato com o suporte de TI.

No modo automático, negações de identidade também mantêm essa mensagem simples.
Não se informa existência de outra conta nem e-mail ou detalhes técnicos.
Logs usam apenas os códigos seguros do consumidor existente:

| Código | Categoria |
| --- | --- |
| `email_missing` | E-mail do membro autenticado ausente; sem fallback UPN |
| `email_invalid` | E-mail autenticado inutilizável; não solicitar outro pelo chat |
| `email_no_match` | Nenhum usuário ativo/não excluído com igualdade exata |
| `email_ambiguous` | Mais de um usuário ativo correspondente |
| `email_changed` | Resultado/alvo/elegibilidade alterado antes da criação |
| `link_conflict` | Vínculo concorrente incompatível ou unicidade conflitante |
| `link_revoked` | Vínculo revogado; somente ação administrativa pode corrigir |
| `auto_link_unavailable` | Busca/revalidação/persistência automática indisponível ou incompleta |

Códigos anteriores de configuração/autenticação/GLPI permanecem. Com a opção
desabilitada, vínculo ausente continua `link_missing` e não há busca por e-mail.

O resultado seguro mantém ID e revisão do vínculo, alimentando a captura pessoal
de notificações existente no mesmo callback. Consumidores simultâneos da mesma
atividade compartilham a resolução via lock local, inclusive a chamada Teams e
captura de referência; não há um segundo adapter. O resolver expira ao terminar
o callback. Não se habilitam notificações globalmente nem se alteram listas de
grupos/integração. Se notificações já estiverem habilitadas, todas as políticas,
baselines e revalidações continuam aplicáveis.

## Atualizar e habilitar com PowerShell

Comandos destinados ao administrador, **não executados no servidor nesta entrega**.
Não houve commit/push: os arquivos desta entrega ainda precisam ser implantados
pelo processo de revisão/distribuição existente. Um `git pull` sozinho não leva
mudanças locais não publicadas ao servidor. Inclua o módulo novo
`identity/email_lookup.py` e as demais alterações de identidade/configuração/main;
não sobrescreva configurações ou SQLite. Testes e AGENTS.md permanecem internos,
fora do versionamento conforme `.gitignore`.

Na janela operacional autorizada, selecione a raiz e o Python realmente usados
pelo serviço, ajustando os caminhos de exemplo. Use a mesma conta e ambiente;
uma sessão interativa pode diferir do serviço. Faça backup consistente do banco
pelo procedimento existente antes da atualização; não remova vínculos/banco.

```powershell
$Project = 'C:\Bots\Bot-Teams-GLPI'
$Python = Join-Path $Project 'venv\Scripts\python.exe'
Set-Location -LiteralPath $Project
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Python do servico nao encontrado.' }
& $Python -m py_compile main.py config.py identity\service.py identity\ingress.py identity\store.py identity\email_lookup.py identity\diagnostics.py bot\ticket_consult.py
if ($LASTEXITCODE -ne 0) { throw 'Fontes incompletas ou invalidas.' }
& $Python -m tools.inspect_identity_sdk
& $Python -m tools.inspect_identity_configuration
if ($LASTEXITCODE -ne 0) { throw 'Revise configuracao sem imprimir valores sensiveis.' }
# Se os testes internos revisados estiverem presentes no ambiente de homologacao:
& $Python -m tests.run_offline_suite
if ($LASTEXITCODE -ne 0) { throw 'Suite offline nao aprovada.' }
```

Esses comandos são locais: não consultam Teams/GLPI. Não imprimem credenciais;
a inspeção mostra presença e o estado efetivo do novo flag. Confirme banco,
permissões e vínculos conforme [procedimento do servidor](server-identity-powershell.md).
Não inicialize um banco novo para contornar caminho incorreto.

Após conferir as premissas administrativas, altere **somente** a opção no
mecanismo real de configuração do serviço. Se for o `.env` existente, edite
apenas essa linha pelo editor autorizado, preservando as demais configurações:

```dotenv
IDENTITY_AUTO_LINK_ENABLED=true
```

Não use Get-Content/Set-Content para copiar ou reescrever todo o arquivo com
segredos em um terminal/transcrição. Para conferir a opção nesta sessão, sem
iniciar o bot nem consultar serviços:

```powershell
$env:IDENTITY_AUTO_LINK_ENABLED = 'true'
& $Python -m tools.inspect_identity_configuration
if ($LASTEXITCODE -ne 0) { throw 'Configuracao indisponivel.' }
```

A atribuição acima só afeta esta sessão e filhos; não configura sozinha um
serviço Windows existente. Aplique o flag ao ambiente real do serviço e
recarregue/reinicie pelo procedimento operacional da instalação. Nenhum nome de
serviço fictício ou comando automático de reinício é fornecido. Reiniciar perde
formulários/navegação em memória; agende a janela apropriada. Não altere
`NOTIFICATIONS_ENABLED`, grupos ou integrações para habilitar esta funcionalidade.

Somente na homologação autorizada, a pessoa escolhe “Consultar meus chamados”
na conversa pessoal. **Essa ação consulta Teams/GLPI reais e pode criar vínculo
local**. Falhas são tratadas pela TI usando os códigos seguros. Nenhum comando
do roteiro dispara essa ação automaticamente.

Para desabilitar, configure `IDENTITY_AUTO_LINK_ENABLED=false` no serviço; se
precisar refletir isso nesta sessão, use:

```powershell
$env:IDENTITY_AUTO_LINK_ENABLED = 'false'
& $Python -m tools.inspect_identity_configuration
```

Recarregue o serviço conforme a janela aprovada. Isso bloqueia somente novas
associações automáticas; vínculos ativos já criados continuam utilizáveis.
Para bloquear uma pessoa, use a revogação administrativa existente. Não apague
SQLite, auditoria ou filas. A CLI `create`/`replace` continua consultando GLPI
real; `get`/`audit`/`revoke` com banco explícito são locais. Consulte os comandos
completos no [roteiro administrativo](server-identity-powershell.md).

## Verificação local e pendências

Testes usam o venv existente, rede globalmente bloqueada e bancos temporários.
Cobrem igualdade/normalização, e-mails secundários e duplicados por usuário,
ambiguidades, inativos/excluídos, páginas incompletas/falhas, concorrência,
revogação e preservação de vínculos, isolamento A/B e captura de notificações.
Não alteram `.env`, credenciais ou banco real. Não validam JWT real, visibilidade
integral de entidades/e-mails, a exclusividade administrativa da TI ou a
renderização no cliente Teams. Esses pontos permanecem para homologação humana
no servidor; PowerShell não está instalado neste ambiente para executar o roteiro.
