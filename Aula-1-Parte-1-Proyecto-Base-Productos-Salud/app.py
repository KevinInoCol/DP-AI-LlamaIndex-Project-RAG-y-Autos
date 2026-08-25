import os
import streamlit as st
from dotenv import load_dotenv
from agent import ask, build_chat_memory
from RAG import SentenceRAG, SemanticRAG
from vector_store import QDRANT_URL

# ------------------------------------------------------------------------------------------
# CONFIGURACIÓN INICIAL
# ------------------------------------------------------------------------------------------
# Carga las variables de entorno desde el archivo .env (donde está la OPENAI_API_KEY)
load_dotenv()

# Verificamos que la API Key exista antes de continuar.
# Sin ella, no podemos generar embeddings ni consultar el LLM.
if not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️ Error: OPENAI_API_KEY no encontrada. Por favor, crea un archivo .env con tu API key.")
    st.stop()

# Los vectores viven en Qdrant, así que sin servidor no hay ni indexación ni consulta.
if not QDRANT_URL:
    st.error("⚠️ Error: QDRANT_URL no encontrada. Añádela al .env apuntando a tu servidor Qdrant.")
    st.stop()

# Ruta donde se almacenan los documentos que serán indexados
doc_path = "./RAG/Base de Conocimientos"

# ------------------------------------------------------------------------------------------
# SELECTOR DE SPLITTER
# ------------------------------------------------------------------------------------------
# El alumno puede elegir entre dos estrategias de splitting desde la UI
SPLITTER_OPTIONS = {
    "SentenceSplitter": SentenceRAG,
    "SemanticSplitter": SemanticRAG,
}
splitter_choice = st.sidebar.selectbox(
    "Estrategia de Splitting:",
    list(SPLITTER_OPTIONS.keys()),
)
try:
    rag_manager = SPLITTER_OPTIONS[splitter_choice](doc_path=doc_path)
except Exception as e:
    st.error(f"⚠️ No se pudo conectar con Qdrant en {QDRANT_URL}: {e}")
    st.stop()
st.sidebar.info(
    f"Splitter: **{splitter_choice}**\n\nColección Qdrant: `{rag_manager.collection_name}`"
)

# ------------------------------------------------------------------------------------------
# ESTADO DE LA APLICACIÓN (Streamlit Session State)
# ------------------------------------------------------------------------------------------
# Streamlit re-ejecuta todo el script en cada interacción del usuario.
# Usamos session_state para que la respuesta persista entre re-ejecuciones
# y no se pierda al hacer click en otro botón.
if "response" not in st.session_state:
    st.session_state.response = ""
if "indexed_file" not in st.session_state:
    st.session_state.indexed_file = None
if "chat_memory" not in st.session_state:
    st.session_state.chat_memory = build_chat_memory()

# ------------------------------------------------------------------------------------------
# CONSULTA vía el agente de IA (agent.py)
# ------------------------------------------------------------------------------------------
def send_click():
    if rag_manager.index is not None:
        st.session_state.response = ask(
            rag_manager.index,
            st.session_state.prompt,
            memory=st.session_state.chat_memory,
        )

def reset_conversation():
    """Reinicia el historial de chat creando un buffer nuevo."""
    st.session_state.chat_memory = build_chat_memory()
    st.session_state.response = ""

# ------------------------------------------------------------------------------------------
# INTERFAZ DE USUARIO (UI)
# ------------------------------------------------------------------------------------------
st.title("Datachatbot responde tus dudas")
sidebar_placeholder = st.sidebar.container()  # Panel lateral para mostrar info del documento
uploaded_file = st.file_uploader("Elige un archivo")  # Widget para subir archivos

# ==========================================================================================
# LÓGICA DE INDEXACIÓN - Decide si crear, cargar o actualizar el índice
# ==========================================================================================
# Hay 3 escenarios posibles cada vez que se ejecuta la app:

