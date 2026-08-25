import os
import pymupdf
from pathlib import Path
from llama_index.core import VectorStoreIndex, StorageContext, Document
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding

from vector_store import (
    COLLECTION_SEMANTIC,
    collection_has_points,
    get_vector_store,
    reset_collection,
)


class RAGManager:
    """
    Pipeline RAG usando SemanticSplitterNodeParser.

    A diferencia de SentenceSplitter (que corta por tamaño fijo),
    SemanticSplitter analiza la SIMILITUD SEMÁNTICA entre oraciones
    y corta cuando detecta un cambio de tema.

    Ventaja:  chunks más coherentes temáticamente.
    Desventaja: más lento y costoso (hace llamadas al modelo de embeddings para decidir dónde cortar).

    Los vectores se almacenan en Qdrant (servidor remoto), en una colección
    DISTINTA a la del SentenceSplitter: los chunks no son comparables.
    """

    def __init__(
        self,
        doc_path: str = "./data/",
        collection_name: str = COLLECTION_SEMANTIC,
        breakpoint_percentile_threshold: int = 95,
        buffer_size: int = 1, #Para un valor de 1: Compara la temática o el tema con el vecino inmediato
    ):
        """
        Args:
            doc_path: Ruta a la carpeta donde se almacenan los documentos
            collection_name: Colección de Qdrant donde viven los vectores
            breakpoint_percentile_threshold: Umbral para decidir dónde cortar (default: 95).
                Cuanto más alto, menos cortes → chunks más grandes.
            buffer_size: Cuántas oraciones agrupa para comparar similitud (default: 1)
        """
        self.doc_path = doc_path
        self.collection_name = collection_name
        self.index = None
        # ============================================== Embedding Model ===============================================
        # Modelo que convierte texto en vectores numéricos (dimensiones: 1536)
        # NOTA: SemanticSplitter TAMBIÉN usa este modelo para decidir dónde cortar
        self.embeddings_model = OpenAIEmbedding(model="text-embedding-3-small")
        # ============================================== Document Splitter (Semántico) ===============================================
        # NO usa chunk_size ni chunk_overlap.
        # En su lugar, compara la similitud semántica entre oraciones consecutivas
        # y corta cuando detecta un cambio grande de tema.
        # Los chunks pueden tener tamaños muy desiguales (depende del contenido).
        self.text_splitter = SemanticSplitterNodeParser(
            embed_model=self.embeddings_model,
            breakpoint_percentile_threshold=breakpoint_percentile_threshold,
            buffer_size=buffer_size,
        )
        # ============================================== Vector Store (Qdrant) ===============================================
        # La colección se crea sola en el servidor la primera vez que se insertan nodos.
        self.vector_store = get_vector_store(collection_name)

    def load_documents(self) -> list:
        """
        Carga los documentos desde la carpeta especificada.

        Returns:
            Lista de documentos cargados
        """
        # ============================================== Paso 1: Document Loader ===============================================
        # Lee todos los archivos de la carpeta y los convierte en objetos Document
        # Usa pymupdf para PDFs (mejor extracción de texto que pypdf)
        documents = []
        for root, _, files in os.walk(self.doc_path):
            for fname in files:
                if fname.startswith("."):
                    continue
                filepath = os.path.join(root, fname)
                if fname.lower().endswith(".pdf"):
                    doc = pymupdf.open(filepath)
                    text = "\n".join(page.get_text() for page in doc)
                    doc.close()
                else:
                    text = Path(filepath).read_text(errors="ignore")
                documents.append(Document(text=text, metadata={"filename": fname}))
        return documents

    def create_index_from_documents(self, documents: list) -> VectorStoreIndex:
        """
        Crea un índice vectorial a partir de los documentos, escribiendo en Qdrant.

        Args:
            documents: Lista de documentos a indexar

        Returns:
            VectorStoreIndex creado
        """
        # ============================================== Paso 2: Splitting (Semántico) ===============================================
        # ============================================== Paso 3: Embeddings ===============================================
        # ============================================== Paso 4: Vector Store ===============================================
        # from_documents() ejecuta los 3 pasos de una vez:
        #   1) Divide los documentos por CAMBIOS DE TEMA (según similitud semántica)
        #   2) Genera embeddings de cada chunk (usando embeddings_model)
        #   3) Escribe los vectores DIRECTAMENTE en la colección de Qdrant
        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            embed_model=self.embeddings_model,
            transformations=[self.text_splitter],
        )
        return index

    def save_index(self, index: VectorStoreIndex):
        """No hace nada: Qdrant persiste en el momento de la inserción."""
        return None

    def load_index_from_storage(self) -> VectorStoreIndex:
        """Carga el índice desde Qdrant, sin releer ni reprocesar los documentos."""
        index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            embed_model=self.embeddings_model,
        )
        return index

    def index_exists(self) -> bool:
        """Verifica si la colección de Qdrant existe y tiene vectores dentro."""
        return collection_has_points(self.collection_name)

    def reset_index(self) -> None:
        """Borra la colección en Qdrant para reindexar desde cero."""
        reset_collection(self.collection_name)
        self.index = None
        # El vector store guarda una referencia a la colección borrada: se pide uno nuevo.
        self.vector_store = get_vector_store(self.collection_name)

    def process_new_document(self, file_path: str) -> tuple:
        """Procesa un nuevo documento: limpia la colección, lo carga y lo indexa."""
        self.reset_index()
        documents = self.load_documents()
        index = self.create_index_from_documents(documents)
        filename = os.path.basename(file_path)
        return index, documents, filename

    def get_document_info(self) -> tuple:
        """Obtiene información del documento actual para mostrar en la UI."""
        if not os.path.exists(self.doc_path):
            return None, None

        doc_files = os.listdir(self.doc_path)
        if not doc_files:
            return None, None

        doc_filename = doc_files[0]
        documents = self.load_documents()

        if documents:
            doc_text = documents[0].text[:10000] + "..." if len(documents[0].text) > 10000 else documents[0].text
            return doc_filename, doc_text

        return None, None
