# API web e integração Teams

[[obsidian/05 - Interfaces e Integracoes/Indice|← Interfaces]] · [[obsidian/Inicio|Início]]

## API FastAPI

| Método/rota | Código | Semântica observada |
|---|---|---|
| `POST /api/messages` | [main.py](../../../main.py#L194) | Recebe Activity JSON, repassa Authorization ao `IdentityIngress.dispatch`; resposta do adapter é propagada quando existir. |
| `GET /health` | [main.py](../../../main.py#L219) | Health básico e timestamp local; não executa checagem de dependências externas. |
| `GET /api/status` | [main.py](../../../main.py#L231) | Status declarativo, formulários e indicadores simples de configuração; não prova conectividade. |

Execução direta usa porta 3000. README indica que a URL pública do Bot Framework deve terminar em `/api/messages` e ser HTTPS; proxy, registro e certificado pertencem à implantação.

## Bot Framework e mensagem

`identity/ingress.py` compõe `BotFrameworkAdapter` e `SimpleCredentialProvider`. O adapter processa uma atividade uma vez. Durante callback, o serviço pode resolver identidade autenticada; a capacidade não deve ser guardada nem usada fora desse callback. A captura de referência proativa é uma operação de saída, não outra autenticação de entrada.

Cartões são `HeroCard` serializados pelo `CardFactory` SDK; ações usam `messageBack` com valores JSON. Texto visível fica no cartão, sem duplicação deliberada em `Activity.text`. Botões numéricos são entrada conveniente, nunca autorização.

## Conversas e anexos

Menu de consulta e notificações exige Teams pessoal explícito. Conversa de canal/grupo não se torna identidade pessoal por nome. Anexos de formulário podem usar URL de download e OAuth do bot conforme tipo recebido; consulte [[obsidian/03 - Fluxos/Navegação e abertura|Abertura]].

## Falhas visíveis

O fluxo sensível tenta retornar mensagem genérica e não registrar rascunho/conteúdo bruto. `/health` ou resposta HTTP 200 do handler não deve ser interpretado como confirmação de que o Teams autenticou ou de que uma operação GLPI concluiu.
