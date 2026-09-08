"""Pruebas de integración con Chroma y MiniLM reales; LLM simulado sin costo."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from openai import OpenAI
from streamlit.testing.v1 import AppTest

from data_loader import generate_mock_csv, load_players, prepare_records
from rag_pipeline import LLMConfig, run_scouting
from vector_store import PlayerVectorStore, build_filter


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Windows mantiene handles de Chroma abiertos hasta finalizar el proceso.
        cls.temp = tempfile.mkdtemp(prefix="scouting-test-")
        cls.csv = generate_mock_csv(Path(cls.temp) / "players.csv")
        cls.df, _ = load_players(cls.csv)
        cls.store = PlayerVectorStore(Path(cls.temp) / "db")
        cls.store.initialize(cls.df)

    def test_index_persistence_and_cosine(self):
        self.assertEqual(self.store.collection.count(), 30)
        self.assertFalse(self.store.initialize(self.df))
        reopened = PlayerVectorStore(Path(self.temp) / "db")
        self.assertEqual(reopened.collection.count(), 30)
        self.assertEqual(reopened.collection.configuration["hnsw"]["space"], "cosine")
        docs = prepare_records(self.df)[1]
        hit = reopened.query_players(docs[0], 1)[0]
        self.assertEqual(hit["metadata"]["name"], "Lionel Messi")
        self.assertAlmostEqual(hit["distance"], 0, places=4)
        stored = reopened.collection.get(ids=[hit["id"]], include=["embeddings"])
        self.assertEqual(len(stored["embeddings"][0]), 384)

    def test_combined_filter_and_order(self):
        where = build_filter("La Liga", 26, "MC")
        hits = self.store.query_players("volante mixto físico con pase largo", 30, where)
        self.assertTrue(hits)
        for hit in hits:
            self.assertLessEqual(hit["metadata"]["age"], 26)
            self.assertEqual(hit["metadata"]["league"], "La Liga")
            self.assertEqual(hit["metadata"]["position"], "MC")
            self.assertAlmostEqual(hit["distance"] + hit["similarity"], 1)
        self.assertEqual([h["distance"] for h in hits], sorted(h["distance"] for h in hits))

    def test_empty_results_skip_llm(self):
        with patch("rag_pipeline.OpenAI") as client:
            result = run_scouting("delantero", self.store,
                                  where_filter=build_filter("Liga inexistente"),
                                  config=LLMConfig.from_env("ollama"))
            self.assertEqual(result["candidates"], [])
            client.assert_not_called()

    def test_invalid_queries_and_changed_dataset(self):
        with self.assertRaises(ValueError):
            self.store.query_players("  ")
        with self.assertRaises(ValueError):
            self.store.query_players("pase", 0)
        changed = self.df.copy()
        changed.loc[0, "age"] = 38
        with self.assertRaisesRegex(ValueError, "CSV cambiado"):
            self.store.initialize(changed)
        self.assertEqual(self.store.collection.count(), 30)

    def test_csv_validation_and_stable_ids(self):
        broken = Path(self.temp) / "broken.csv"
        self.df.drop(columns=["age"]).to_csv(broken, index=False)
        with self.assertRaisesRegex(ValueError, "Faltan columnas"):
            load_players(broken)
        negative = self.df.copy()
        negative.loc[0, "pace"] = -1
        negative.to_csv(broken, index=False)
        with self.assertRaises(ValueError):
            load_players(broken)
        with self.assertRaises(FileNotFoundError):
            load_players(Path(self.temp) / "missing.csv")
        ids, _, _ = prepare_records(self.df)
        self.assertEqual(len(set(ids)), 30)
        self.assertEqual(ids, prepare_records(self.df)[0])

    def test_real_openai_sdk_with_mock_http_transport(self):
        def handler(request):
            body = json.loads(request.content)
            self.assertTrue(str(request.url).endswith("/v1/chat/completions"))
            self.assertEqual(body["model"], "gpt-4o-mini")
            context = json.loads(body["messages"][1]["content"])
            self.assertEqual(len(context["contexto_recuperado"]), 2)
            return httpx.Response(200, json={
                "id": "test", "object": "chat.completion", "created": 1,
                "model": "gpt-4o-mini", "choices": [{"index": 0,
                "message": {"role": "assistant", "content": "Reporte de prueba [J1]."},
                "finish_reason": "stop"}]})
        client = OpenAI(api_key="test-key", base_url="http://test.local/v1",
                        http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        with patch("rag_pipeline.OpenAI", return_value=client):
            result = run_scouting("volante mixto", self.store, k=2,
                                  config=LLMConfig("openai", "gpt-4o-mini", "http://test.local/v1", "test-key"))
        self.assertTrue(result["generated"])
        self.assertIn("[J1]", result["report"])

    def test_gateway_error_body_without_choices_degrades(self):
        """OpenRouter puede responder 200 con el error del proveedor en el cuerpo.
        El SDK entrega choices=None y eso no debe tirar abajo la búsqueda resuelta."""
        def handler(request):
            return httpx.Response(200, json={"id": "x", "object": "chat.completion",
                "created": 1, "model": "m", "error": {"message": "upstream", "code": 502}})
        client = OpenAI(api_key="test-key", base_url="http://test.local/v1",
                        http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        with patch("rag_pipeline.OpenAI", return_value=client):
            result = run_scouting("volante mixto", self.store, k=2,
                                  config=LLMConfig("openai", "m", "http://test.local/v1", "k"))
        self.assertFalse(result["generated"])
        self.assertIn("No se pudo generar el reporte", result["warning"])
        self.assertEqual(len(result["candidates"]), 2)

    def test_generation_failure_retains_retrieval(self):
        with patch("rag_pipeline.OpenAI", side_effect=ValueError("test")):
            result = run_scouting("pase largo", self.store,
                                  config=LLMConfig.from_env("ollama"))
        self.assertFalse(result["generated"])
        self.assertTrue(result["warning"])
        self.assertEqual(len(result["candidates"]), 5)

    def test_streamlit_search(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.run(timeout=120)
        next(x for x in app.selectbox if x.label == "Dataset").select("Demo sintética · 30 jugadores").run(timeout=60)
        self.assertFalse(app.exception)
        app.button[0].click().run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 5)


if __name__ == "__main__":
    unittest.main()
