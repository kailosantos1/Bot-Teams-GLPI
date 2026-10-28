# Funcionamento

## Menu e navegação
- Menu pessoal: `1 — Abrir chamado`, `2 — Consultar chamados`, `3 — Sair`.
- Saída apenas encerra a navegação; não altera vínculo, identidade, banco ou notificações.
- Durante formulário ativo, `sair` pede confirmação vinculada ao token atual.
- Em canais/grupos, não envia cartões pessoais; caminho textual preservado.
- Formulário em andamento tem prioridade; botões do menu pedem continuar ou cancelar.

## Abertura pelo Teams via Formcreator
- Formulários: FlexSmart (ID 5), Manutenção (ID 1) e Cadastro de Novo Colaborador (ID 2).
- Perguntas condicionais, múltipla escolha, anexos e autorização de cadastro preservados.
- Anexos são enviados como documentos após criação do ticket, não pelo campo nativo do Formcreator.
- Confirmação final usa o número real do Ticket vinculado ao FormAnswer, não o ID de FormAnswer.

## Consulta dos próprios chamados
- Somente conversas pessoais do Teams.
- Identidade resolvida a cada operação pelo mesmo fluxo autenticado.
- Filtros GLPI: requerente individual, status 1-4, não excluído.
- Técnicos/observadores/grupos não concedem acesso.
- 5 itens por página; ordenação `date_mod`/ID decrescente.

## Descrição, histórico público e respostas
- Detalhes mostram solicitação inicial autorizada.
- Histórico público: apenas `ITILFollowup` com `is_private=0` inteiro/string `"0"`.
- Resposta textual é capturada sem envio imediato e enviada diretamente após texto válido.
- Limite de 2000 caracteres; anexos são recusados na resposta.
- Autoria apresentada usa `followup_id` confirmado em `reply_operations`.

## Notificações de respostas de técnicos
- Opt-in, desabilitadas por padrão.
- Apenas autores membros de grupos configurados.
- Baseline por destinatário/geração/ticket; primeiro snapshot não envia histórico.
- Fila persistente com estados e entrega incerta sem repetição automática.
- Requisitos: conversa pessoal válida, vínculo confirmado, resolução segura prévia.

## Referências
- [[08 - Formulários GLPI]], [[03 - Execução e notificações]], [[09 - Validação manual]]
