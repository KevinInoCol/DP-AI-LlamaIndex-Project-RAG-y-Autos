"""
API del agente de Productos de Salud (FastAPI).

Expone el agente RAG (agent.py) por HTTP para que cualquier frontend lo consuma.
La interfaz de Streamlit vive fuera de este proyecto (carpeta Frontend-Productos-Salud)
y habla con esta API.

Endpoints:
- POST   /chat                  → pregunta al agente (con memoria por session_id)
- DELETE /chat/{session_id}     → reinicia la conversación
- POST   /documents             → sube un documento y re-indexa la colección
- GET    /documents             → info del documento indexado
- GET    /health                → estado del servicio

Ejecutar:
    uvicorn app:app --reload --port 8000
"""

import os
import uuid
from contextlib import asynccontextmanager
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from llama_index.core.memory import ChatMemoryBuffer
from pydantic import BaseModel, Field

from agent import aask, build_chat_memory
from RAG import SemanticRAG, SentenceRAG
from vector_store import QDRANT_URL

# ------------------------------------------------------------------------------------------
# CONFIGURACIÓN INICIAL
# ------------------------------------------------------------------------------------------
load_dotenv()

# Ruta donde se almacenan los documentos que serán indexados
DOC_PATH = "./RAG/Base de Conocimientos"

SplitterName = Literal["SentenceSplitter", "SemanticSplitter"]
SPLITTER_OPTIONS = {
    "SentenceSplitter": SentenceRAG,
    "SemanticSplitter": SemanticRAG,
}

# ------------------------------------------------------------------------------------------
# ESTADO DEL PROCESO
# ------------------------------------------------------------------------------------------
# En Streamlit el estado vivía en st.session_state (uno por pestaña). En una API un
# mismo proceso atiende a todos los clientes, así que el historial se indexa por
# session_id. Sigue siendo memoria RAM: se pierde al reiniciar el servidor.
_rag_managers: dict[str, object] = {}
_sessions: dict[str, ChatMemoryBuffer] = {}


def _get_rag_manager(splitter: str):
    """Un RAGManager por estrategia de splitting, creado la primera vez que se pide."""
    if splitter not in _rag_managers:
        try:
            _rag_managers[splitter] = SPLITTER_OPTIONS[splitter](doc_path=DOC_PATH)
        except Exception as e:
            raise HTTPException(503, f"No se pudo conectar con Qdrant en {QDRANT_URL}: {e}")
    return _rag_managers[splitter]


def _has_docs() -> bool:
    return os.path.exists(DOC_PATH) and any(os.scandir(DOC_PATH))


def _get_index(splitter: str):
    """Devuelve el índice listo para consultar, cargándolo o creándolo si hace falta.

    Mismos escenarios que tenía la app de Streamlit:
    - Ya en memoria → se reutiliza.
    - La colección de Qdrant tiene vectores → se conecta (sin pagar embeddings).
    - Colección vacía pero hay archivos en la carpeta → pipeline RAG completo.
    - Nada de lo anterior → None.
    """
    rag_manager = _get_rag_manager(splitter)
    if rag_manager.index is not None:
        return rag_manager.index

    if rag_manager.index_exists():
        rag_manager.index = rag_manager.load_index_from_storage()
    elif _has_docs():
        documents = rag_manager.load_documents()
        if documents:
            rag_manager.index = rag_manager.create_index_from_documents(documents)
            rag_manager.save_index(rag_manager.index)
    return rag_manager.index


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Sin API key no hay embeddings ni LLM; sin Qdrant no hay vectores.
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no encontrada. Crea un archivo .env con tu API key.")
    if not QDRANT_URL:
        raise RuntimeError("QDRANT_URL no encontrada. Añádela al .env apuntando a tu servidor Qdrant.")
    yield


app = FastAPI(title="Datachatbot - Productos de Salud", lifespan=lifespan)


# ------------------------------------------------------------------------------------------
# ESQUEMAS
# ------------------------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["¿Para qué sirve VitaCalm?"])
    session_id: str | None = Field(None, description="Omitir para iniciar una conversación nueva.")
    splitter: SplitterName = "SentenceSplitter"


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    turns: int


class DocumentInfo(BaseModel):
    splitter: SplitterName
    collection: str
    indexed: bool
    filename: str | None = None
    preview: str | None = None


# ------------------------------------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Consulta al agente. Reenvía el session_id devuelto para mantener el historial."""
    # Cargar/crear el índice habla con Qdrant y bloquea: se ejecuta en un hilo.
    index = await run_in_threadpool(_get_index, req.splitter)
    if index is None:
        raise HTTPException(
            409,
            "No hay documentos indexados. Sube un archivo en POST /documents "
            "o añade documentos en 'Base de Conocimientos'.",
        )

    session_id = req.session_id or str(uuid.uuid4())
    memory = _sessions.setdefault(session_id, build_chat_memory())

    try:
        answer = await aask(index, req.question, memory=memory)
    except Exception as e:
        raise HTTPException(502, f"Error al consultar el agente: {e}")

    return ChatResponse(answer=answer, session_id=session_id, turns=len(memory.get_all()))


@app.delete("/chat/{session_id}", status_code=204)
async def reset_conversation(session_id: str):
    """Reinicia el historial de una conversación."""
    _sessions.pop(session_id, None)


@app.post("/documents", response_model=DocumentInfo)
def upload_document(
    file: UploadFile = File(...),
    splitter: SplitterName = Form("SentenceSplitter"),
):
    """Reemplaza la base de conocimientos por el archivo subido y re-indexa.

    Se limpia la carpeta y se BORRA la colección de Qdrant; si no, los vectores del
    documento anterior seguirían allí y el agente respondería mezclando ambos.
    Es `def` (no async) porque indexar bloquea: FastAPI lo corre en un hilo aparte.
    """
    os.makedirs(DOC_PATH, exist_ok=True)
    for old_file in os.listdir(DOC_PATH):
        os.remove(os.path.join(DOC_PATH, old_file))

    filename = os.path.basename(file.filename or "documento")
    file_path = os.path.join(DOC_PATH, filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())

    rag_manager = _get_rag_manager(splitter)
    rag_manager.index, documents, filename = rag_manager.process_new_document(file_path)

    preview = documents[0].text[:10000] if documents else None
    return DocumentInfo(
        splitter=splitter,
        collection=rag_manager.collection_name,
        indexed=True,
        filename=filename,
        preview=preview,
    )


@app.get("/documents", response_model=DocumentInfo)
def document_info(splitter: SplitterName = "SentenceSplitter"):
    """Info del documento en la base de conocimientos (para el sidebar del frontend)."""
    index = _get_index(splitter)
    rag_manager = _get_rag_manager(splitter)
    filename, preview = rag_manager.get_document_info()
    return DocumentInfo(
        splitter=splitter,
        collection=rag_manager.collection_name,
        indexed=index is not None,
        filename=filename,
        preview=preview,
    )
