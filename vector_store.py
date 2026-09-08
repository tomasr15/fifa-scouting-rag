"""Índice persistente HNSW con embeddings locales y filtros estructurados."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import threading
from time import perf_counter_ns

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from data_loader import BASE_DIR, dataset_fingerprint, prepare_records
from instrumentation import collection_summary, elapsed_ms, filter_metadata, print_collection_summary

COLLECTION_NAME = "players_scouting"
INDEX_VERSION = "minilm-onnx-document-v1"


def build_filter(league: str | None = None, max_age: int | None = None,
                 position: str | None = None) -> dict | None:
    clauses = []
    if league:
        clauses.append({"league": {"$eq": league}})
    if max_age is not None:
        if max_age < 15 or max_age > 60:
            raise ValueError("La edad máxima debe estar entre 15 y 60.")
        clauses.append({"age": {"$lte": int(max_age)}})
    if position:
        clauses.append({"position": {"$eq": position.upper()}})
    return {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else None)


class PlayerVectorStore:
    def __init__(self, persist_path: str | Path = BASE_DIR / "chroma_db", collection_name: str = COLLECTION_NAME):
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(
            path=str(Path(persist_path).resolve()),
            settings=Settings(anonymized_telemetry=False),
        )
        self.embedding_function = DefaultEmbeddingFunction()
        self._lock = threading.RLock()
        self.collection = self._get_collection()

    def _get_collection(self):
        return self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    def initialize(self, df, rebuild: bool = False) -> bool:
        """Indexa una sola vez; rechaza CSV cambiado e índices incompletos.

        rebuild es explícito y sólo reemplaza players_scouting, nunca otras colecciones.
        El bloqueo protege sesiones Streamlit del mismo proceso.
        """
        ids, documents, metadatas = prepare_records(df)
        return self.initialize_records(ids, documents, metadatas, dataset_fingerprint(df),
                                       INDEX_VERSION, rebuild=rebuild)

    def initialize_records(self, ids, documents, metadatas, fingerprint, index_version,
                           rebuild=False, embedding_texts=None) -> bool:
        """Ingesta común: permite que FIFA vectorice perfiles sin nombres ni URLs."""
        if not ids or not len(ids) == len(documents) == len(metadatas) or len(set(ids)) != len(ids):
            raise ValueError("Registros vacíos, longitudes incompatibles o IDs duplicados.")
        if embedding_texts is not None and len(embedding_texts) != len(ids):
            raise ValueError("Los textos de embedding deben corresponder a cada ID.")
        with self._lock:
            if rebuild:
                self.client.delete_collection(self.collection_name)
                self.collection = self._get_collection()
            metadata = self.collection.metadata or {}
            if (self.collection.configuration.get("hnsw") or {}).get("space") != "cosine":
                raise ValueError("El índice no usa coseno. Ejecutá main.py --rebuild.")
            if self.collection.count():
                if (metadata.get("dataset_hash") != fingerprint
                        or metadata.get("index_version") != index_version
                        or self.collection.count() != len(ids)):
                    raise ValueError("CSV cambiado o índice incompleto. Cerrá la app y ejecutá main.py --rebuild.")
                print_collection_summary(self.technical_summary())
                return False
            # Publicamos el hash sólo al terminar todos los lotes. Un fallo parcial
            # nunca se interpreta como una ingesta completa en el siguiente arranque.
            for start in range(0, len(ids), 128):
                end = start + 128
                extra = {"embeddings": self.embedding_function(embedding_texts[start:end])} if embedding_texts is not None else {}
                self.collection.add(ids=ids[start:end], documents=documents[start:end],
                                    metadatas=metadatas[start:end], **extra)
            # Chroma prohíbe incluir hnsw:space en modify, incluso sin cambiarlo.
            # La métrica queda fijada en configuration desde la creación.
            self.collection.modify(metadata={"dataset_hash": fingerprint,
                                             "index_version": index_version})
            print_collection_summary(self.technical_summary())
            return True

    def technical_summary(self) -> dict:
        return collection_summary(self.collection)

    def query_players(self, query_text: str, n_results: int = 5,
                      where_filter: dict | None = None) -> list[dict]:
        # Compatibilidad con los consumidores que esperan una lista.
        return self.query_players_measured(query_text, n_results, where_filter)["candidates"]

    def query_players_measured(self, query_text: str, n_results: int = 5,
                               where_filter: dict | None = None) -> dict:
        """Cronometra la API Chroma por separado del embedding y del LLM.

        execution_time_ms incluye validación SDK, filtros, vecinos y materialización
        de documentos/metadata dentro de collection.query; no es tiempo puro de HNSW.
        """
        total_start = perf_counter_ns()
        if not query_text.strip():
            raise ValueError("Ingresá una consulta no vacía.")
        if not isinstance(n_results, int) or not 1 <= n_results <= 30:
            raise ValueError("n_results debe ser un entero entre 1 y 30.")
        count = self.collection.count()
        if not count:
            return {"candidates": [], "execution_time_ms": 0.0, "embedding_time_ms": 0.0,
                    "retrieval_time_ms": elapsed_ms(total_start), "query_executed": False}
        kwargs = {"where": where_filter} if where_filter else {}
        embedding_start = perf_counter_ns()
        query_embeddings = self.embedding_function([query_text.strip()])
        embedding_time_ms = elapsed_ms(embedding_start)
        query_start = perf_counter_ns()
        result = self.collection.query(
            query_embeddings=query_embeddings, n_results=min(n_results, count),
            include=["documents", "metadatas", "distances"], **kwargs,
        )
        execution_time_ms = elapsed_ms(query_start)
        candidates = [
            {"id": player_id, "document": document, "metadata": metadata,
             "distance": float(distance), "similarity": 1.0 - float(distance),
             "filter_metadata": filter_metadata(metadata, where_filter)}
            for player_id, document, metadata, distance in zip(
                result["ids"][0], result["documents"][0],
                result["metadatas"][0], result["distances"][0])
        ]
        return {"candidates": candidates, "execution_time_ms": execution_time_ms,
                "embedding_time_ms": embedding_time_ms,
                "retrieval_time_ms": elapsed_ms(total_start), "query_executed": True}


@lru_cache(maxsize=1)
def get_default_store() -> PlayerVectorStore:
    return PlayerVectorStore()


def query_players(query_text: str, n_results: int = 5,
                  where_filter: dict | None = None) -> list[dict]:
    """Atajo público solicitado; ingestar mediante initialize antes de consultar."""
    return get_default_store().query_players(query_text, n_results, where_filter)
