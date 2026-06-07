import unittest

from llm_corrector.llama import clean_model_output


class CleanModelOutputTest(unittest.TestCase):
    def test_strips_wrapping_quotes(self):
        self.assertEqual(clean_model_output('"hello there"'), "hello there")

    def test_keeps_inner_quotes(self):
        self.assertEqual(clean_model_output('say "hello" there'), 'say "hello" there')
