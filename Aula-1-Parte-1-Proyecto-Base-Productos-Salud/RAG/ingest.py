"""
Script de INGESTA: carga la Base de Conocimientos en Qdrant.

Ejecuta el pipeline completo (loader → splitter → embeddings → vector store)
para una o las dos estrategias de splitting, y deja los vectores escritos en el
servidor Qdrant. La app (app.py) solo se conecta a esas colecciones; no vuelve a
pagar embeddings.

Uso:

    python RAG/ingest.py                  # ambas colecciones
    python RAG/ingest.py --sentence       # solo SentenceSplitter
    python RAG/ingest.py --semantic       # solo SemanticSplitter
    python RAG/ingest.py --dry-run        # no escribe: solo informa qué haría

Por defecto BORRA la colección antes de escribir, para que reindexar no deje
vectores huérfanos del contenido anterior. Con --append se conserva lo que haya.
"""

import argparse
import os
import sys

# Permite `python RAG/ingest.py` desde la raíz: sin esto, sys.path[0] es RAG/
# y `import vector_store` (que vive en la raíz) falla.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from RAG import SemanticRAG, SentenceRAG
from vector_store import (
    COLLECTION_SEMANTIC,
    COLLECTION_SENTENCE,
    QDRANT_URL,
    collection_has_points,
    get_client,
)

load_dotenv()

DOC_PATH = "./RAG/Base de Conocimientos"

# (etiqueta, clase, colección) — el orden es el de ejecución
PIPELINES = {
    "sentence": ("SentenceSplitter", SentenceRAG, COLLECTION_SENTENCE),
    "semantic": ("SemanticSplitter", SemanticRAG, COLLECTION_SEMANTIC),
}


def verificar_precondiciones() -> None:
    """Falla pronto y con un mensaje claro, antes de gastar en embeddings."""
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Falta OPENAI_API_KEY en el .env.")
    if not QDRANT_URL:
        raise SystemExit("Falta QDRANT_URL en el .env.")
    if not os.path.isdir(DOC_PATH):
        raise SystemExit(f"No existe la carpeta de documentos: {DOC_PATH}")
    archivos = [f for f in os.listdir(DOC_PATH) if not f.startswith(".")]
    if not archivos:
        raise SystemExit(f"La carpeta {DOC_PATH} está vacía: no hay nada que indexar.")
    print(f"Documentos a indexar ({len(archivos)}):")
    for f in sorted(archivos):
        print(f"  - {f}")


def ingestar(clave: str, append: bool, dry_run: bool) -> None:
    etiqueta, clase, coleccion = PIPELINES[clave]
    print(f"\n{'=' * 78}\n{etiqueta} → colección '{coleccion}'\n{'=' * 78}")

    manager = clase(doc_path=DOC_PATH)

    if dry_run:
        existe = collection_has_points(coleccion)
        print(f"  [dry-run] La colección {'YA tiene vectores' if existe else 'está vacía o no existe'}.")
        print(f"  [dry-run] Se {'conservaría' if append else 'borraría'} antes de escribir.")
        return

    if not append:
        print("  Borrando la colección anterior...")
        manager.reset_index()

    print("  Cargando documentos...")
    documentos = manager.load_documents()
    print(f"  {len(documentos)} documento(s) cargado(s).")

    print("  Chunking + embeddings + escritura en Qdrant (esto tarda)...")
    manager.create_index_from_documents(documentos)

    total = get_client().count(coleccion, exact=True).count
    print(f"  OK: {total} vectores en '{coleccion}'.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga la Base de Conocimientos en Qdrant.")
    parser.add_argument("--sentence", action="store_true", help="Solo el SentenceSplitter")
    parser.add_argument("--semantic", action="store_true", help="Solo el SemanticSplitter")
    parser.add_argument("--append", action="store_true", help="No borrar la colección antes de escribir")
    parser.add_argument("--dry-run", action="store_true", help="No escribe nada, solo informa")
    args = parser.parse_args()

    # Sin flags de selección se ejecutan las dos
    claves = [k for k in PIPELINES if getattr(args, k)] or list(PIPELINES)

    verificar_precondiciones()
    print(f"\nQdrant: {QDRANT_URL}")

    for clave in claves:
        ingestar(clave, append=args.append, dry_run=args.dry_run)

    print("\nIngesta terminada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
