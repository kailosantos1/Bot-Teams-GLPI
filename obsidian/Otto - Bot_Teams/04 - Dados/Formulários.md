# Formulários GLPI

[[obsidian/04 - Dados/Indice|← Dados]] · [[obsidian/Inicio|Início]] · [[obsidian/03 - Fluxos/Navegação e abertura|Fluxo]]

`config/forms.yaml` fornece chave, ID Formcreator, nome, palavras-chave e campos conversacionais. A ordem no YAML é a ordem seguida pelo processador, não confirmação da ordem visual no GLPI. Os valores do YAML precisam ser conferidos contra o ambiente GLPI que recebe o formulário.

## FlexSmart — Formcreator ID 5

| Ordem | ID | Campo | Condição/opções |
|---:|---:|---|---|
| 1 | 106 | Tipo de atendimento | Liberação / Outro |
| 2 | 107 | Qual liberação | Só se tipo=Liberação; Telas / Outros |
| 3 | 108 | Qual tela | Só se qual liberação=Telas |
| 4 | 111 | Liberação no sistema | Só se qual liberação=Outros |
| 5 | 109 | Usuário da liberação | Só se tipo=Liberação; usuário atual / outro usuário |
| 6 | 110 | Nome do usuário | Só se usuário escolhido=Outro Usuario |
| 7 | 42 | Descrição do problema | Texto obrigatório |
| 8 | 73 | Canal de contato | Microsoft Teams / WhatsApp / OPA |
| 9 | 74 | WhatsApp | Só se canal=WhatsApp |
| 10 | 75 | E-mail Teams | Só se canal=Microsoft Teams |
| 11 | 112 | Urgência | Baixa / Média / Alta |

## Manutenção — Formcreator ID 1

| Ordem | ID | Campo | Condição/opções |
|---:|---:|---|---|
| 1 | 2 | Tipo de solicitação | Manutenção de Equipamentos / Manutenção de Acessos |
| 2 | 26 | Equipamento | Computador/Hardware; Periféricos; Smartphone/Mobile; Sistemas/Softwares; Servidores/Pastas; Internet/Páginas da Web; Outros |
| 3 | 3 | Descrição do problema | Texto obrigatório |
| 4 | 6 | Local | Filial / Matriz |
| 5 | 7 | Filial | Só se local=Filial; Maravilha, Lages, Videira, Concordia, Catanduvas |
| 6 | 70 | Canal de contato | WhatsApp / Microsoft Teams / OPA |
| 7 | 71 | WhatsApp | Só se canal=WhatsApp |
| 8 | 72 | E-mail Teams | Só se canal=Microsoft Teams |
| 9 | 4 | Urgência | Baixa / Média / Alta |

O YAML preserva um NBSP no valor canônico `Internet/Páginas da Web`; validação textual normaliza espaços para comparar entradas. Urgência é solicitada pelo bot mesmo que o Formcreator possa ter padrão; o serviço converte rótulos textuais conforme mapa de urgência do código.

As opções completas do campo 26 são `Computador/Hardware`, `Periféricos (Webcam/Impressora)`, `Smartphone/Mobile`, `Sistemas/Softwares`, `Servidores/Pastas de Arquivos`, `Internet/Páginas da Web` e `Outros`.

## Cadastro de Novo Colaborador — Formcreator ID 2

| Ordem | ID | Campo | Condição/opções |
|---:|---:|---|---|
| 1 | 8 | Nome completo | Texto |
| 2 | 9 | Unidade | Matriz / Filial |
| 3 | 10 | Filial | Só se unidade=Filial; cinco filiais acima |
| 4 | 11 | Setor | 13 opções no YAML, incluindo Comercial, Compras, Financeiro, RH etc. |
| 5 | 12 | Modelo/perfil | Texto |
| 6 | 13 | VPN | Sim / Não |
| 7 | 14 | Licença M365 | Standard / Basic |
| 8 | 15 | FLEX | Sim / Não |
| 9 | 16 | Já possui equipamento | Sim / Não |
| 10 | 17 | Tipo existente | Só se possui=Sim; Desktop / Notebook |
| 11 | 102 | Ramal corporativo | Sim / Não |
| 12 | 18 | Equipamento necessário | Múltipla escolha: Desktop, Notebook, Celular, Fone |
| 13 | 19 | Instalar programas | Sim / Não |
| 14 | 20 | Quais programas | Só se resposta=Sim |
| 15 | 22 | Assinatura de e-mail | Sim / Não |
| 16 | 24 | Observações | Opcional |
| 17 | 82 | Canal | WhatsApp / Microsoft Teams / OPA |
| 18 | 83 | WhatsApp | Só se canal=WhatsApp |
| 19 | 84 | E-mail Teams | Só se canal=Microsoft Teams |

O setor (campo 11) contém `Comercial Peças`, `Comercial Implementos`, `Compras`, `Financeiro`, `Fiscal`, `Logística`, `Garantia`, `Almoxarifado`, `Qualidade`, `Recepção`, `Marketing`, `Desenvolvimento e Implantações` e `RH`. O campo 18 permite Desktop, Notebook, Celular e Fone de ouvido com microfone; pode haver mais de uma seleção.

## Limites e conferência

- O campo nativo de arquivo Formcreator não é usado. Anexos do Teams são enviados depois como `Document` e vinculados a Ticket.
- IDs e opções acima são lidos do YAML, não consultados agora no GLPI. As condições correspondem ao conteúdo atual de `config/forms.yaml`.
- A descrição no detalhe é extraída do HTML Formcreator reconhecido (tabelas estruturadas ou divs com rótulo em negrito); fonte sem estrutura segura pode resultar em mensagem indisponível.

Arquivo: [config/forms.yaml](../../../config/forms.yaml) · [services/ticket_content.py](../../../services/ticket_content.py#L173)
