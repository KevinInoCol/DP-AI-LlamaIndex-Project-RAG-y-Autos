from llama_index.core.tools import QueryEngineTool


def get_retrieval_tool(index, llm):
    query_engine = index.as_query_engine(llm=llm, similarity_top_k=5)
    return QueryEngineTool.from_defaults(
        query_engine=query_engine,
        name="knowledge_base",
        description="Consulta los documentos indexados. Úsala para responder preguntas sobre su contenido.",
    )
