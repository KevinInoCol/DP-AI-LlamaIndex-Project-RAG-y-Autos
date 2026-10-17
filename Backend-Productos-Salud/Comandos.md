Virtual Environment:
- Python 3.11
- Nombre "Datapath-LlamaIndex"


# Backend (API FastAPI) — desde esta carpeta
uvicorn app:app --reload --port 8000
# Documentación interactiva: http://localhost:8000/docs

# Frontend (Streamlit) — desde ../Frontend-Productos-Salud
streamlit run app.py
