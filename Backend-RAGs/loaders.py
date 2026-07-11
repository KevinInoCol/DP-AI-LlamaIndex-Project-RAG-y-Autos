"""
Catálogo de Document Loaders (Readers) para extraer texto de archivos.

Ordenados de PEOR a MEJOR (campo `quality`, 1 = básico … 4 = el mejor):

  1. PyPDF (manual)          -> extracción cruda, sin framework (baseline)
  2. PDFReader (LlamaIndex)  -> Reader básico del framework
  3. PyMuPDFReader (Llama.)  -> mejor extracción de texto y layout
  4. LlamaParse (LlamaIndex) -> parsing con IA (tablas, layout, OCR) [API KEY]

Cada loader recibe (raw: bytes, filename: str) y devuelve una lista de
"documentos" -> [{"text": str, "metadata": dict}]. Un PDF suele producir un
documento por página.
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Any, Callable


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def _write_temp(raw: bytes, filename: str) -> str:
    """Escribe los bytes a un archivo temporal y devuelve su ruta.

    Los Readers de LlamaIndex trabajan con rutas de archivo, no con bytes.
    """
    suffix = Path(filename or "").suffix or ".pdf"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(raw)
    tmp.close()
    return tmp.name


def _docs_from_llama(documents: list[Any]) -> list[dict[str, Any]]:
    """Convierte objetos Document de LlamaIndex a dicts serializables."""
    out = []
    for d in documents:
        text = d.get_content() if hasattr(d, "get_content") else str(d)
        meta = dict(d.metadata) if getattr(d, "metadata", None) else {}
        out.append({"text": text, "metadata": meta})
    return out


# --------------------------------------------------------------------------- #
# Implementaciones de cada loader
# --------------------------------------------------------------------------- #
def _load_pypdf(raw: bytes, filename: str) -> list[dict[str, Any]]:
    """1) PyPDF manual: recorre páginas y usa page.extract_text()."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    return [
        {"text": (page.extract_text() or ""), "metadata": {"page": i + 1}}
        for i, page in enumerate(reader.pages)
    ]


def _load_pdfreader(raw: bytes, filename: str) -> list[dict[str, Any]]:
    """2) PDFReader de LlamaIndex (envuelve pypdf, un Document por página)."""
    from llama_index.readers.file import PDFReader

    tmp = _write_temp(raw, filename)
    try:
        documents = PDFReader().load_data(file=Path(tmp))
    finally:
        os.unlink(tmp)
    return _docs_from_llama(documents)


def _load_pymupdf(raw: bytes, filename: str) -> list[dict[str, Any]]:
    """3) PyMuPDFReader de LlamaIndex (motor PyMuPDF/fitz, mejor calidad)."""
    from llama_index.readers.file import PyMuPDFReader

    tmp = _write_temp(raw, filename)
    try:
        reader = PyMuPDFReader()
        try:
            documents = reader.load_data(file_path=tmp)
        except TypeError:
            # Compatibilidad entre versiones (algunas usan `file` en vez de `file_path`)
            documents = reader.load_data(file=Path(tmp))
    finally:
        os.unlink(tmp)
    return _docs_from_llama(documents)


def _load_llamaparse(raw: bytes, filename: str) -> list[dict[str, Any]]:
    """4) LlamaParse: parsing con IA en la nube. Requiere LLAMA_CLOUD_API_KEY."""
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta LLAMA_CLOUD_API_KEY. Consíguela en https://cloud.llamaindex.ai "
            "y colócala en el archivo .env para usar LlamaParse."
        )

    from llama_parse import LlamaParse

    tmp = _write_temp(raw, filename)
    try:
        parser = LlamaParse(api_key=api_key, result_type="markdown")
        documents = parser.load_data(tmp)
    finally:
        os.unlink(tmp)
    return _docs_from_llama(documents)


# --------------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------------- #
LOADERS: dict[str, dict[str, Any]] = {
    "pypdf": {
        "name": "PyPDF (manual)",
        "group": "no_api",
        "quality": 1,
        "engine": "pypdf",
        "accepts": [".pdf"],
        "description": (
            "El clásico. Extracción cruda página por página con page.extract_text(). "
            "Sin framework. Funciona con PDFs de texto simple, pero pierde tablas, "
            "columnas y no hace OCR de escaneos."
        ),
        "loader": _load_pypdf,
    },
    "pdf_reader": {
        "name": "PDFReader (LlamaIndex)",
        "group": "no_api",
        "quality": 2,
        "engine": "llama-index-readers-file",
        "accepts": [".pdf"],
        "description": (
            "El Reader básico de LlamaIndex. Envuelve pypdf y devuelve un objeto "
            "Document por página con metadata (page_label). Ya usa la abstracción "
            "del framework, pero la calidad de extracción es similar a PyPDF."
        ),
        "loader": _load_pdfreader,
    },
    "pymupdf": {
        "name": "PyMuPDFReader (LlamaIndex)",
        "group": "no_api",
        "quality": 3,
        "engine": "pymupdf / fitz",
        "accepts": [".pdf"],
        "description": (
            "Usa el motor PyMuPDF (fitz). Extracción más rápida y precisa, respeta "
            "mejor el orden de lectura y el layout. La mejor opción SIN API key para "
            "PDFs de texto."
        ),
        "loader": _load_pymupdf,
    },
    "llama_parse": {
        "name": "LlamaParse (LlamaIndex)",
        "group": "api",
        "quality": 4,
        "engine": "LlamaCloud (IA)",
        "accepts": [".pdf", ".docx", ".pptx", ".xlsx", ".html"],
        "description": (
            "El mejor. Parsing con IA en la nube: entiende tablas, columnas, "
            "figuras y hace OCR de documentos escaneados. Devuelve Markdown limpio "
            "listo para RAG. Requiere LLAMA_CLOUD_API_KEY."
        ),
        "loader": _load_llamaparse,
    },
}


def list_loaders() -> list[dict[str, Any]]:
    """Catálogo (sin funciones) para el frontend, ordenado de peor a mejor."""
    items = sorted(LOADERS.items(), key=lambda kv: kv[1]["quality"])
    return [
        {
            "key": key,
            "name": cfg["name"],
            "group": cfg["group"],
            "quality": cfg["quality"],
            "engine": cfg["engine"],
            "accepts": cfg["accepts"],
            "description": cfg["description"],
            "requires_api_key": cfg["group"] == "api",
        }
        for key, cfg in items
    ]


def load_document(key: str, raw: bytes, filename: str) -> list[dict[str, Any]]:
    """Aplica el loader indicado y devuelve la lista de documentos extraídos."""
    if key not in LOADERS:
        raise KeyError(f"Loader desconocido: {key}")
    return LOADERS[key]["loader"](raw, filename)