# ------------------------------------------------------------------------------------------
# ESCENARIO 1: El usuario sube un archivo nuevo
# ------------------------------------------------------------------------------------------
# → Se limpia la carpeta "Base de Conocimientos" (borra documentos anteriores)
# → Se BORRA la colección en Qdrant (si no, los vectores viejos seguirían allí)
# → Se guarda SOLO el archivo nuevo
# → Se RE-INDEXA con ese único documento
if uploaded_file is not None and uploaded_file.name != st.session_state.indexed_file:
    # Crear la carpeta si no existe
    os.makedirs(doc_path, exist_ok=True)

    # Limpiar documentos anteriores de la carpeta
    for old_file in os.listdir(doc_path):
        os.remove(os.path.join(doc_path, old_file))

    # Guardar el archivo subido en disco
    bytes_data = uploaded_file.read()
    file_path = os.path.join(doc_path, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(bytes_data)

    # Procesar: cargar el documento → crear índice → guardarlo
    with st.spinner("Indexando documento... Esto puede tardar unos segundos."):
        rag_manager.index, documents, filename = rag_manager.process_new_document(file_path)
    st.session_state.indexed_file = uploaded_file.name
    st.success(f"Documento '{uploaded_file.name}' indexado correctamente. Ya puedes hacer preguntas.")

    # Mostrar información del documento en el sidebar
    sidebar_placeholder.header("Documento en proceso:")
    sidebar_placeholder.subheader(filename)
    if documents:
        doc_text = documents[0].text[:10000] + "..." if len(documents[0].text) > 10000 else documents[0].text
        sidebar_placeholder.write(doc_text)

# ------------------------------------------------------------------------------------------
# ESCENARIO 2: No se sube archivo, pero la colección de Qdrant ya tiene vectores
# ------------------------------------------------------------------------------------------
# → Simplemente se conecta a la colección (rápido, sin re-procesar documentos ni pagar embeddings)
# → Esto es lo que pasa en la mayoría de ejecuciones después de la primera
elif rag_manager.index_exists():
    rag_manager.index = rag_manager.load_index_from_storage()

    # Intentar mostrar info del documento en el sidebar
    doc_filename, doc_text = rag_manager.get_document_info()
    if doc_filename:
        sidebar_placeholder.header("Documento en proceso:")
        sidebar_placeholder.subheader(doc_filename)
        sidebar_placeholder.write(doc_text)
    else:
        sidebar_placeholder.warning(
            "No se encontró ningún archivo en la carpeta 'Base de Conocimientos'. "
            "Solo se cargaron los vectores ya presentes en Qdrant."
        )

# ------------------------------------------------------------------------------------------
# ESCENARIO 3: La colección de Qdrant no existe o está vacía (primera ejecución)
# ------------------------------------------------------------------------------------------
# → Busca archivos en "Base de Conocimientos"
# → Si los encuentra, ejecuta el pipeline completo: cargar → chunking → embeddings → índice
# → Los vectores quedan escritos en Qdrant para futuras ejecuciones (Escenario 2)
elif not rag_manager.index_exists():
    has_docs = os.path.exists(doc_path) and any(os.scandir(doc_path))
    if has_docs:
        documents = rag_manager.load_documents()
    else:
        documents = []
    if documents:
        # Pipeline RAG completo: documentos → chunks → embeddings → índice vectorial
        with st.spinner("Indexando documentos... Esto puede tardar unos segundos."):
            rag_manager.index = rag_manager.create_index_from_documents(documents)
            rag_manager.save_index(rag_manager.index)
        st.success("Documentos indexados correctamente. Ya puedes hacer preguntas.")

        doc_filename, doc_text = rag_manager.get_document_info()
        sidebar_placeholder.header("Documento en proceso:")
        sidebar_placeholder.subheader(doc_filename or "Base de Conocimientos")
        if doc_text:
            sidebar_placeholder.write(doc_text)
    else:
        sidebar_placeholder.warning(
            "No hay archivos en 'Base de Conocimientos'. "
            "Sube al menos un archivo o añade documentos en esa carpeta."
        )

# ==========================================================================================
# AGENTE DE IA + CONSULTA (solo si hay índice)
# ==========================================================================================
if rag_manager.index is not None:
    st.text_input("Haz una pregunta: ", key="prompt")
    col_send, col_reset = st.columns([1, 1])
    with col_send:
        st.button("Consultar", on_click=send_click, type="primary")
    with col_reset:
        st.button("Reiniciar conversación", on_click=reset_conversation)

    # Mostrar la respuesta si existe
    if st.session_state.response:
        st.subheader("Respuesta:")
        st.success(st.session_state.response, icon="🤖")

    # Mini indicador del historial en el sidebar
    n_msgs = len(st.session_state.chat_memory.get_all())
    st.sidebar.caption(f"Turnos en memoria: {n_msgs}")