"""Controles de los CSV nuevos y búsqueda real en una muestra, sin LLM remoto."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from supplied_data import DATA, build_records, prepare


class SuppliedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=build_records()

    def test_snapshot_identity_and_missing_finances(self):
        records=self.records
        self.assertEqual(len(records),18350+702+1369)
        self.assertEqual(len({r['id'] for r in records}),len(records))
        for r in records:
            self.assertEqual(r['metadata']['update_as_of'],'2023-09-22')
            self.assertEqual(r['metadata']['fifa_version'],24)
            self.assertIn('videogame',r['metadata']['source_kind'])
            if r['metadata']['entity_type']=='club':
                self.assertNotIn('transfer_budget_eur',r['metadata'])
        keeper=next(r for r in records if r['metadata'].get('is_goalkeeper'))
        self.assertNotIn('Regate gambeta',keeper['embedding_text'])
        self.assertIn('Reflejos',keeper['embedding_text'])
        self.assertNotIn(keeper['metadata']['name'],keeper['embedding_text'])

    def test_coach_join_uses_team_id_reference(self):
        teams=pd.read_csv(DATA/'male_teams.csv')
        for r in self.records:
            m=r['metadata']
            if m['entity_type']!='coach': continue
            linked=json.loads(m['team_ids_json'])
            expected=teams[teams.coach_id==int(m['entity_id'])].team_id.astype(int).tolist()
            self.assertEqual(linked,expected)
            self.assertEqual(m['has_team'],bool(expected))

    def test_historical_selection_no_cross_version_join(self):
        with tempfile.TemporaryDirectory() as root:
            source=Path(root)/'raw'; source.mkdir()
            for kind,id_col in [('players','player_id'),('teams','team_id')]:
                pd.DataFrame([{id_col:1,'fifa_version':23,'fifa_update':2,'update_as_of':'2022-09-26'},
                              {id_col:1,'fifa_version':24,'fifa_update':2,'update_as_of':'2023-09-22'}]).to_csv(source/f'male_{kind}.csv',index=False)
            pd.DataFrame([{'coach_id':1}]).to_csv(source/'male_coaches.csv',index=False)
            info=prepare(source,Path(root)/'selected',version=23)
            self.assertEqual(info['snapshot']['fifa_version'],23)
            self.assertEqual(info['counts']['players'],1)
            with self.assertRaises(ValueError): prepare(source,Path(root)/'missing',version=99)

    def test_small_real_index_and_filters(self):
        from vector_store import PlayerVectorStore
        from fifa_corpus import CorpusBenchmark,fingerprint
        forwards=[r for r in self.records if r['metadata'].get('plays_ST') and r['metadata'].get('dribbling',0)>=80][:6]
        keepers=[r for r in self.records if r['metadata'].get('is_goalkeeper')][:3]
        records=forwards+keepers
        self.assertTrue(forwards)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            store=PlayerVectorStore(directory,collection_name='supplied_test')
            store.initialize_records([r['id'] for r in records],[r['document'] for r in records],
                [r['metadata'] for r in records],fingerprint(records),'test',embedding_texts=[r['embedding_text'] for r in records])
            benchmark=CorpusBenchmark(store,records)
            result=benchmark.benchmark_search('Delantero con regate y desborde',{'$and':[{'plays_ST':True},{'dribbling':{'$gte':80}}]})
            self.assertTrue(result['vector']['candidates'])
            for side in ['vector','lexical']:
                for hit in result[side]['candidates']:
                    self.assertTrue(hit['metadata']['plays_ST'])
                    self.assertGreaterEqual(hit['metadata']['dribbling'],80)
            # Verificar la UI activa con esta muestra real, sin indexar 20 mil fichas.
            with patch('supplied_app.resources',return_value=(store,records,benchmark)):
                app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=60)
                next(c for c in app.checkbox if c.key=='supplied_enabled').check().run(timeout=60)
                next(s for s in app.selectbox if s.label=='Posición').select('ST')
                next(s for s in app.slider if s.label.startswith('Regate mínimo')).set_value(80)
                next(b for b in app.button if b.label=='Buscar en los CSV').click().run(timeout=60)
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                self.assertTrue(app.session_state.supplied_result['candidates'])
                self.assertEqual(len(app.metric),3)

    def test_app_starts_inactive_without_indexing(self):
        with patch('supplied_app.open_store') as factory:
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=60)
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox[0].value,'CSV del usuario · FIFA/EA FC')
            factory.assert_not_called()


if __name__=='__main__': unittest.main()
