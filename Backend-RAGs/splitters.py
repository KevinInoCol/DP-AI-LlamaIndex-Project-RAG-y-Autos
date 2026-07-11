"""
Catálogo de Text Splitters / Node Parsers de LlamaIndex.

Cada técnica se describe con:
  - key           : identificador único (usado por el frontend)
  - name          : nombre legible
  - group         : "no_api" (funciona sin conexión) | "api" (requiere OPENAI_API_KEY)
  - description   : explicación corta
  - params        : parámetros configurables desde la UI (con valores por defecto)
  - factory(params, embed_model) -> NodeParser de LlamaIndex

Para dividir un texto se convierte en un Document y se llama a
`node_parser.get_nodes_from_documents([doc])`.
"""

from __future__ import annotations

import os
from typing import Any, Callable

import tiktoken
from llama_index.core import Document
from llama_index.core.node_parser import (
    CodeSplitter,
    SemanticSplitterNodeParser,
    SentenceSplitter,
    SentenceWindowNodeParser,
    TokenTextSplitter,
)

# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
_ENCODER = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Cuenta tokens aproximados (codificación cl100k_base, la de OpenAI)."""
    return len(_ENCODER.encode(text or ""))


def _get_code_parser(language: str):
    """Construye un parser tree-sitter para CodeSplitter.

    La versión de CodeSplitter de LlamaIndex intenta importar el paquete antiguo
    `tree_sitter_languages` (que no compila en Python 3.14). Aquí construimos el
    parser con `tree-sitter-language-pack` y lo pasamos directamente.
    """
    try:
        from tree_sitter_language_pack import get_parser

        return get_parser(language)
    except ImportError as exc:
        raise RuntimeError(
            "Falta 'tree-sitter-language-pack'. Instálalo con: "
            "pip install tree-sitter-language-pack"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Lenguaje no soportado por CodeSplitter: {language} ({exc})") from exc


def _get_embed_model():
    """Instancia el modelo de embeddings de OpenAI (para splitters semánticos)."""
    from llama_index.embeddings.openai import OpenAIEmbedding

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta OPENAI_API_KEY. Copia .env.example a .env y coloca tu clave "
            "para usar los splitters semánticos."
        )
    model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    return OpenAIEmbedding(model=model, api_key=api_key)


# --------------------------------------------------------------------------- #
# Definición de cada splitter
# --------------------------------------------------------------------------- #
# Cada entrada del catálogo. `params` describe los controles de la UI:
#   {name, label, type: "int"|"float"|"select", default, min, max, step, options}

SPLITTERS: dict[str, dict[str, Any]] = {
    # ---------------------- SIN API KEY --------------------------------- #
    "sentence": {
        "name": "SentenceSplitter",
        "group": "no_api",
        "description": (
            "Divide por tamaño intentando NO romper oraciones. Es el splitter "
            "por defecto y el más usado en RAG."
        ),
        "params": [
            {"name": "chunk_size", "label": "Tamaño de chunk (tokens)", "type": "int", "default": 256, "min": 32, "max": 2048, "step": 32},
            {"name": "chunk_overlap", "label": "Solapamiento (tokens)", "type": "int", "default": 20, "min": 0, "max": 512, "step": 8},
        ],
        "factory": lambda p, _: SentenceSplitter(
            chunk_size=int(p.get("chunk_size", 256)),
            chunk_overlap=int(p.get("chunk_overlap", 20)),
        ),
    },
    "token": {
        "name": "TokenTextSplitter",
        "group": "no_api",
        "description": (
            "Divide por un número fijo de tokens sin preocuparse por las "
            "fronteras de oración. Rápido y predecible."
        ),
        "params": [
            {"name": "chunk_size", "label": "Tamaño de chunk (tokens)", "type": "int", "default": 256, "min": 32, "max": 2048, "step": 32},
            {"name": "chunk_overlap", "label": "Solapamiento (tokens)", "type": "int", "default": 20, "min": 0, "max": 512, "step": 8},
        ],
        "factory": lambda p, _: TokenTextSplitter(
            chunk_size=int(p.get("chunk_size", 256)),
            chunk_overlap=int(p.get("chunk_overlap", 20)),
        ),
    },
    "sentence_window": {
        "name": "SentenceWindowNodeParser",
        "group": "no_api",
        "description": (
            "Crea un nodo por cada oración y guarda una 'ventana' de N oraciones "
            "alrededor como contexto (en metadata: window)."
        ),
        "params": [
            {"name": "window_size", "label": "Tamaño de ventana (oraciones)", "type": "int", "default": 3, "min": 1, "max": 10, "step": 1},
        ],
        "factory": lambda p, _: SentenceWindowNodeParser.from_defaults(
            window_size=int(p.get("window_size", 3)),
            window_metadata_key="window",
            original_text_metadata_key="original_sentence",
        ),
    },
    "code": {
        "name": "CodeSplitter",
        "group": "no_api",
        "description": (
            "Divide código fuente respetando su sintaxis (usa el AST del "
            "lenguaje). Ideal para indexar repositorios."
        ),
        "params": [
            {"name": "language", "label": "Lenguaje", "type": "select", "default": "python",
             "options": ["python", "javascript", "typescript", "java", "go", "cpp", "html"]},
            {"name": "chunk_lines", "label": "Líneas por chunk", "type": "int", "default": 40, "min": 5, "max": 200, "step": 5},
            {"name": "chunk_lines_overlap", "label": "Solapamiento (líneas)", "type": "int", "default": 15, "min": 0, "max": 100, "step": 5},
            {"name": "max_chars", "label": "Máx. caracteres", "type": "int", "default": 1500, "min": 200, "max": 8000, "step": 100},
        ],
        "factory": lambda p, _: CodeSplitter(
            language=str(p.get("language", "python")),
            chunk_lines=int(p.get("chunk_lines", 40)),
            chunk_lines_overlap=int(p.get("chunk_lines_overlap", 15)),
            max_chars=int(p.get("max_chars", 1500)),
            parser=_get_code_parser(str(p.get("language", "python"))),
        ),
    },
    # ---------------------- CON API KEY (OpenAI) ------------------------ #
    "semantic": {
        "name": "SemanticSplitterNodeParser",
        "group": "api",
        "description": (
            "Divide por SIMILITUD SEMÁNTICA: usa embeddings para detectar dónde "
            "cambia el tema y corta ahí. Los chunks son de tamaño adaptativo. "
            "Requiere OPENAI_API_KEY."
        ),
        "params": [
            {"name": "buffer_size", "label": "Buffer (oraciones)", "type": "int", "default": 1, "min": 1, "max": 5, "step": 1},
            {"name": "breakpoint_percentile_threshold", "label": "Umbral de corte (percentil)", "type": "int", "default": 95, "min": 50, "max": 99, "step": 1},
        ],
        "factory": lambda p, embed: SemanticSplitterNodeParser(
            buffer_size=int(p.get("buffer_size", 1)),
            breakpoint_percentile_threshold=int(p.get("breakpoint_percentile_threshold", 95)),
            embed_model=embed,
        ),
    },
}


def list_splitters() -> list[dict[str, Any]]:
    """Devuelve el catálogo (sin las funciones factory) para el frontend."""
    out = []
    for key, cfg in SPLITTERS.items():
        out.append(
            {
                "key": key,
                "name": cfg["name"],
                "group": cfg["group"],
                "description": cfg["description"],
                "params": cfg["params"],
                "requires_api_key": cfg["group"] == "api",
            }
        )
    return out


def split_text(key: str, text: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Aplica el splitter indicado y devuelve la lista de chunks resultante."""
    if key not in SPLITTERS:
        raise KeyError(f"Splitter desconocido: {key}")
    if not text or not text.strip():
        return []

    cfg = SPLITTERS[key]
    params = params or {}

    embed_model = _get_embed_model() if cfg["group"] == "api" else None
    parser = cfg["factory"](params, embed_model)

    document = Document(text=text)
    nodes = parser.get_nodes_from_documents([document])

    chunks = []
    for i, node in enumerate(nodes):
        content = node.get_content()
        # Para SentenceWindow mostramos también la ventana de contexto.
        window = node.metadata.get("window") if node.metadata else None
        chunks.append(
            {
                "index": i,
                "text": content,
                "char_count": len(content),
                "token_count": count_tokens(content),
                "window": window,
            }
        )
    return chunks
