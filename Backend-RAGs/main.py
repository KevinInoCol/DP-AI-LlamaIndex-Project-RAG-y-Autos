"""
API FastAPI para visualizar los Text Splitters de LlamaIndex.

Endpoints:
  GET  /splitters        -> catálogo de técnicas (agrupadas por API key)
  POST /split            -> divide un texto con el splitter elegido
  POST /extract          -> extrae texto plano de un archivo subido (.txt/.md/.pdf/...)
  GET  /health           -> estado del servicio

Ejecutar:
  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import io
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from loaders import list_loaders, load_document
from splitters import list_splitters, split_text

load_dotenv()

app = FastAPI(title="RAG Text Splitters Visualizer", version="1.0.0")

# CORS abierto para desarrollo (frontend en Vite: 5173).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SplitRequest(BaseModel):
    splitter: str
    text: str
    params: dict[str, Any] = {}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "openai_key_loaded": bool(os.getenv("OPENAI_API_KEY"))}


@app.get("/splitters")
def get_splitters() -> dict[str, Any]:
    """Catálogo de splitters para construir el menú del frontend."""
    return {"splitters": list_splitters()}


@app.post("/split")
def post_split(req: SplitRequest) -> dict[str, Any]:
    """Aplica un splitter a un texto y devuelve los chunks + estadísticas."""
    try:
        chunks = split_text(req.splitter, req.text, req.params)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:  # p.ej. falta OPENAI_API_KEY
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error al dividir: {exc}") from exc

    total_tokens = sum(c["token_count"] for c in chunks)
    total_chars = sum(c["char_count"] for c in chunks)
    return {
        "splitter": req.splitter,
        "num_chunks": len(chunks),
        "stats": {
            "total_chunks": len(chunks),
            "total_tokens": total_tokens,
            "total_chars": total_chars,
            "avg_tokens": round(total_tokens / len(chunks), 1) if chunks else 0,
            "avg_chars": round(total_chars / len(chunks), 1) if chunks else 0,
        },
        "chunks": chunks,
    }


@app.get("/loaders")
def get_loaders() -> dict[str, Any]:
    """Catálogo de Document Loaders (ordenado de peor a mejor)."""
    return {"loaders": list_loaders()}


@app.post("/load")
async def post_load(
    loader: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Extrae el texto de un archivo con el Document Loader elegido."""
    raw = await file.read()
    try:
        documents = load_document(loader, raw, file.filename or "")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:  # p.ej. falta LLAMA_CLOUD_API_KEY
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error al cargar: {exc}") from exc

    total_chars = sum(len(d["text"]) for d in documents)
    return {
        "loader": loader,
        "filename": file.filename,
        "num_documents": len(documents),
        "stats": {
            "total_documents": len(documents),
            "total_chars": total_chars,
            "avg_chars": round(total_chars / len(documents), 1) if documents else 0,
        },
        "documents": documents,
    }


@app.post("/extract")
async def post_extract(file: UploadFile = File(...)) -> dict[str, Any]:
    """Extrae texto plano de un archivo subido (.txt, .md, .pdf, código, etc.)."""
    raw = await file.read()
    filename = (file.filename or "").lower()

    if filename.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"No se pudo leer el PDF: {exc}") from exc
    else:
        # Texto / markdown / código: decodificar como UTF-8 (con fallback).
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="replace")

    return {"filename": file.filename, "chars": len(text), "text": text}
