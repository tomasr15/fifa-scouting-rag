"""Comparativa didáctica: Chroma ANN vs escaneo léxico LIKE en pandas.

Sin rankings trucados: OR inclusivo de términos, mismos documentos y mismo where.
No implementa un B-tree ni mide un motor SQL; no llama al LLM.
"""
from __future__ import annotations

from functools import lru_cache
import re
from time import perf_counter_ns
import unicodedata

import pandas as pd
from chromadb.api.types import validate_where

from data_loader import dataset_fingerprint, load_players, prepare_records
from instrumentation import elapsed_ms, filter_metadata
from vector_store import PlayerVectorStore, get_default_store

STOPWORDS = set("a al algo algun alguna alguien con como de del el en es la las lo los "
                "me mi para por que se sin su sus un una unos unas y o buscame busco "
                "buscar necesito quiero jugador jugadores".split())
DEMO_QUERY = "pasador"
BENCHMARK_NOTE = (
    "Comparativa didáctica de una consulta, no benchmark de escalabilidad. "
    "LIKE '%término%' se simula con un escaneo pandas (no B-tree). "
    "Chroma usa HNSW y puede consultar un buffer de fuerza bruta. "
    "Obtener vecinos no prueba relevancia: inspeccioná los perfiles y sus distancias."
)


def normalize_text(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c))


def keywords(query: str) -> list[str]:
    return list(dict.fromkeys(t for t in re.findall(r"\w+", normalize_text(query))
                              if t not in STOPWORDS))


def metadata_mask(frame: pd.DataFrame, where: dict | None) -> pd.Series:
    """Mismo subconjunto de metadata escalar que Chroma; rechaza campos desconocidos.

    El CSV validado no tiene nulos. Los filtros se validan antes de medir y ejecutar.
    """
    if not where:
        return pd.Series(True, index=frame.index)
    key, value = next(iter(where.items()))
    if key in ("$and", "$or"):
        masks = [metadata_mask(frame, child) for child in value]
        result = masks[0]
        for mask in masks[1:]:
            result = result & mask if key == "$and" else result | mask
        return result
    if key not in frame.columns:
        raise ValueError(f"Campo de metadata desconocido en comparativa: {key}")
    column = frame[key]
    op, operand = next(iter(value.items())) if isinstance(value, dict) else ("$eq", value)
    operations = {"$eq": column.eq, "$ne": column.ne, "$lt": column.lt,
                  "$lte": column.le, "$gt": column.gt, "$gte": column.ge,
                  "$in": column.isin, "$nin": lambda v: ~column.isin(v)}
    if op not in operations:
        raise ValueError(f"Operador no soportado: {op}")
    try:
        return operations[op](operand)
    except TypeError as exc:
        raise ValueError(f"Tipo incompatible para el campo {key}") from exc


class SearchBenchmark:
    def __init__(self, store: PlayerVectorStore, players: pd.DataFrame):
        self.store = store
        self.fingerprint = dataset_fingerprint(players)
        ids, documents, metadatas = prepare_records(players)
        self.frame = pd.DataFrame(metadatas)
        self.ids, self.documents, self.metadatas = ids, documents, metadatas
        # Preparación de corpus fuera del cronómetro, equivalente al índice ya creado.
        self.normalized_documents = pd.Series([normalize_text(d) for d in documents])

    def benchmark_search(self, query_text: str, filter_dict: dict | None = None,
                         n_results: int = 5) -> dict:
        if not query_text.strip():
            raise ValueError("Ingresá una consulta no vacía.")
        if (self.store.collection.metadata or {}).get("dataset_hash") != self.fingerprint:
            raise ValueError("La comparativa requiere el mismo dataset que el índice Chroma.")
        if filter_dict:
            validate_where(filter_dict)
        # Valida campos/tipos antes de ejecutar ambas búsquedas, incluso si no hay términos.
        metadata_mask(self.frame, filter_dict)
        vector = self.store.query_players_measured(query_text, n_results, filter_dict)
        lexical_start = perf_counter_ns()
        terms = keywords(query_text)
        mask = metadata_mask(self.frame, filter_dict)
        eligible_count = int(mask.sum())
        eligible = self.normalized_documents[mask]
        matches = pd.Series(False, index=eligible.index)
        for term in terms:
            matches |= eligible.str.contains(term, regex=False)
        all_indices = eligible.index[matches].tolist()
        # LIKE no define ranking; ordenar por ID da un LIMIT determinista.
        ordered = sorted(all_indices, key=lambda i: self.ids[i])[:n_results]
        lexical_candidates = [
            {"id": self.ids[i], "document": self.documents[i], "metadata": self.metadatas[i],
             "filter_metadata": filter_metadata(self.metadatas[i], filter_dict),
             "matched_terms": [t for t in terms if t in self.normalized_documents[i]]}
            for i in ordered
        ]
        lexical_time_ms = elapsed_ms(lexical_start)
        lexical = {"candidates": lexical_candidates, "execution_time_ms": lexical_time_ms,
                   "total_matches": len(all_indices), "eligible_count": eligible_count,
                   "terms": terms, "operator": "OR", "order_by": "id ASC", "limit": n_results,
                   "like_patterns": [f"%{t}%" for t in terms]}
        lexical_ids = {self.ids[i] for i in all_indices}
        only_vector = [c["id"] for c in vector["candidates"] if c["id"] not in lexical_ids]
        return {"query": query_text, "where_filter": filter_dict, "vector": vector,
                "lexical": lexical, "vector_only_ids": only_vector,
                "note": BENCHMARK_NOTE,
                "interpretation": (
                    "Sin términos útiles después de quitar palabras vacías; no se ejecuta LIKE sin condición."
                    if not terms else
                    "Hay vecinos vectoriales sin coincidencia literal: revisar su encaje conceptual."
                    if only_vector else
                    "No hay candidatos vectoriales exclusivos en esta consulta; ambas vías pueden coincidir."
                )}


@lru_cache(maxsize=1)
def _default_benchmark() -> SearchBenchmark:
    players, _ = load_players()
    store = get_default_store()
    store.initialize(players)
    return SearchBenchmark(store, players)


def benchmark_search(query_text: str, filter_dict: dict | None = None) -> dict:
    """API de dos argumentos solicitada; usar SearchBenchmark para CSV/BD propios o k."""
    return _default_benchmark().benchmark_search(query_text, filter_dict)
