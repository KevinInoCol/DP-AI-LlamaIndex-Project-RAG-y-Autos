"""
Módulo RAG (Retrieval-Augmented Generation) — versión LlamaCloud.

Ahora usa las tecnologías gestionadas de LlamaIndex:
- LlamaParse      -> Document Loader avanzado (parsing con IA: tablas, layout, OCR)
- LlamaCloudIndex -> Índice + base de datos vectorial gestionados en la nube

Responsabilidades:
- Ingesta:  documentos → LlamaParse → vectores en LlamaCloud   (ingest_data_with_llamaparse)
- Runtime:  el agente se conecta al índice de la nube            (load_or_create_index)

Las consultas las maneja el agente en agent.py usando tools/retrieval.py
(index.as_query_engine(...)), que sigue siendo compatible con LlamaCloudIndex.
"""

import os
import sys
import logging

from dotenv import load_dotenv

# Logging claro para ver el proceso de ingesta.
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Carga las variables de entorno (.env del proyecto).
load_dotenv()

# La API key de LlamaCloud es necesaria tanto para LlamaParse como para
# LlamaCloudIndex. Se expone también como variable de entorno.
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
if LLAMA_CLOUD_API_KEY:
    os.environ["LLAMA_CLOUD_API_KEY"] = LLAMA_CLOUD_API_KEY

from llama_index.core import Settings, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_parse import LlamaParse

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #
DOC_PATH = "../Base_de_Conocimiento"
LLAMA_CLOUD_INDEX_NAME = "catalogoautos"          # Nombre del índice en LlamaCloud
LLAMA_CLOUD_PROJECT_NAME = os.getenv("LLAMA_CLOUD_PROJECT_NAME", "Default")

# ============================================== Paso 1: Document Loader (LlamaParse) ===============================================
# LlamaParse usa modelos de visión para entender mejor la estructura del PDF
# (tablas, columnas, precios), mucho más preciso que un parser tradicional.
parser = LlamaParse(
    api_key=LLAMA_CLOUD_API_KEY,
    result_type="markdown",   # Devuelve Markdown estructurado, ideal para RAG
    language="es",            # Español para mejor reconocimiento
    verbose=True,
)

# ============================================== Paso 2: Document Splitter ===============================================
Settings.text_splitter = SentenceSplitter(
    chunk_size=1024,     # Chunks grandes para aprovechar el parsing de LlamaParse
    chunk_overlap=200,   # Overlap para mantener contexto entre chunks
)

# ============================================== Paso 3: Embedding Model ===============================================
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")


# --------------------------------------------------------------------------- #
# Ingesta (crear/actualizar el índice en la nube)
# --------------------------------------------------------------------------- #
def ingest_data_with_llamaparse(
    doc_path: str = DOC_PATH,
    index_name: str = LLAMA_CLOUD_INDEX_NAME,
) -> LlamaCloudIndex:
    """
    Pipeline de ingesta: lee los documentos con LlamaParse y sube los vectores
    a LlamaCloud, creando (o actualizando) el índice gestionado.
    """
    logging.info("=" * 80)
    logging.info("🚀 INGESTA RAG CON LLAMAPARSE + LLAMACLOUD")
    logging.info("=" * 80)

    # ---- Paso 1: Document Loader con LlamaParse ----
    logging.info(f"🔍 Cargando documentos desde '{doc_path}' con LlamaParse...")
    file_extractor = {
        ".pdf": parser,
        ".docx": parser,
        ".pptx": parser,
    }
    documents = SimpleDirectoryReader(
        doc_path,
        recursive=True,
        exclude_hidden=True,
        file_extractor=file_extractor,
    ).load_data()

    if not documents:
        logging.warning("⚠️ No se encontraron documentos para procesar.")
        raise RuntimeError(f"No hay documentos en '{doc_path}'.")

    logging.info(f"✅ {len(documents)} documento(s) cargado(s). Subiendo a LlamaCloud…")
    logging.info("⏳ LlamaParse puede tardar un poco, pero mejora la calidad.")

    # ---- Paso 2: Llevar los vectores a LlamaCloud ----
    index = LlamaCloudIndex.from_documents(
        documents=documents,
        name=index_name,
        project_name=LLAMA_CLOUD_PROJECT_NAME,
        api_key=LLAMA_CLOUD_API_KEY,
        verbose=True,
    )

    logging.info("=" * 80)
    logging.info(f"🎉 Índice '{index_name}' creado/actualizado en LlamaCloud.")
    logging.info("=" * 80)
    return index


# --------------------------------------------------------------------------- #
# Conexión (runtime) — usada por el agente
# --------------------------------------------------------------------------- #
def connect_to_cloud_index(index_name: str = LLAMA_CLOUD_INDEX_NAME) -> LlamaCloudIndex:
    """Se conecta a un índice ya existente en LlamaCloud (sin re-ingestar)."""
    return LlamaCloudIndex(
        name=index_name,
        project_name=LLAMA_CLOUD_PROJECT_NAME,
        api_key=LLAMA_CLOUD_API_KEY,
    )


def load_or_create_index(
    doc_path: str = DOC_PATH,
    index_name: str = LLAMA_CLOUD_INDEX_NAME,
) -> LlamaCloudIndex:
    """
    Devuelve el índice listo para consultar (compatible con agent.py).

    - Si el índice ya existe en LlamaCloud → se conecta a él (rápido, sin costo).
    - Si no existe todavía → lo crea ingestando los documentos con LlamaParse.
    """
    if not LLAMA_CLOUD_API_KEY:
        raise RuntimeError(
            "Falta LLAMA_CLOUD_API_KEY en el .env. Consíguela en "
            "https://cloud.llamaindex.ai para usar LlamaParse y LlamaCloudIndex."
        )

    try:
        logging.info(f"☁️ Conectando al índice '{index_name}' en LlamaCloud…")
        return connect_to_cloud_index(index_name)
    except Exception as exc:  # noqa: BLE001
        logging.warning(f"No se pudo conectar al índice ({exc}).")
        logging.info("📥 Creándolo desde documentos con LlamaParse…")
        return ingest_data_with_llamaparse(doc_path, index_name)


if __name__ == "__main__":
    # Ejecuta este archivo directamente para (re)crear el índice en la nube:
    #   python RAG/rag.py
    ingest_data_with_llamaparse()
