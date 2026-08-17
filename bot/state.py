from botbuilder.core import MemoryStorage, ConversationState, UserState
 
# Armazenamento temporário em memória.
# ATENÇÃO PRODUÇÃO: com MemoryStorage, o estado se perde a cada restart do processo
# e não é compartilhado entre múltiplas réplicas/workers. Se o bot for rodar com mais
# de um worker (ex: uvicorn --workers 2) ou precisar sobreviver a deploys, troque por
# um storage persistente e compartilhado, ex:
#   from botbuilder.azure import CosmosDbPartitionedStorage
#   memory_storage = CosmosDbPartitionedStorage(...)
memory_storage = MemoryStorage()
 
# Gerenciadores de estado para o Bot Framework
conversation_state = ConversationState(memory_storage)
user_state = UserState(memory_storage)
 
# Acessor de propriedade usado pelo DynamicFormProcessor para guardar a sessão do
# formulário em andamento (form_key, respostas, perguntas pendentes) por usuário.
# Como o UserState já é indexado pelo ID único do usuário/canal do Teams, isso evita
# colisão entre usuários com o mesmo nome de exibição.
dialog_state_accessor = conversation_state.create_property("DialogState")
user_profile_accessor = user_state.create_property("UserProfile")