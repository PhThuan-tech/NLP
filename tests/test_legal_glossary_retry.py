import csv
import json
from pathlib import Path
import tempfile
import unittest
from src.vinai_baseline.pipeline.glossary import Glossary
from src.vinai_baseline.pipeline.retry import choose, should_retry, retry_unit
from src.vinai_baseline.pipeline.md_parser import parse_document
from src.vinai_baseline.pipeline.config import PipelineConfig
from src.vinai_baseline.pipeline.types import Candidate
from tests.test_legal_chunker import WordTokenizer


class GlossaryRetryTests(unittest.TestCase):
    def test_approved_only_longest_domain_direction_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"terms.csv"
            fields="id src_phrase direction domain preferred accepted_variants match_mode priority evidence status".split()
            rows=[("full","Bộ Y tế","vi2en","general","Ministry of Health","[]","exact_phrase",1,"review","approved"),("partial","y tế","vi2en","general","health","[]","exact_phrase",2,"review","approved"),("pending","Bộ Xây dựng","vi2en","general","Ministry of Construction","[]","exact_phrase",1,"train","pending"),("domain","thuốc","vi2en","medical","medicine","[]","exact_phrase",1,"review","approved")]
            with path.open("w",encoding="utf-8",newline="") as f:
                writer=csv.writer(f); writer.writerow(fields); writer.writerows(rows)
            settings={"domains":{},"domain_min_score":None,"domain_margin":None}
            glossary=Glossary(path,settings)
            hits=glossary.match("Bộ Y tế và Bộ Xây dựng, thuốc, y tếx",direction="vi2en",domain="general")
            self.assertEqual([h["id"] for h in hits],["full"])
            self.assertEqual(glossary.match("Bộ Y tế",direction="en2vi",domain="general"),[])
    def test_selection_tie_and_new_error_cannot_win(self):
        weights={"error":3,"warning":1,"info":0}
        first=Candidate("Bad.",checks=[{"check":"numbers","severity":"error"}])
        worse=Candidate("Wrong language.",checks=[{"check":"wrong_language","severity":"error"}])
        better=Candidate("Fixed.",checks=[])
        self.assertIs(choose(first,[worse],weights),first); self.assertIs(choose(first,[better],weights),better)
        warning=Candidate("Terminology.",checks=[{"check":"terminology","severity":"warning"}])
        self.assertIs(choose(warning,[better],weights),warning)
    def test_retry_one_round_and_fixed_entity(self):
        config=PipelineConfig.load("submission/configs/inference_pipeline.json",environment=False)
        unit=parse_document("Có 100 người.").units[0]
        first=Candidate("There are 200 people.",gen_finished_by_eos=True,reached_token_cap=False,checks=[{"check":"numbers","severity":"error"}])
        unit.translations=[first]
        class Translator:
            tokenizer=WordTokenizer(); calls=0
            def generate_many(self,texts,**kwargs):
                self.calls+=1
                return [[Candidate("There are 100 people.","retry","split_smaller",True,False)] for t in texts]
        translator=Translator(); retry_unit(unit,translator,config,direction="vi2en")
        self.assertEqual(translator.calls,1); self.assertEqual(unit.status,"RETRIED_FIXED")
        self.assertEqual(len(unit.translations),2)


if __name__=="__main__": unittest.main()
