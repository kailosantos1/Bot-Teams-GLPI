# Persistência e modelos

[[obsidian/04 - Dados/Indice|← Dados]] · [[obsidian/Inicio|Início]]

## Estado em memória

`bot/state.py` cria um `MemoryStorage` compartilhado por `ConversationState` e `UserState`.

| Propriedade | Uso | Sobrevive a reinício? |
|---|---|---|
| `DialogState` | Estado de conversa do Bot Framework | Não |
| `UserProfile` | Sessão do formulário, respostas e anexos pendentes em base64 | Não |
| `NavState` | Menu, tela, confirmação e versões de botões | Não |
| `TicketQueryState` | Página/seleção/detalhes e referência ao rascunho | Não |
| `NotificationState` | Aviso pendente/rascunho preservado para retomar | Não |

Uma chave de `UserState` não é o nome de exibição. Ainda assim, `MemoryStorage` é local ao processo, sem compartilhamento entre réplicas.

## SQLite

`IDENTITY_DB_PATH` aponta para o arquivo padrão `data/identity.sqlite3`. O caminho relativo é resolvido por `runtime_paths.ROOT`: raiz do projeto em fonte e diretório do executável quando congelado. `LinkStore.initialize()` aceita versões 0–4 e migra incrementalmente sob transação; banco inexistente não é criado pelas operações de resposta/notificação que exigem vínculo administrativo prévio.

### Tabelas

| Tabela | Chaves/conteúdo principal | Função |
|---|---|---|
| `links` | `(tenant_id, object_id)`, `glpi_user_id`, status e revisão/aprovação | Associação Teams–GLPI |
| `audit` | tenant/object, ação, IDs antigos/novos, operador e referência | Trilha de create/revoke/replace |
| `reply_operations` | binding, ticket, corpo temporário, estado, tentativa, `followup_id`, `activity_id` | Resposta direta e anti-replay por atividade |
| `notification_references` | destinatário, revisão, geração, app e ConversationReference | Destino de envio |
| `notification_watches` | geração/ticket e high-water mark | Evitar replay de histórico |
| `notification_events` | IDs de destinatário/ticket/followup e estado/lease de reserva | Fila sem corpo da mensagem GLPI |
| `notification_lease` | dono e expiração | Exclusividade lógica de ciclo |

Schema atual declarado no código: `PRAGMA user_version=4`. A versão implantada do banco não foi inspecionada.

## Regras de retenção e segurança

- Resposta: rascunho expira em 15 minutos; corpo é removido ao concluir/cancelar/expirar/ficar incerto. Metadados têm janela de 7 dias, com limpeza oportunista/comando.
- Notificações: eventos retidos por 7 dias desde transição; referências sem captura autenticada são desabilitadas após 30 dias; watches ativos persistem para não repetir histórico.
- Apagar linhas SQLite não garante remoção física de páginas, WAL, snapshots ou backups.
- Instância única com disco local persistente é pressuposto; NFS, discos efêmeros e múltiplas réplicas não são suportados por esta arquitetura documentada.

[[obsidian/02 - Modulos/Identidade|Identidade]] · [[obsidian/02 - Modulos/Notificações|Notificações]] · [[obsidian/07 - Operacao/Atualização e backup|Backup]]
