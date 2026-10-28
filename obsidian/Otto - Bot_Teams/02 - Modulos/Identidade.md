# Módulo de identidade

[[obsidian/02 - Modulos/Indice|← Módulos]] · [[obsidian/03 - Fluxos/Identidade e autorização|Fluxo de identidade]]

## Componentes

- `identity/ingress.py`: compõe adapter e executa uma única passagem autenticada. Resolver só vive no callback e compartilha uma resolução por Activity.
- `identity/service.py`: valida Teams pessoal, tenant, remetente e membro consultado via `TeamsInfo.get_member`; retorna `IdentityResult`.
- `identity/glpi.py`: valida por ID exato que o usuário GLPI existe, está ativo e não excluído.
- `identity/email_lookup.py`: modo automático opcional, busca paginada e verifica igualdade de e-mail exata em endereços GLPI.
- `identity/store.py`: links, auditoria transacional, restrição de um usuário GLPI por tenant e operações SQLite.
- `identity/replies.py`: persistência e deduplicação de operações de resposta.
- `identity/notifications.py`: referências pessoais, marcos por ticket, fila e lease.
- `identity/diagnostics.py`: allowlist de códigos de falha; não registra dados pessoais ou exceções brutas.

## Modos de associação

O modo manual é o padrão. A CLI de identidade grava um vínculo aprovado administrativamente entre tenant/object ID do Entra e ID do GLPI. `IDENTITY_AUTO_LINK_ENABLED=true` permite associação apenas quando o vínculo está ausente e após validação de e-mail retornado pelo membro autenticado do Teams e correspondência inequívoca com um usuário GLPI ativo. UPN, nome, e-mail digitado e IDs de payload não são prova.

Vínculo existente é revalidado; vínculo revogado não é recriado automaticamente. Para detalhes e limites, ver [[obsidian/03 - Fluxos/Identidade e autorização|fluxo de identidade]].

## Fronteira de segurança

Consulta, detalhe, resposta e ações de notificação resolvem identidade de novo. O GLPI revalida o usuário e o ticket; a seleção guardada em estado é apenas navegação, não autorização. A abertura legada ainda usa o caminho de domínio/cadastro baseado em dados GLPI pelo nome; o mecanismo de identidade não torna essa autorização antiga equivalente.

[[obsidian/04 - Dados/Persistência e modelos|Schema SQLite]] · [[obsidian/06 - Desenvolvimento/Configuração|Variáveis de configuração]] · [[obsidian/08 - Pendencias/Homologação|Homologação pendente]]
