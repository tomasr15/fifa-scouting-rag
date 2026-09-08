import os
import unittest
from unittest.mock import patch
from rag_pipeline import LLMConfig


class ConfigTests(unittest.TestCase):
    def test_dotenv_and_environment_precedence(self):
        with patch('rag_pipeline.dotenv_values', return_value={'OPENAI_API_KEY': 'file-test', 'OPENAI_MODEL': 'file-model'}):
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(LLMConfig.from_env('openai').api_key, 'file-test')
                self.assertEqual(LLMConfig.from_env('openai').model, 'file-model')
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'env-test'}, clear=True):
                self.assertEqual(LLMConfig.from_env('openai').api_key, 'env-test')

    def test_edits_are_read_without_mutating_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch('rag_pipeline.dotenv_values', side_effect=[{'OPENAI_API_KEY': 'first'}, {'OPENAI_API_KEY': 'second'}]):
                self.assertEqual(LLMConfig.from_env('openai').api_key, 'first')
                self.assertEqual(LLMConfig.from_env('openai').api_key, 'second')
                self.assertNotIn('OPENAI_API_KEY', os.environ)
            self.assertEqual(LLMConfig.from_env('ollama').api_key, 'ollama')
