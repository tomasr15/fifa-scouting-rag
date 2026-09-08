"""Controles del snapshot oficial y de la recuperación real, sin API de pago."""
import json
from pathlib import Path
import unittest
from urllib.parse import urlparse

import pandas as pd
from streamlit.testing.v1 import AppTest
from fifa_corpus import DATA, load_corpus, open_fifa_store


class FifaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_corpus()
        cls.pm = pd.read_csv(DATA / 'player_matches.csv')

    def test_coverage_and_joins(self):
        players = pd.read_csv(DATA / 'players.csv')
        self.assertEqual(len(players), 1000)
        self.assertEqual(len(pd.read_csv(DATA / 'clubs.csv')), 32)
        self.assertEqual(len(pd.read_csv(DATA / 'coaches.csv')), 32)
        self.assertEqual(len(self.pm), 1998)
        self.assertEqual(self.pm.match_id.nunique(), 63)
        self.assertEqual(self.pm.entity_id.nunique(), 675)
        self.assertTrue(set(self.pm.entity_id) <= set(players.entity_id))
        self.assertFalse(self.pm.isna().any().any())
        self.assertFalse(self.pm.duplicated(['match_id', 'entity_id']).any())
        self.assertTrue((self.pm.passes_completed <= self.pm.passes_attempted).all())
        self.assertTrue(self.pm.top_speed_kmh.between(0, 45).all())

    def test_visually_checked_pdf_values(self):
        row = self.pm[(self.pm.match_id == 6) & (self.pm.entity_id == 'chelseafc:1')].iloc[0]
        self.assertEqual((row.passes_attempted, row.passes_completed), (26, 20))
        self.assertAlmostEqual(row.distance_m, 4158.9)
        self.assertAlmostEqual(row.top_speed_kmh, 25.4)
        self.assertEqual((row.distribution_page, row.physical_page), (42, 50))

    def test_identity_excluded_and_sources_present(self):
        self.assertEqual(len(self.records), 2452)
        self.assertEqual(len({r['id'] for r in self.records}), 2452)
        for r in self.records:
            m = r['metadata']
            self.assertEqual(m['gender'], 'male')
            self.assertNotIn(m['name'].casefold(), r['embedding_text'].casefold())
            self.assertNotIn('overall_rating', m)
            for ref in json.loads(m['source_refs_json']):
                host = urlparse(ref['url']).hostname
                self.assertIn(host, {'fdp.fifa.org', 'inside.fifa.com', 'www.fifatrainingcentre.com'})

    def test_missing_stats_and_economics(self):
        roster = [r for r in self.records if r['metadata']['aspect'] == 'roster']
        self.assertEqual(len(roster), 325)
        self.assertTrue(all(not r['metadata']['has_stats'] for r in roster))
        economics = [r for r in self.records if r['metadata']['aspect'] == 'economics']
        self.assertEqual(len(economics), 32)
        for r in economics:
            self.assertLessEqual(r['metadata']['participation_min_usd'], r['metadata']['participation_max_usd'])
            self.assertIn('no cobro auditado', r['document'])

    def test_real_index_and_identical_filters(self):
        store, records, benchmark = open_fifa_store()
        self.assertEqual(store.technical_summary()['dimensions'], 384)
        self.assertEqual(store.technical_summary()['space'], 'cosine')
        where = {'$and': [{'entity_type': 'player'}, {'club': 'Chelsea FC'}, {'aspect': 'editorial_tactics'}]}
        result = benchmark.benchmark_search('Lateral que avanza por dentro', where)
        self.assertGreaterEqual(result['vector']['execution_time_ms'], 0)
        for side in ('vector', 'lexical'):
            for hit in result[side]['candidates']:
                self.assertEqual(hit['metadata']['club'], 'Chelsea FC')
                self.assertEqual(hit['metadata']['aspect'], 'editorial_tactics')
        for hit in result['vector']['candidates']:
            self.assertAlmostEqual(hit['similarity'], 1 - hit['distance'])

    def test_streamlit_real_search(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=120)
        next(x for x in app.selectbox if x.label == 'Dataset').select('FIFA real · Mundial de Clubes 2025').run(timeout=120)
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label == 'Buscar evidencia FIFA').click().run(timeout=120)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(app.session_state.fifa_result['candidates'])
        self.assertEqual(len(app.metric), 3)


if __name__ == '__main__':
    unittest.main()
