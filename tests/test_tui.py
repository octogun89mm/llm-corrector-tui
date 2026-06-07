import unittest

from llm_corrector.tui import wrap_buffer


class WrapBufferTest(unittest.TestCase):
    def test_preserves_blank_lines(self):
        self.assertEqual(wrap_buffer("one\n\ntwo", 20), ["one", "", "two"])

    def test_wraps_long_lines(self):
        self.assertEqual(wrap_buffer("abcdef", 3), ["abc", "def"])
