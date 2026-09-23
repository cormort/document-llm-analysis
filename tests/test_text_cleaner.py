import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.text_cleaner import clean_rag_content, clean_text_for_display


class TestTextCleaner(unittest.TestCase):
    def test_strips_thought_tags(self):
        self.assertEqual(clean_rag_content("<think>推理</think>答案"), "答案")

    def test_strips_control_chars_and_collapses_newlines(self):
        self.assertEqual(clean_rag_content("a\x00\x07b\n\n\n\nc"), "ab\n\nc")

    def test_display_keeps_newlines_and_tabs(self):
        self.assertEqual(clean_text_for_display("a\tb\n\x01c"), "a\tb\nc")

    def test_empty(self):
        self.assertEqual(clean_rag_content(""), "")
        self.assertEqual(clean_text_for_display(None), "")


if __name__ == "__main__":
    unittest.main()
