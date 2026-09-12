"""Navegación educativa sin importar ni inicializar el motor de recuperación."""
import builtins
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from exposition import standalone_html

ROOT = Path(__file__).resolve().parents[1]


class ExpositionTests(unittest.TestCase):
    def test_standalone_is_self_contained(self):
        html = standalone_html()
        for marker in ("/*__STYLES__*/", "/*__MODEL__*/", "/*__UI__*/"):
            self.assertNotIn(marker, html)
        self.assertNotIn('<script src=', html)
        self.assertNotIn('https://', html)
        self.assertIn('id="graphPlot"', html)

    def test_education_does_not_import_retrieval(self):
        original_import = builtins.__import__
        blocked = {'chromadb', 'vector_store', 'rag_pipeline', 'supplied_app', 'benchmark'}

        def guarded(name, *args, **kwargs):
            if name.split('.')[0] in blocked:
                raise AssertionError(f"La exposición importó {name}")
            return original_import(name, *args, **kwargs)

        app = AppTest.from_file(str(ROOT / 'app.py'))
        app.session_state.app_section = 'Exposición interactiva'
        with patch('builtins.__import__', side_effect=guarded):
            app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, 'Bases de datos vectoriales')
        self.assertEqual(len(app.selectbox), 0)

    def test_navigation_returns_to_inactive_search_and_preserves_evidence(self):
        app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=30)
        self.assertEqual(app.radio[0].value, 'Buscador')
        app.session_state.supplied_result = {'rerank': None, 'test_marker': 'conservado'}
        app.radio[0].set_value('Exposición interactiva').run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.supplied_result['test_marker'], 'conservado')
        app.button[0].click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.radio[0].value, 'Buscador')
        self.assertFalse(next(c for c in app.checkbox if c.key == 'supplied_enabled').value)
        self.assertEqual(app.session_state.supplied_result['test_marker'], 'conservado')


if __name__ == '__main__':
    unittest.main()
