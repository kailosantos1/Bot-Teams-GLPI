# Homologação e dúvidas pendentes

[[obsidian/08 - Pendencias/Indice|← Pendências]] · [[obsidian/Inicio|Início]]

Esta nota incorpora o checklist da documentação anterior, atualizado com o código atual. Itens abaixo não foram homologados nesta tarefa.

## Microsoft Teams e Bot Framework

- Executar `tools.inspect_identity_sdk` no interpretador efetivo de produção e confirmar todas as dependências/assinaturas.
- Validar credenciais, JWT, app ID/audience, tenant permitido, membro retornado por TeamsInfo e atividade de canal pessoal no tenant real.
- Conferir cartões e ações `messageBack` em Teams desktop/web/móvel, incluindo textos longos, anexos e paginação.
- Validar conversation reference, instalação/contato com o bot, proatividade e comportamento de erro/transporte.

## GLPI e Formcreator

- Confirmar versão implantada, REST v1, permissões, entidades e formato real de paginação, `Content-Range` e coleção vazia.
- Homologar opções de busca, códigos de status, relacionamento `Ticket_User`, visibilidade por requerente e exclusão/fechamento.
- Conferir os três formulários e IDs/opções/dependências do `config/forms.yaml` no ambiente real; confirmar ordem visual e urgência.
- Validar `PluginFormcreatorFormanswer` → `Item_Ticket`, requerente, remoção de atores, upload/vínculo de documentos, nota Teams e efeitos parciais.
- Validar HTML real de descrições Formcreator e privacidade/renderização de acompanhamentos.
- Confirmar autoria da resposta pública via conta do token e efeito de `_no_reopen=true`/plugins.
- Confirmar associação direta de autores a grupos e lista completa de contas de integração.

## Identidade, segurança e dados

- Rever vínculo manual/auto-link com administrador responsável; comprovar exclusividade e governança dos e-mails GLPI se auto-link for ativado.
- Testar isolamento entre usuários, tentativa de ID adulterado, usuário GLPI desativado, revogação/alteração de vínculo e tenant incorreto.
- Conferir permissões de diretório/banco/backups, schema/migração incremental e execução em reinício real.
- Demonstrar limpeza de conteúdo expirado e retenção de WAL/backups sem afirmar exclusão física.

## Notificações e operação

- Confirmar IDs reais de grupos de suporte e de todas as contas de integração; não os obter por nome no código.
- Validar baseline com o volume de eventos real, crescimento/ordem de IDs, respostas tardias, fila, 429, lease, reinício e envio incerto.
- Confirmar execução de manager e CLI sob único processo; shutdown e locks entre processos.
- Em Windows, compilar/iniciar o onedir, imports/certificados, caminhos externos, NSSM/conta efetiva, disputa `msvcrt` e parada normal/forçada.
- Contrastar `otto.spec` do checkout com o artefato e serviço instalado; este repositório não prova deployment.

## Limitações de evidência nesta tarefa

- Foi feita leitura estática; não foram executados testes, aplicação, build, PowerShell ou scripts.
- Não houve chamada real a Teams/GLPI, modificação de banco/vínculos/configuração, envio ou migração.
- A referência de API GLPI 10.0.18 vem do código/documentação anterior do projeto; instalação vigente não foi identificada.
- Existem chamadas síncronas Requests no caminho de aplicação e operações não transacionais após abertura; não se presume prazo absoluto nem recuperação automática.
- MemoryStorage perde estado de UI em reinícios e não atende réplicas; SQLite local também não é solução distribuída.

[[obsidian/06 - Desenvolvimento/Testes|Cobertura de testes]] · [[obsidian/07 - Operacao/Diagnóstico|Diagnóstico]]
