"""
Backend de histórico de conversación en memoria (RAM del proceso).

Apto para:
- Proyectos sin multi-usuario (un solo cliente por proceso, como Streamlit).
- Demos, aulas y prototipos.

NO apto para:
- Producción multi-usuario (cada pestaña/proceso pierde su historial al refrescar).
- Bots concurrentes (Telegram, WhatsApp). Para ese caso usar postgres_store o redis_store
  manteniendo la misma carpeta conversation_history/ y solo cambiando el archivo del backend.
"""

from llama_index.core.memory import ChatMemoryBuffer


def build_chat_memory(token_limit: int = 3000) -> ChatMemoryBuffer:
    """
    Crea un ChatMemoryBuffer en memoria.
    Cada conversación debe instanciar UN buffer y reusarlo en todos los turns.
    """
    return ChatMemoryBuffer.from_defaults(token_limit=token_limit)
