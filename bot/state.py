# bot/state.py
"""
Gerenciamento de estado do Bot Framework e sessões em memória.
Separa explicitamente o UserProfile (sessão de formulários) do NavState (estado de navegação do menu).
"""

try:
    from botbuilder.core import MemoryStorage, ConversationState, UserState

    memory_storage = MemoryStorage()
    conversation_state = ConversationState(memory_storage)
    user_state = UserState(memory_storage)

    dialog_state_accessor = conversation_state.create_property("DialogState")
    user_profile_accessor = user_state.create_property("UserProfile")
    nav_state_accessor = user_state.create_property("NavState")

except ImportError:
    # Fallback em memória para ambientes locais ou testes onde o SDK não está instalado
    class _FallbackPropertyAccessor:
        def __init__(self, name: str, store: dict):
            self.name = name
            self.store = store

        def _get_key(self, turn_context) -> str:
            activity = getattr(turn_context, "activity", None)
            from_prop = getattr(activity, "from_property", None) if activity else None
            user_id = getattr(from_prop, "id", None) if from_prop else None
            if not user_id:
                user_id = getattr(turn_context, "user_name", "default_user")
            return f"{user_id}:{self.name}"

        async def get(self, turn_context, default_value_or_factory=None):
            key = self._get_key(turn_context)
            if key not in self.store:
                if callable(default_value_or_factory):
                    val = default_value_or_factory()
                else:
                    val = default_value_or_factory
                return val
            return self.store[key]

        async def set(self, turn_context, value):
            key = self._get_key(turn_context)
            self.store[key] = value

        async def delete(self, turn_context):
            key = self._get_key(turn_context)
            self.store.pop(key, None)

    class _FallbackState:
        def __init__(self):
            self._store = {}

        def create_property(self, name: str):
            return _FallbackPropertyAccessor(name, self._store)

        async def save_changes(self, turn_context, force: bool = False):
            pass

    memory_storage = None
    conversation_state = _FallbackState()
    user_state = _FallbackState()

    dialog_state_accessor = conversation_state.create_property("DialogState")
    user_profile_accessor = user_state.create_property("UserProfile")
    nav_state_accessor = user_state.create_property("NavState")


def reset_in_memory_state():
    """Limpa o armazenamento em memória (útil para testes unitários)."""
    if hasattr(user_state, "_store"):
        user_state._store.clear()
    if hasattr(conversation_state, "_store"):
        conversation_state._store.clear()
    if hasattr(memory_storage, "memory") and isinstance(memory_storage.memory, dict):
        memory_storage.memory.clear()
