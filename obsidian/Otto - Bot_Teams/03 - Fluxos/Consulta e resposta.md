# Consulta, histórico e resposta

[[obsidian/03 - Fluxos/Indice|← Fluxos]] · [[obsidian/Inicio|Início]]

## Lista e detalhes

1. Entrada disponível em conversa pessoal; a identidade é resolvida no callback autenticado.
2. `TicketQuery.list` consulta pesquisa GLPI e revalida cada resultado pela relação de requerente. Só status mapeados a Novo, Em atendimento e Pendente são mantidos; excluídos e estados fora desse conjunto não aparecem.
3. Estado efêmero guarda binding de identidade/conversa, página atual, IDs visíveis, versão e expiração. Seleção não usa ID fornecido pelo botão: índice mapeia para a página guardada e o ticket é revalidado.
4. Detalhes mostram título, status e descrição inicial sanitizada; para estruturas Formcreator reconhecidas, tentam extrair somente o campo de descrição. Se não for seguro, a UI indica indisponibilidade da descrição.

A lista mostra cinco itens por página. Controles: `7` anteriores, `9` próximos, `8` atualizar e `0` menu. Detalhes oferecem `1` conversa, `2` responder, `3` lista e `0` menu; conteúdo longo é paginado sem alterar o dado usado na ordenação. Histórico é recente-primeiro, com `7`/`9` para navegar por mensagens ou partes.

## Conversa pública

Histórico carrega apenas `ITILFollowup` do Ticket exato com `is_private` representado como inteiro `0` ou string `"0"`. Pai/tipo divergente ou coleção/paginação inválida falha sem exibir conteúdo parcial. Não consulta anexos, logs ou timeline bruta. Trechos são paginados; HTML é convertido para texto passivo e endereços são ocultados.

## Resposta de texto

Em “Responder”, texto válido é enviado diretamente, sem prévia; limite de 2.000 caracteres. Anexos reais são recusados sem download ou envio. O backend valida novamente a autorização do Ticket, grava operação persistente e só então cruza o fence `submitting` antes do POST público ao GLPI. Não envia o ID de usuário como autor: autoria nativa é a conta de integração GLPI.

- Confirmação de sucesso exige recibo de followup válido.
- Falha conhecida antes do POST pode preservar a operação para nova tentativa.
- Timeout/falha após possível envio torna o resultado incerto; a UI avisa e não repete cegamente.
- Uma atividade reentregue com o mesmo ID, binding e ticket reaproveita operação existente.

## Estados e tempos

Lista/tela de navegação tem validade curta em memória. Rascunho do SQLite tem TTL de 15 minutos; metadados de resposta são limpos após 7 dias por rotina/comando. Reinício perde o estado de UI, mas o estado de envio persiste; a tentativa pode ainda ficar incerta.

Arquivos: [bot/ticket_consult.py](../../../bot/ticket_consult.py#L54), [bot/ticket_detail.py](../../../bot/ticket_detail.py#L38), [TicketConversation](../../../services/ticket_conversation.py#L18), [ReplyStore](../../../identity/replies.py#L19).
