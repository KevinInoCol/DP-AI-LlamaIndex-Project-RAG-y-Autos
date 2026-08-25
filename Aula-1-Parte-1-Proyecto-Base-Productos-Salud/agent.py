import asyncio
from pathlib import Path

import yaml
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.openai import OpenAI

from conversation_history import build_chat_memory as _build_chat_memory_buffer
from tools.retrieval import get_retrieval_tool

ROOT = Path(__file__).parent
LLM_CONFIG_PATH = ROOT / "model_config" / "model.yaml"
PROMPT_CONFIG_PATH = ROOT / "prompt" / "system_prompt.yaml"


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_chat_memory() -> ChatMemoryBuffer:
    """Crea un ChatMemoryBuffer leyendo token_limit desde model_config/model.yaml.
    Cada conversación debería instanciar UNO y reusarlo en todos los turns."""
    mem_cfg = _load_yaml(LLM_CONFIG_PATH).get("memory", {})
    return _build_chat_memory_buffer(token_limit=mem_cfg.get("token_limit", 3000))


def ask(index, question: str, memory: ChatMemoryBuffer | None = None) -> str:
    llm_cfg = _load_yaml(LLM_CONFIG_PATH)["llm"]
    prompt_cfg = _load_yaml(PROMPT_CONFIG_PATH)

    llm = OpenAI(
        model=llm_cfg["model"],
        temperature=llm_cfg.get("temperature", 0),
    )
    agent = FunctionAgent(
        tools=[get_retrieval_tool(index, llm)],
        llm=llm,
        system_prompt=prompt_cfg["system_prompt"],
    )

    async def _run() -> str:
        return str(await agent.run(user_msg=question.strip(), memory=memory))

    return asyncio.run(_run())
