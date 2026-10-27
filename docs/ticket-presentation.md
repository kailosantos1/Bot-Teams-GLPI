# Apresentação da lista, solicitação e conversa

Mudança somente de apresentação: identidade automática, autorização por
requerente, estados/TTL/versões, ações, captura/envio de respostas e políticas
notificações permanecem. Não requer configuração ou migração de banco.

## Lista

```text
📋 Seus chamados
Escolha um chamado ou digite o número.

[1 — #1028 · Manutenção]
[8 — Atualizar]
[0 — Menu]
```

O exemplo usa o título “Solicitações de Manutenção”. O resumo remove apenas
prefixos iniciais conhecidos e redundantes, depois limita a 24 caracteres com
corte em espaço e reticência quando necessário. É determinístico, sem IA, sem
consultas adicionais e sem alterar título original. Cada número continua ligado
ao ID da mesma página; anteriores/próximos mantêm 7/9, atualização 8 e menu 0.
Não entram status nem título completo no botão. Lista vazia continua explícita.

## Solicitação

```text
🎫 Chamado #1028
Manutenção de Equipamentos
Situação: Em atendimento

📝 Solicitação
Tipo: Manutenção de Equipamentos

Local: Matriz

Problema:
erro

Contato: WhatsApp
Número: 49999454437
Urgência: Médio

Campo adicional: conteúdo original
ATENÇÃO: aviso original preservado

[1 — Conversa]
[2 — Responder]
[3 — Meus chamados]
[0 — Menu]
```

Campos e valores acima ilustram conteúdo de teste, não são inseridos em chamados
pelo bot. A conversão usa estrutura HTML, não posições fixas ou uma lista de
campos deduzidos: pares em linhas com cabeçalho/ênfase de rótulo ou dois-pontos
explícitos tornam-se rótulo/valor. Linhas desconhecidas de tabela preservam suas
células em ordem; parágrafos, seções, listas, títulos e avisos mantêm texto visível.
Não se removem rótulos de perguntas, campos adicionais ou advertências do
Formcreator. Não se tenta corrigir suas regras. Elementos desconhecidos mantêm
texto; profundidade excessiva usa o sanitizador anterior como fallback. Scripts,
recursos remotos, links/menções e entidades continuam tratados passivamente.

Somente a apresentação de títulos remove prefixos ancorados, como “Solicitações
de ” ou “Chamado #1028 — ” quando o ID coincide. O título completo restante é
mostrado, sem o corte antigo de 120 caracteres. Dados de origem não são alterados.
A descrição inteira continua acessível pelos controles existentes 7/9, em
partes de até 1200 caracteres. Indicador aparece só quando há várias partes.
Um título excepcionalmente maior que 1200 caracteres também é paginado pelo
mesmo fluxo, antes da descrição, em vez de truncado ou enviado sem limite.

## Conversa pública

```text
💬 Conversa · #1028
Mais recentes primeiro

Teams Bot
26/10/2026 às 19:52 — horário do GLPI

Chamado aberto pelo Teams — Otto Bot de Chamados

[4 — Voltar]
[8 — Atualizar]
[3 — Meus chamados]
[0 — Menu]
```

Mantém um registro/trecho por página e a ordem existente. Não oculta mensagens
públicas por autoria do bot. Autor, horário e conteúdo ficam em parágrafos
separados. “Página x/y” aparece somente com várias páginas; “Trecho x/y” somente
quando a própria mensagem tem várias partes. Não se exibem os prefixos técnicos
“Autor:”/“Data:” adicionados anteriormente pelo bot; conteúdo original que
contenha essas palavras não é removido.

A data é exibida em dia/mês/ano e hora:minuto, sem conversão de fuso ou uso do
fuso da máquina. A origem “horário do GLPI” permanece explícita. Segundos continuam
nos dados e na ordenação; só a exibição os omite. Nenhum offset UTC é presumido.

## Renderização e segurança

O componente continua sendo HeroCard. A documentação oficial descreve suporte
a HTML nesse tipo e exemplifica parágrafos `<p>`:
[Formatar HeroCards no Teams](https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-format#format-example-for-simple-cards).
A mudança não confia apenas em `\n`: somente nas telas de leitura/lista, cada
linha de apresentação recebe um parágrafo criado pelo bot. O texto é escapado
antes de entrar no wrapper; HTML do GLPI não é enviado para execução. Não são
criadas tags de link, imagens, menções, estilos ou scripts. Não há conversão
global Markdown→HTML. Outros cartões, formulários e rascunhos conservam a
apresentação anterior.

MIME, CardFactory público e ações messageBack originais permanecem, incluindo
payloads query/detail, versões e draft onde já existia. Não há Activity.text
copiado junto com cartão nem listas de opções repetidas no corpo. A divisão
anterior em até cinco botões por cartão é mantida. O processamento da descrição
ocorre depois da autorização existente; sanitização de mensagens públicas,
filtros de privacidade e leituras HTTP não são ampliados.

## Verificação

`venv/bin/python -m tests.run_offline_suite` executa a suíte com HTTP/DNS/sockets/
aiohttp bloqueados globalmente. Novos testes conferem o payload final pelo
serializador ConnectorClient do SDK com adapter de captura, parágrafos reais,
botões/seleções, prefixos/títulos longos, dados Formcreator/desconhecidos, avisos,
Unicode/HTML/URLs/menções, paginação, datas e ações antigas. Fixtures locais não
comprovam a estrutura exata do Formcreator implantado ou a renderização real.

Após atualizar os arquivos, conferir visualmente no Teams desktop/web/móvel:
separação e espaçamento dos parágrafos, botões curtos, títulos com acentos,
campos longos, navegação, avisos e conversa. Não houve envio real ao Teams ou
consulta real ao GLPI durante esta alteração.
