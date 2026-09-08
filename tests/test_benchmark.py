"""Instrumentación y comparativa sobre la base real, sin servicios LLM."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from streamlit.testing.v1 import AppTest

from benchmark import DEMO_QUERY, SearchBenchmark, metadata_mask
from data_loader import generate_mock_csv, load_players
from rag_pipeline import run_scouting
from vector_store import PlayerVectorStore, build_filter


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = Path(tempfile.mkdtemp(prefix="scouting-benchmark-test-"))
        cls.df, _ = load_players(generate_mock_csv(folder / "players.csv"))
        cls.store = PlayerVectorStore(folder / "db")
        cls.store.initialize(cls.df)
        cls.benchmark = SearchBenchmark(cls.store, cls.df)

    def test_timings_raw_cosine_and_filtered_metadata(self):
        where = build_filter("La Liga", 27, "MC")
        result = self.store.query_players_measured("buen pase largo", 3, where)
        self.assertTrue(result["query_executed"])
        self.assertGreater(result["execution_time_ms"], 0)
        self.assertGreater(result["embedding_time_ms"], 0)
        self.assertGreaterEqual(result["retrieval_time_ms"],
                                result["execution_time_ms"] + result["embedding_time_ms"])
        query_vector = np.asarray(self.store.embedding_function(["buen pase largo"])[0])
        for hit in result["candidates"]:
            vector = self.store.collection.get(ids=[hit["id"]], include=["embeddings"])["embeddings"][0]
            expected = 1 - np.dot(query_vector, vector) / (np.linalg.norm(query_vector) * np.linalg.norm(vector))
            self.assertAlmostEqual(hit["distance"], expected, places=5)
            self.assertEqual(hit["similarity"], 1 - hit["distance"])
            self.assertEqual(hit["filter_metadata"], {k: hit["metadata"][k] for k in ("league", "age", "position")})

    def test_conceptual_demo_without_literal_matches(self):
        result = self.benchmark.benchmark_search(DEMO_QUERY)
        self.assertEqual(result["lexical"]["total_matches"], 0)
        self.assertEqual(result["lexical"]["terms"], ["pasador"])
        self.assertEqual(result["vector"]["candidates"][0]["metadata"]["name"], "Pedri")
        self.assertEqual(len(result["vector_only_ids"]), 5)

    def test_literal_search_finds_matches_and_shares_where(self):
        where = {"$and": [{"age": {"$lte": 27}}, {"$or": [
            {"league": "La Liga"}, {"league": "Premier League"}]}]}
        result = self.benchmark.benchmark_search("PÁSE", where, 30)
        lexical = result["lexical"]
        self.assertGreater(lexical["total_matches"], 0)
        self.assertEqual(lexical["terms"], ["pase"])
        # Compara filtros contra Chroma.get (no contra la implementación pandas).
        exact = self.store.collection.get(where=where)
        self.assertEqual(lexical["eligible_count"], len(exact["ids"]))
        for hit in lexical["candidates"] + result["vector"]["candidates"]:
            self.assertIn(hit["id"], exact["ids"])
        self.assertEqual([h["id"] for h in lexical["candidates"]],
                         sorted(h["id"] for h in lexical["candidates"]))

    def test_filter_operator_parity_with_chroma(self):
        for where in [{"age": {"$gt": 25}}, {"age": {"$lt": 25}},
                      {"age": {"$gte": 25}}, {"age": {"$ne": 25}},
                      {"position": {"$in": ["MC", "MCD"]}},
                      {"position": {"$nin": ["MC", "MCD"]}}]:
            with self.subTest(where=where):
                mask = metadata_mask(self.benchmark.frame, where)
                pandas_ids = {self.benchmark.ids[i] for i in self.benchmark.frame.index[mask]}
                self.assertEqual(pandas_ids, set(self.store.collection.get(where=where)["ids"]))

    def test_empty_lexical_terms_and_filters(self):
        result = self.benchmark.benchmark_search("de la y")
        self.assertEqual(result["lexical"]["total_matches"], 0)
        self.assertEqual(result["lexical"]["terms"], [])
        result = self.benchmark.benchmark_search("pase", {"age": {"$lt": 15}})
        self.assertEqual(result["vector"]["candidates"], [])
        self.assertEqual(result["lexical"]["eligible_count"], 0)
        with self.assertRaises(ValueError):
            self.benchmark.benchmark_search("pase", {"missing_field": "x"})
        with self.assertRaises(ValueError):
            self.benchmark.benchmark_search("pase", {"age": {"$unknown": 25}})
        with self.assertRaises(ValueError):
            self.benchmark.benchmark_search("  ")

    def test_rag_reuses_one_measured_query(self):
        with patch.object(self.store, "query_players_measured", wraps=self.store.query_players_measured) as measured:
            result = run_scouting("pase largo", self.store, benchmark=self.benchmark)
        self.assertEqual(measured.call_count, 1)
        self.assertEqual(result["execution_time_ms"], result["benchmark"]["vector"]["execution_time_ms"])
        self.assertEqual(result["candidates"], result["benchmark"]["vector"]["candidates"])

    def test_reject_different_corpus(self):
        changed = self.df.copy()
        changed.loc[0, "age"] = 38
        with self.assertRaisesRegex(ValueError, "mismo dataset"):
            SearchBenchmark(self.store, changed).benchmark_search("pase")

    def test_summary_and_empty_collection(self):
        summary = self.store.technical_summary()
        self.assertEqual(summary["vector_count"], 30)
        self.assertEqual(summary["dimensions"], 384)
        self.assertEqual(summary["space"], "cosine")
        empty = PlayerVectorStore(Path(tempfile.mkdtemp(prefix="scouting-empty-test-")))
        result = empty.query_players_measured("pase")
        self.assertFalse(result["query_executed"])
        self.assertEqual(result["execution_time_ms"], 0)
        self.assertEqual(result["candidates"], [])
        self.assertIsNone(empty.technical_summary()["dimensions"])

    def test_streamlit_benchmark_mode(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.run(timeout=60)
        next(x for x in app.selectbox if x.label == "Dataset").select("Demo sintética · 30 jugadores").run(timeout=60)
        self.assertFalse(app.exception)
        next(c for c in app.checkbox if c.label == "Comparar ANN vs LIKE").check()
        app.text_area[0].set_value(DEMO_QUERY)
        app.button[0].click().run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 3)
        self.assertEqual(len(app.dataframe), 2)
        self.assertIn("ID vector", app.dataframe[0].value.columns)
        self.assertEqual(app.session_state.result["benchmark"]["lexical"]["total_matches"], 0)


if __name__ == "__main__":
    unittest.main()
