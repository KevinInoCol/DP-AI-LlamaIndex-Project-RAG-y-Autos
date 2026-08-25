import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding

from vector_store import (
    COLLECTION_SENTENCE,
    collection_has_points,
    get_vector_store,
    reset_collection,
)


class RAGManager:
    """
    Clase para gestionar el pipeline de datos RAG (sin el agente conversacional):
    - Carga de documentos
    - Creación de índices vectoriales
    - Persistencia y carga de índices

    Los vectores se almacenan en Qdrant (servidor remoto), no en disco.

    Las preguntas las responde `KnowledgeAgent` en agent.py usando este índice.
    """

    def __init__(
        self,
        doc_path: str = "./data/",
        collection_name: str = COLLECTION_SENTENCE,
        chunk_size: int = 128,
        chunk_overlap: int = 0,
    ):
        """
        Inicializa el RAGManager con la ruta de documentos y la colección de Qdrant.

        Args:
            doc_path: Ruta a la carpeta donde se almacenan los documentos
            collection_name: Colección de Qdrant donde viven los vectores
            chunk_size: Tamaño máximo de cada chunk en caracteres (default: 128)
            chunk_overlap: Solapamiento entre chunks en caracteres (default: 0)
        """
        self.doc_path = doc_path
        self.collection_name = collection_name
        self.index = None
        # ============================================== Embedding Model ===============================================
        # Modelo que convierte texto en vectores numéricos (dimensiones: 1536)
        self.embeddings_model = OpenAIEmbedding(model="text-embedding-3-small")
        # ============================================== Document Splitter ===============================================
        # Configura cómo se dividen los documentos en chunks antes de generar embeddings
        self.text_splitter = SentenceSplitter(
            chunk_size=chunk_size,       # Tamaño máximo de cada chunk (en caracteres)
            chunk_overlap=chunk_overlap,  # Solapamiento entre chunks (para no perder contexto)
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
        # Lee todos los archivos de la carpeta (PDFs, TXTs, etc.) y los convierte en objetos Document
        loader = SimpleDirectoryReader(self.doc_path, recursive=True, exclude_hidden=True)
        documents = loader.load_data()
        return documents

    def create_index_from_documents(self, documents: list) -> VectorStoreIndex:
        """
        Crea un índice vectorial a partir de los documentos, escribiendo en Qdrant.

        Args:
            documents: Lista de documentos a indexar

        Returns:
            VectorStoreIndex creado
        """
        # ============================================== Paso 2: Splitting ===============================================
        # ============================================== Paso 3: Embeddings ===============================================
        # ============================================== Paso 4: Vector Store ===============================================
        # from_documents() ejecuta los 3 pasos de una vez:
        #   1) Divide los documentos en chunks (según text_splitter)
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
        """
        No hace nada: Qdrant persiste en el momento de la inserción.

        Se conserva el método para que app.py no tenga que saber qué backend hay
        detrás. Con el índice en disco había que llamar a persist(); con un vector
        store remoto los vectores ya están guardados al salir de
        create_index_from_documents().
        """
        return None

    def load_index_from_storage(self) -> VectorStoreIndex:
        """
        Carga el índice desde Qdrant, sin releer ni reprocesar los documentos.

        Returns:
            VectorStoreIndex cargado
        """
        index = VectorStoreIndex.from_vector_store(
            self.vector_store,
            embed_model=self.embeddings_model,
        )
        return index

    def index_exists(self) -> bool:
        """
        Verifica si la colección de Qdrant existe y tiene vectores dentro.

        Returns:
            True si hay índice utilizable, False en caso contrario
        """
        return collection_has_points(self.collection_name)

    def reset_index(self) -> None:
        """
        Borra la colección en Qdrant para reindexar desde cero.

        Sin esto, al subir un documento nuevo los vectores del anterior seguirían
        en el servidor y el agente respondería mezclando ambos.
        """
        reset_collection(self.collection_name)
        self.index = None
        # El vector store guarda una referencia a la colección borrada: se pide uno nuevo.
        self.vector_store = get_vector_store(self.collection_name)

    def process_new_document(self, file_path: str) -> tuple:
        """
        Procesa un nuevo documento: limpia la colección, lo carga y lo indexa.

        Args:
            file_path: Ruta al archivo del documento

        Returns:
            Tupla con (índice, documentos, nombre_archivo)
        """
        # Vaciar la colección anterior en Qdrant
        self.reset_index()

        # Cargar documentos
        documents = self.load_documents()

        # Crear índice (escribe en Qdrant)
        index = self.create_index_from_documents(documents)

        # Obtener nombre del archivo
        filename = os.path.basename(file_path)

        return index, documents, filename

    def get_document_info(self) -> tuple:
        """
        Obtiene información del documento actual para mostrar en la UI.

        Returns:
            Tupla con (nombre_archivo, texto_documento) o (None, None) si no hay documentos
        """
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
