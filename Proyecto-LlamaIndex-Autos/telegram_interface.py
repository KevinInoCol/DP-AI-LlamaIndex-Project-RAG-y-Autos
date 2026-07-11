"""
Interfaz síncrona para el bot de Telegram.

Usamos un event loop dedicado en un hilo separado para evitar
el error "Future attached to a different loop" que ocurre cuando
asyncio.run() crea un loop nuevo en cada llamada, pero asyncpg
mantiene conexiones ligadas al loop original.
"""

import asyncio
import threading

from agent import create_agent
from chat_history import get_memory_for_user

_agent = None
_chat_store = None
_token_limit = None
_loop = None
_loop_thread = None


def _start_event_loop(loop):
    """Ejecuta el event loop en un hilo dedicado."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def initialize(bot_name: str) -> None:
    """
    Inicializa el agente y el event loop persistente.
    Llamar una sola vez al iniciar el bot.
    """
    global _agent, _chat_store, _token_limit, _loop, _loop_thread

    _loop = asyncio.new_event_loop()
    _loop_thread = threading.Thread(target=_start_event_loop, args=(_loop,), daemon=True)
    _loop_thread.start()

    _agent, _chat_store, _token_limit = create_agent(bot_name)


async def _async_chat(message: str, chat_id: str) -> str:
    """Envía un mensaje al agente (async)."""
    if _agent is None:
        raise RuntimeError("El agente no ha sido inicializado. Llama a initialize() primero.")

    memory = get_memory_for_user(_chat_store, chat_id, _token_limit)
    response = await _agent.run(message, memory=memory)
    return str(response)


def chat(message: str, chat_id: str) -> str:
    """
    Interfaz síncrona para el bot de Telegram.
    Envía la coroutine al event loop dedicado y espera el resultado.

    Args:
        message: Mensaje del usuario
        chat_id: ID del chat de Telegram (se usa como key de memoria)

    Returns:
        str: Respuesta del agente
    """
    future = asyncio.run_coroutine_threadsafe(_async_chat(message, chat_id), _loop)
    return future.result()
