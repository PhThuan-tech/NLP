import unittest
from src.vinai_baseline.pipeline.chunker import split_unit, ChunkingError, protected_spans


class WordTokenizer:
    def __call__(self,text,**kw): return {"input_ids":text.split()}


class ChunkerTests(unittest.TestCase):
    def test_atomic_references_dates_numbers_and_glossary(self):
        text="Căn cứ Điều 5 Khoản 2 Điểm a; mức 1.000.000 đồng, ngày 5 tháng 3 năm 2020; Bộ Y tế quy định."
        pieces=split_unit(text,WordTokenizer(),budget=8,hard_budget=20,phrases=["Bộ Y tế"])
        self.assertEqual("".join(p.separator_before+p.text for p in pieces),text)
        for atom in ["Điều 5 Khoản 2 Điểm a","1.000.000","5 tháng 3 năm 2020","Bộ Y tế"]:
            self.assertTrue(any(atom in p.text for p in pieces),atom)
    def test_oversize_atomic_span_raises_never_truncates(self):
        with self.assertRaises(ChunkingError): split_unit("(a b c d e f)",WordTokenizer(),budget=2,hard_budget=4)
    def test_whitespace_and_unit_coverage(self):
        text="one two;\r\nthree four five.  six seven"
        pieces=split_unit(text,WordTokenizer(),budget=3,hard_budget=8)
        self.assertEqual("".join(p.separator_before+p.text for p in pieces),text)
    def test_abbreviation_not_sentence_boundary(self):
        self.assertTrue(any("TP."=="TP." and a<=4<=b for a,b in protected_spans("Tại TP. Hồ Chí Minh")))


if __name__=="__main__": unittest.main()
