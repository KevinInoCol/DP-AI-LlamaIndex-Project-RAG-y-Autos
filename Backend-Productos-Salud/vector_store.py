"""
Configuración del vector store. FUENTE ÚNICA del proyecto.

Los vectores ya NO viven en disco (carpeta Almacenamiento_Vectorial/): viven en
el servidor Qdrant de la VPS. Todo el que necesite hablar con Qdrant pasa por
aquí — los dos pipelines de RAG/, la app y cualquier script de mantenimiento.
Nadie más construye un QdrantClient ni repite el nombre de una colección.

Convención de nombrado (skill rag-tenant-collection-naming):
toda colección empieza por el prefijo del tenant, `tenant_id_`, con guiones
bajos. El nombre se valida antes de crear nada.
"""

import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from validacion_nombre_tenant_id import validar_qdrant

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# Una colección por estrategia de splitting: el chunking distinto produce nodos
# distintos, y mezclarlos en la misma colección envenena el retrieval.
COLLECTION_SENTENCE = os.getenv(
    "QDRANT_COLLECTION_SENTENCE", "tenant_id_productos_salud_sentence"
)
COLLECTION_SEMANTIC = os.getenv(
    "QDRANT_COLLECTION_SEMANTIC", "tenant_id_productos_salud_semantic"
)

# Nota sobre la dimensión: no se declara aquí. Qdrant crea la colección con el
# tamaño del primer vector que recibe (1536 para text-embedding-3-small).
# Cambiar de modelo de embeddings obliga a borrar la colección y reindexar.

# Timeout generoso: la VPS puede tardar en responder al indexar lotes grandes.
QDRANT_TIMEOUT = 60

_client: QdrantClient | None = None


def validar_nombre_coleccion(nombre: str) -> str:
    """Guardia de nombrado. Falla antes de tocar la red o el modelo de embeddings."""
    resultado = validar_qdrant(nombre)
    if not resultado.ok:
        raise ValueError(f"Nombre de colección inválido: {resultado.motivos}")
    return nombre


def _puerto_para(url: str) -> int | None:
    """Decide qué puerto pasarle al cliente cuando la URL no lleva uno.

    qdrant-client rellena el puerto con 6333 si la URL no lo trae. Eso es
    correcto para un Qdrant expuesto en crudo, pero rompe el caso de un
    reverse proxy (EasyPanel, Traefik, nginx), donde la URL es
    https://host sin puerto y el servicio escucha en el 443: el cliente
    intentaría https://host:6333 y devolvería "Connection refused".

    Devolver None hace que el cliente construya la URL sin puerto y use el
    del esquema (443 en https). Si la URL trae puerto explícito, este valor
    se ignora y manda el de la URL.
    """
    parsed = urlparse(url)
    if parsed.port is not None:
        return None  # la URL manda; el valor da igual
    if parsed.scheme == "https":
        return None  # detrás de proxy TLS: puerto 443 implícito
    return 6333  # http sin puerto: Qdrant en crudo


def get_client() -> QdrantClient:
    """Cliente Qdrant único para todo el proceso.

    Streamlit re-ejecuta el script en cada interacción, así que cachearlo a
    nivel de módulo evita abrir una conexión nueva por click.
    """
    global _client
    if _client is None:
        if not QDRANT_URL:
            raise RuntimeError(
                "Falta QDRANT_URL en el .env. Apunta a tu servidor Qdrant "
                "(por ejemplo https://qdrant.mi-vps.com)."
            )
        _client = QdrantClient(
            url=QDRANT_URL,
            port=_puerto_para(QDRANT_URL),
            api_key=QDRANT_API_KEY or None,
            timeout=QDRANT_TIMEOUT,
        )
    return _client


def get_vector_store(collection_name: str) -> QdrantVectorStore:
    """Devuelve el vector store de una colección.

    No crea la colección: Qdrant la crea sola, con la dimensión correcta, la
    primera vez que se insertan nodos.
    """
    validar_nombre_coleccion(collection_name)
    return QdrantVectorStore(
        client=get_client(),
        collection_name=collection_name,
    )


def collection_has_points(collection_name: str) -> bool:
    """True si la colección existe Y tiene vectores dentro.

    Sustituye al viejo `os.path.exists(index_file)`. Ojo con la diferencia: una
    colección creada pero vacía existe y no sirve para responder nada, así que
    aquí cuenta como "no hay índice".
    """
    client = get_client()
    if not client.collection_exists(collection_name):
        return False
    return client.count(collection_name, exact=True).count > 0


def reset_collection(collection_name: str) -> None:
    """Borra la colección entera para reindexar desde cero.

    Necesario al subir un documento nuevo: sin esto los vectores del documento
    anterior siguen en Qdrant y el agente sigue respondiendo con ellos.
    """
    validar_nombre_coleccion(collection_name)
    client = get_client()
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)
