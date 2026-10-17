"""
Frontend de Streamlit para el agente de Productos de Salud.

Ya no importa el agente ni el RAG: todo pasa por la API de FastAPI del proyecto
Backend-Productos-Salud.

Layout:
- Sidebar izquierdo: estrategia de splitting, carga de documentos e info del índice.
- Área principal: el chat, a todo el ancho de la pantalla.

Ejecutar (con la API levantada):
    streamlit run app.py
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

# Indexar y consultar al agente puede tardar; los timeouts son generosos.
CHAT_TIMEOUT = 120
UPLOAD_TIMEOUT = 300

SPLITTER_OPTIONS = ["SentenceSplitter", "SemanticSplitter"]

st.set_page_config(page_title="Datachatbot", page_icon="🤖", layout="wide")


def api_error(e: requests.RequestException) -> str:
    """Extrae el `detail` que devuelve FastAPI, o el error de conexión."""
    if e.response is not None:
        try:
            return e.response.json().get("detail", e.response.text)
        except ValueError:
            return e.response.text
    return f"No se pudo conectar con la API en {API_URL}: {e}"


# ------------------------------------------------------------------------------------------
# ESTADO DE LA APLICACIÓN
# ------------------------------------------------------------------------------------------
# El historial que usa el agente vive en la API (identificado por session_id).
# `messages` es solo la copia que se pinta en pantalla.
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "turns" not in st.session_state:
    st.session_state.turns = 0
if "indexed_file" not in st.session_state:
    st.session_state.indexed_file = None


def reset_conversation():
    if st.session_state.session_id:
        try:
            requests.delete(f"{API_URL}/chat/{st.session_state.session_id}", timeout=10)
        except requests.RequestException:
            pass  # si la API no responde, igual empezamos una sesión nueva
    st.session_state.session_id = None
    st.session_state.messages = []
    st.session_state.turns = 0


# ------------------------------------------------------------------------------------------
# SIDEBAR IZQUIERDO: base de conocimientos
# ------------------------------------------------------------------------------------------
with st.sidebar:
    st.header("📚 Base de conocimientos")
    splitter_choice = st.selectbox("Estrategia de Splitting:", SPLITTER_OPTIONS)
    uploaded_file = st.file_uploader("Sube un documento para el RAG")

    # Subir un archivo nuevo → la API limpia la base de conocimientos y re-indexa
    if uploaded_file is not None and uploaded_file.name != st.session_state.indexed_file:
        with st.spinner("Indexando documento..."):
            try:
                r = requests.post(
                    f"{API_URL}/documents",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue())},
                    data={"splitter": splitter_choice},
                    timeout=UPLOAD_TIMEOUT,
                )
                r.raise_for_status()
                st.session_state.indexed_file = uploaded_file.name
                st.success(f"'{uploaded_file.name}' indexado correctamente.")
            except requests.RequestException as e:
                st.error(f"⚠️ {api_error(e)}")

    # Info del documento indexado
    try:
        r = requests.get(f"{API_URL}/documents", params={"splitter": splitter_choice}, timeout=UPLOAD_TIMEOUT)
        r.raise_for_status()
        info = r.json()
    except requests.RequestException as e:
        st.error(f"⚠️ {api_error(e)}")
        st.stop()

    st.info(f"Splitter: **{splitter_choice}**\n\nColección Qdrant: `{info['collection']}`")
    if info["filename"]:
        st.subheader("Documento en proceso:")
        st.caption(info["filename"])
        if info["preview"]:
            with st.expander("Ver contenido"):
                st.write(info["preview"])
    elif not info["indexed"]:
        st.warning(
            "No hay archivos en 'Base de Conocimientos'. "
            "Sube al menos un archivo o añade documentos en esa carpeta."
        )

    st.divider()
    st.button("Reiniciar conversación", on_click=reset_conversation, use_container_width=True)
    st.caption(f"Turnos en memoria: {st.session_state.turns}")


# ------------------------------------------------------------------------------------------
# ÁREA PRINCIPAL: chat a todo el ancho
# ------------------------------------------------------------------------------------------
st.title("Datachatbot responde tus dudas")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if not info["indexed"]:
    st.info("Sube un documento en el panel izquierdo para empezar a chatear.")
elif prompt := st.chat_input("Haz una pregunta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                r = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "question": prompt,
                        "session_id": st.session_state.session_id,
                        "splitter": splitter_choice,
                    },
                    timeout=CHAT_TIMEOUT,
                )
                r.raise_for_status()
            except requests.RequestException as e:
                st.error(f"⚠️ {api_error(e)}")
                st.stop()
        data = r.json()
        st.markdown(data["answer"])

    st.session_state.session_id = data["session_id"]
    st.session_state.turns = data["turns"]
    st.session_state.messages.append({"role": "assistant", "content": data["answer"]})
    # Re-ejecuta para que el contador de turnos del sidebar se actualice
    st.rerun()
