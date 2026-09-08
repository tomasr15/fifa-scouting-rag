"""Métricas sin estado global: seguras entre sesiones y exportables como JSON."""
from time import perf_counter_ns


def elapsed_ms(start_ns: int) -> float:
    return (perf_counter_ns() - start_ns) / 1_000_000


def filter_fields(where: dict | None) -> set[str]:
    fields = set()
    for key, value in (where or {}).items():
        if key in ("$and", "$or"):
            for child in value:
                fields.update(filter_fields(child))
        else:
            fields.add(key)
    return fields


def filter_metadata(metadata: dict, where: dict | None) -> dict:
    """Valores escalares de los campos referenciados; no es un plan interno de Chroma."""
    return {key: metadata[key] for key in sorted(filter_fields(where)) if key in metadata}


def collection_summary(collection) -> dict:
    count = collection.count()
    dimensions = None
    if count:
        sample = collection.get(limit=1, include=["embeddings"])
        dimensions = len(sample["embeddings"][0])
    return {"collection_name": collection.name,
            "space": (collection.configuration.get("hnsw") or {}).get("space"),
            "vector_count": count, "dimensions": dimensions,
            "index_type": "HNSW (Chroma; puede incluir buffer de fuerza bruta)",
            "creation_metadata": {"hnsw:space": "cosine"}}


def print_collection_summary(summary: dict) -> None:
    print("\n=== COLECCIÓN VECTORIAL ===")
    print(f"Nombre: {summary['collection_name']} | Espacio real: {summary['space']}")
    print(f"Creación: metadata={summary['creation_metadata']}")
    print(f"Vectores: {summary['vector_count']} | D = {summary['dimensions']}")
    print(f"Índice: {summary['index_type']}")


def print_search_metrics(result: dict) -> None:
    print("\n=== MÉTRICAS DE RECUPERACIÓN ===")
    print(f"execution_time_ms (llamada Chroma, sin embedding): {result['execution_time_ms']:.6f}")
    print(f"embedding_time_ms: {result['embedding_time_ms']:.6f}")
    print(f"retrieval_time_ms (recuperación completa, sin LLM): {result['retrieval_time_ms']:.6f}")
