# Backend-RAGs · API de Text Splitters (FastAPI + LlamaIndex)

API que aplica los distintos **Text Splitters / Node Parsers** de LlamaIndex
sobre un texto y devuelve los chunks resultantes.

## Instalación (conda)

```bash
cd Backend-RAGs
conda activate LlamaIndex-RAG      # entorno ya creado con Python 3.12
pip install -r requirements.txt
```

> El entorno `LlamaIndex-RAG` usa Python 3.12. Evita las versiones muy nuevas
> (3.14) porque `tiktoken`/`tree-sitter` aún no traen wheels para ellas.

## Configuración (opcional)

Solo necesaria para los splitters **semánticos** (Con API Key):

```bash
cp .env.example .env
# edita .env y coloca tu OPENAI_API_KEY
```

## Ejecutar

```bash
conda activate LlamaIndex-RAG
uvicorn main:app --reload --port 8000
```

Docs interactivas: http://localhost:8000/docs

## Endpoints

| Método | Ruta         | Descripción                                  |
|--------|--------------|----------------------------------------------|
| GET    | `/splitters` | Catálogo de técnicas (agrupadas por API key) |
| POST   | `/split`     | Divide un texto con el splitter elegido      |
| POST   | `/extract`   | Extrae texto de un archivo (.txt/.md/.pdf…)  |
| GET    | `/health`    | Estado del servicio                          |

## Splitters incluidos

**🟢 Sin API Key**
- `SentenceSplitter`
- `TokenTextSplitter`
- `SentenceWindowNodeParser`
- `CodeSplitter`

**🔵 Con API Key (OpenAI)**
- `SemanticSplitterNodeParser`
