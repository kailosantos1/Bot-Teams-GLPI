# Matriz de botões e anexos de entrada

## Matriz final

| Tela | Ações |
| --- | --- |
| Menu | `1 — Abrir chamado`, `2 — Consultar chamados`, `3 — Sair` |
| Início da abertura | `0 — Voltar ao menu` |
| Confirmação/troca de formulário | opções numeradas da etapa atual |
| Escolha única/múltipla | opções numeradas; em múltipla, `Continuar` usa o número seguinte |
| Página de opções | números originais; `Voltar` e `Mais opções` usam números fora das opções |
| Anexos | `1 — Sim`, `2 — Não`; na coleta, `1 — Concluir anexos` |
| Lista de chamados | chamados `1–5`; `7 — Anteriores`, `9 — Próximos` quando disponíveis; `8 — Atualizar`; `0 — Menu` |
| Detalhes | `1 — Conversa`, `2 — Responder`, `3 — Meus chamados`, `0 — Menu`; descrição dividida usa `7 — Trecho anterior` e `9 — Ver mais` |
| Conversa | `4 — Voltar ao chamado`, `8 — Atualizar`; `7/9` aparecem somente quando existe direção disponível |
| Resposta | cancelar, enviar e editar somente nas etapas correspondentes; confirmação mantém `1/2/0` |
| Notificação | `Ver chamado`; interrupção de formulário/rascunho mantém as confirmações vinculadas ao estado |

Na conversa, `7/9` recebem nomes contextuais: `Mensagens mais recentes`,
`Mensagens mais antigas`, `Parte anterior` ou `Continuar mensagem`. A ordem
continua sendo a mesma do serviço: mais recentes primeiro. Não se exibe um
contador inventado de mensagens quando o serviço só conhece os registros/partes
carregados.

O construtor de consulta não divide mais arbitrariamente os botões a cada cinco.
Essa divisão local era a causa do cartão isolado “Navegação”. O contrato oficial
do HeroCard expõe um array de botões e não documenta cinco como limite; as telas
foram reduzidas antes de manter uma única unidade visual. O formato HeroCard e os
payloads `messageBack` existentes foram preservados.

Referências oficiais: [tipos e propriedades de cartões](https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-reference) e [formatação de cartões](https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-format).

## Classificação de anexos recebidos

A causa confirmada da recusa de “teste” era `bool(activity.attachments)` na
captura de resposta. O Teams pode acompanhar `activity.text` com uma representação
técnica `text/html`; ela não é um arquivo do usuário.

A classificação compartilhada agora considera técnica somente uma entrada
`text/html` sem nome, `content_url` ou `downloadUrl`. Seu conteúdo nunca é lido,
executado ou usado como resposta. A resposta sempre vem de `activity.text`.
Arquivos, imagens, HTML enviado como arquivo e tipos desconhecidos continuam
sendo anexos reais.

Na resposta ao chamado, texto acompanhado de arquivo real não é salvo nem
enviado, e o arquivo também não é enviado: a tela pede que o usuário remova o
arquivo e reenvie o texto. Nas perguntas textuais do formulário vale a mesma
regra; arquivos continuam disponíveis apenas na etapa própria de anexos. Isso
evita descartar silenciosamente qualquer uma das duas entradas.

## Exemplos

```text
Olá, Ana! Como posso ajudar?
Escolha uma opção ou digite o número.
[1 — Abrir chamado]
[2 — Consultar chamados]
[3 — Sair]
```

```text
🎫 Chamado #1028
Manutenção de Equipamentos
Situação: Em atendimento

📝 Solicitação
Tipo: Manutenção de Equipamentos
Local: Matriz
[1 — Conversa] [2 — Responder] [3 — Meus chamados] [0 — Menu]
```

```text
💬 Conversa · #1028
Mais recentes primeiro

Teams Bot
26/10/2026 às 19:52 — horário do GLPI

Chamado aberto pelo Teams — Otto Bot de Chamados
[4 — Voltar ao chamado] [8 — Atualizar] [9 — Mensagens mais antigas]
```

## Homologação pendente no Teams

- Conferir todos os cartões em desktop, web, Android e iOS, especialmente uma
  lista com cinco chamados e todos os controles disponíveis.
- Confirmar que o cliente envia a representação técnica exatamente como
  `text/html` sem metadados de arquivo; qualquer variação desconhecida continuará
  sendo recusada com segurança até ser documentada.
- Exercitar menu, paginação temporal, mensagem longa, formulário, resposta e
  notificação com cartões enviados antes e depois da atualização.
- Confirmar visualmente os parágrafos HTML suportados em HeroCard. A documentação
  oficial alerta que a renderização pode variar entre desktop e dispositivos móveis.

Os testes são locais, com SDK real para modelos/serialização, GLPI mockado e rede
bloqueada. Eles não homologam JWT, transporte ou renderização real do Teams.
