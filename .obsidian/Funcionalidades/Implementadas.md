# Funcionalidades Implementadas

## 1. Abertura de Chamados
- **Formulários dinâmicos**: Carregados de `config/forms.yaml` (FlexSmart ID 5, Manutenção ID 1, Cadastro de Novo Colaborador ID 2)
- **Perguntas condicionais**: Suporte a `depends_on` com dependências entre campos
- **Múltipla escolha**: Suporte com seleção/desmarcação
- **Paginação de opções**: Para listas extensas (5 opções por página)
- **Anexos**: Coleta de anexos/imagens do Teams, enviados como documentos ao ticket
- **Integração Formcreator**: Criação via `GLPIService.create_form_answer()`
- **Autorização legada**: Validação por domínio/grupos para cadastro de colaborador

## 2. Menu e Navegação
- **Menu inicial**: 1 - Abrir chamado, 2 - Consultar chamados, 3 - Sair
- **Navegação com botões**: HeroCards com `messageBack`
- **Suporte numérico**: Aceita tanto cliques em botões quanto digitação numérica
- **Confirmação de cancelamento**: Em formulários ativos
- **Preservação de estado**: Em memória (MemoryStorage)

## 3. Consulta de Chamados Próprios
- **Identidade obrigatória**: Requer vínculo Teams-GLPI via `identity/service.py`
- **Filtro por requerente**: Apenas chamados onde o usuário é requerente (type=1 em Ticket_User)
- **Status filtrados**: Novo (1), Em atendimento (2/3), Pendente (4). Exclui Solucionado (5) e Fechado (6)
- **Paginação**: 5 itens por página
- **Ordenação**: Por data_mod/ID decrescente
- **Sem contagem total**: Para evitar consultas pesadas

## 4. Detalhes e Histórico Público
- **Solicitação inicial**: Exibe conteúdo da descrição do ticket
- **Acompanhamentos públicos**: Apenas ITILFollowup com `is_private = 0`
- **Paginação de histórico**: Um registro/trecho por página, mais recentes primeiro
- **Sanitização**: Remove scripts, estilos, converte HTML para texto limpo
- **Ocultação de cabeçalho do bot**: Quando comprovadamente enviado via resposta do bot
- **Sem anexos privados/notas**: Nunca exibe conteúdo privado

## 5. Resposta Textual Confirmada
- **Captura direta**: Sem prévia obrigatória (fluxo simplificado)
- **Envio único atômico**: Controle via `reply_operations` com estados
- **Deduplicação por atividade**: Evita envios duplicados
- **Autorização revalidada**: Antes de cada envio
- **Resultado uncertain**: Se falha após envio possível, não reenvia cegamente
- **TTL**: 15 minutos para resposta pendente
- **Cabeçalho padronizado**: "Origem: Microsoft Teams — Nome do usuário"

## 6. Sistema de Identidade
- **Vínculo manual**: Via CLI `tools/identity_links`
- **Vínculo automático opt-in**: Por e-mail Microsoft autenticado (desabilitado por padrão)
- **Validação Teams-GLPI**: Verifica membro, tenant permitido
- **Revalidação a cada operação**: Em consultas/respostas
- **Auditoria completa**: Todas as operações registradas
- **Migrações transacionais**: Preservam dados existentes

## 7. Notificações Públicas (Opcional)
- **Desabilitado por padrão**: Requer configuração explícita
- **Por grupos GLPI**: Autores devem pertencer a grupos configurados
- **Apenas novos followups públicos**: Não envia histórico
- **Linha de base por ticket**: Evita notificações duplicadas
- **Clique reautorizado**: Botão leva para consulta com revalidação
- **Worker dedicado**: Processo separado do Uvicorn
- **Política rigorosa**: Exclui integrações, destinatário, privados

## 8. Tratamento de Anexos
- **Download do Teams**: Suporta arquivos e imagens coladas
- **Armazenamento em base64**: Temporário em memória durante formulário
- **Envio como documentos**: Vinculados ao ticket após criação
- **Classificação**: Diferencia arquivo real vs HTML técnico
- **Recusa na resposta**: Não aceita anexos em resposta a followups
