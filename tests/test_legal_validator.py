import json
from pathlib import Path
import unittest
from src.vinai_baseline.pipeline.types import Candidate
from src.vinai_baseline.pipeline.md_parser import parse_document
from src.vinai_baseline.pipeline.validator import entities, normalize_number, validate, citation_variants


class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings={"kept_names":[],"vi_density_limit":0.1,"dangling_pattern":r"(?:/ND|of the|\band)\s*$","short_ratio":0.1,"short_ratio_by_kind":{},"consecutive_ngram_sizes":[1,2,3,4],"consecutive_repeat_min":3,"sentence_retention_ratio":0.5}
    def checks(self,source,text,**kw):
        unit=parse_document(source).units[0]; candidate=Candidate(text,**kw)
        return {c["check"]:c["severity"] for c in validate(unit,candidate,self.settings)}
    def test_numbers_are_direction_aware(self):
        self.assertEqual(normalize_number("1.000.000","vi"),normalize_number("1,000,000","en"))
        self.assertEqual(normalize_number("1,5","vi"),normalize_number("1.5","en"))
        self.assertNotEqual(normalize_number("1.000","en"),normalize_number("1.000","vi"))
    def test_dates_identifiers_references_normalize(self):
        source="Điều 5 Khoản 2 Điểm a, ngày 5 tháng 3 năm 2020, Nghị định 12/2020/NĐ-CP: 1.000.000 và 1,5."
        target="Article 5 Clause 2 Point a, March 5, 2020, Decree 12/2020/ND-CP: 1,000,000 and 1.5."
        self.assertEqual(entities(source,"vi"),entities(target,"en"))
        for value in ["5 March 2020","05/03/2020"]:
            self.assertEqual(entities("ngày 5 tháng 3 năm 2020","vi"),entities(value,"en"))
    def test_correct_entities_not_errors_missing_wrong_are_errors(self):
        self.assertNotIn("identifiers",self.checks("Nghị định 12/2020/NĐ-CP.","Decree 12/2020/ND-CP."))
        self.assertEqual(self.checks("Theo Điều 5, số 100.","Under Article 6, number 200.")["numbers"],"error")
        self.assertEqual(self.checks("Ngày 5 tháng 3 năm 2020.","March 6, 2020.")["dates"],"error")
    def test_empty_language_cap_and_dangling(self):
        self.assertEqual(self.checks("Nội dung.","")["empty"],"error")
        self.assertEqual(self.checks("Nội dung.","Nội dung tiếng Việt có dấu.")["wrong_language"],"error")
        self.assertEqual(self.checks("Nội dung.","Text",gen_finished_by_eos=True,reached_token_cap=True)["token_cutoff"],"error")
        self.assertEqual(self.checks("Nội dung.","of the")["dangling"],"warning")
        self.assertNotIn("token_cutoff",self.checks("Nội dung.","Text.",gen_finished_by_eos=True,reached_token_cap=False))
    def test_short_repetition_sentence_and_placeholder_signals(self):
        self.assertIn("short",self.checks(" ".join(["nguồn"]*20),"text"))
        self.assertIn("repetition",self.checks("Nguồn.","the law the law the law."))
        self.assertNotIn("repetition",self.checks("law law law", "law law law"))
        self.assertIn("missing_sentences",self.checks("A; B; C; D;", "Content."))
        self.assertEqual(self.checks("**Nội dung**", "Content")["placeholder"],"error")
    def test_written_number_is_warning_and_citations_only_report(self):
        self.assertEqual(self.checks("Có 2 người.","There are two people.")["numbers"],"warning")
        self.assertEqual(citation_variants("Article 5; Art. 5"),{"article:5":["Art. 5","Article 5"]})
    def test_ambiguous_locale_format_is_warning_not_confirmed_integer_error(self):
        self.assertEqual(self.checks("Số tiền 1,000 đồng.","Amount 1,000 dong.")["numbers"],"warning")


if __name__=="__main__": unittest.main()
