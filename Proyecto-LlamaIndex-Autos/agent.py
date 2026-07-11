"""
Módulo Agente IA (FunctionAgent).

Configuración modular:
- LLM + parámetros de memoria: model_config/model.yaml
- System prompt:                prompt/system_prompt.yaml
- Histórico de conversación:    chat_history/  (Postgres / Supabase)
- Credenciales DB y BOT_NAME:   .env
"""

from pathlib import Path

import yaml
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

from RAG.rag import load_or_create_index
from chat_history import build_chat_store
from tools.retrieval import get_retrieval_tool

# ──────────────────────────────────────────────
# 0. CARGA DE CONFIGURACIÓN MODULAR
# ──────────────────────────────────────────────

ROOT = Path(__file__).parent
LLM_CONFIG_PATH = ROOT / "model_config" / "model.yaml"
PROMPT_CONFIG_PATH = ROOT / "prompt" / "system_prompt.yaml"


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _render_system_prompt(bot_name: str) -> str:
    """Carga el system_prompt.yaml y reemplaza los placeholders {variable}."""
    prompt_cfg = _load_yaml(PROMPT_CONFIG_PATH)
    return prompt_cfg["system_prompt"].replace("{bot_name}", bot_name)


# ──────────────────────────────────────────────
# 1. CONFIGURACIÓN DEL AGENTE
# ──────────────────────────────────────────────

def create_agent(bot_name: str):
    """
    Crea y configura el agente FunctionAgent con sus herramientas y memoria.

    Returns:
        tuple: (agent, chat_store, token_limit)
        - agent: FunctionAgent listo para correr
        - chat_store: PostgresChatStore compartido entre usuarios
        - token_limit: tope de tokens del historial, leído del YAML
    """
    config = _load_yaml(LLM_CONFIG_PATH)
    llm_cfg = config["llm"]
    mem_cfg = config["memory"]

    llm = OpenAI(
        model=llm_cfg["model"],
        temperature=llm_cfg.get("temperature", 0),
    )

    index = load_or_create_index()

    agent = FunctionAgent(
        tools=[get_retrieval_tool(index, llm)],
        llm=llm,
        system_prompt=_render_system_prompt(bot_name),
    )

    chat_store = build_chat_store(table_name=mem_cfg["table_name"])

    return agent, chat_store, mem_cfg["token_limit"]
