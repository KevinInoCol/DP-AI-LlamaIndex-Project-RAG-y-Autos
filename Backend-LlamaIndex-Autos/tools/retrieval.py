from llama_index.core.tools import QueryEngineTool


def get_retrieval_tool(index, llm):
    query_engine = index.as_query_engine(llm=llm, similarity_top_k=3)
    return QueryEngineTool.from_defaults(
        query_engine=query_engine,
        name="catalogo_vehiculos",
        description=(
            "Busca información sobre los vehículos disponibles en la tienda. "
            "Usa esta herramienta para consultar precios, modelos, marcas, "
            "características técnicas, colores, disponibilidad y cualquier "
            "dato relacionado con los automóviles y motos en venta."
        ),
    )
