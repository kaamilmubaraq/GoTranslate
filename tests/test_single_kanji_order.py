import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


LIBS = Path(__file__).resolve().parents[1] / "libraries"
if str(LIBS) not in sys.path:
    sys.path.insert(0, str(LIBS))

if "fugashi" not in sys.modules:
    sys.modules["fugashi"] = SimpleNamespace(Tagger=object, fugashi=SimpleNamespace(Node=object))
if "jaconv" not in sys.modules:
    sys.modules["jaconv"] = SimpleNamespace(kata2hira=lambda s: s)
if "jamdict" not in sys.modules:
    sys.modules["jamdict"] = SimpleNamespace(Jamdict=object)

from japanseanalyzer import analyze_text


class FakeWord:
    def __init__(self, surface: str, lemma: str, kana: str, pos1: str = "名詞", pos2: str = ""):
        self.surface = surface
        self.feature = SimpleNamespace(
            pos1=pos1,
            pos2=pos2,
            lemma=lemma,
            kana=kana,
        )


class SingleKanjiOrderingTest(unittest.TestCase):
    def test_defined_single_kanji_is_sorted_before_no_definition_entries(self):
        fake_tokens = [
            FakeWord("勉強", "勉強", "ベンキョウ"),
            FakeWord("山", "山", "ヤマ"),
            FakeWord("謎語", "謎語", "ナゾゴ"),
        ]

        def fake_lookup(_jmd, query: str, max_senses: int = 2):
            if query == "勉強":
                return (["study"], 10)
            if query == "山":
                return (["mountain"], 5)
            return ([], 999)

        with patch("japanseanalyzer.get_tagger", return_value=lambda _text: fake_tokens), \
             patch("japanseanalyzer.get_jamdict", return_value=object()), \
             patch("japanseanalyzer.lookup_entry_data", side_effect=fake_lookup), \
             patch("japanseanalyzer._get_jlpt_level", return_value=None):
            result = analyze_text("dummy text", normalize_text=False)

        self.assertEqual([entry["word"] for entry in result], ["勉強", "山", "謎語"])
        self.assertEqual(result[0]["english"], ["study"])
        self.assertEqual(result[1]["english"], ["mountain"])
        self.assertEqual(result[2]["english"], [])


if __name__ == "__main__":
    unittest.main()
