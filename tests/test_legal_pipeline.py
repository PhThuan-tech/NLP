from pathlib import Path
import tempfile
import unittest
from src.vinai_baseline.pipeline.config import PipelineConfig
from src.vinai_baseline.pipeline.runtime import LegalTranslationPipeline
from src.vinai_baseline.pipeline.report import write_report
from src.vinai_baseline.pipeline.types import Candidate
from tests.test_legal_chunker import WordTokenizer


class PipelineTests(unittest.TestCase):
    def config(self):
        config=PipelineConfig.load("submission/configs/inference_pipeline.json",environment=False)
        config.values["runtime"]["structured_logs"]=False
        return config
    def translator(self,text=None,raise_error=False):
        class Translator:
            tokenizer=WordTokenizer()
            def generate_many(self,texts,**kwargs):
                if raise_error: raise RuntimeError("model exception")
                return [[Candidate(t if text is None else text,gen_finished_by_eos=True,reached_token_cap=False)] for t in texts]
        return Translator()
    def test_structure_roundtrip_coverage_reports(self):
        config=self.config(); config.values["features"]["retry"]=False
        source="# Title\r\n\r\n- **bold** and `code`  \r\n| A | B |\r\n| --- | --- |\r\n"
        output,report=LegalTranslationPipeline(self.translator(),config).translate(source,direction="vi2en")
        self.assertEqual(output,source); self.assertTrue(report["invariants"]["unit_coverage"])
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"doc.report.json"; write_report(path,report)
            self.assertTrue(path.is_file()); self.assertTrue(path.with_suffix(".md").is_file())
    def test_empty_output_keeps_source_with_error(self):
        config=self.config(); config.values["features"]["retry"]=False
        output,report=LegalTranslationPipeline(self.translator(""),config).translate("- Nội dung\n",direction="vi2en")
        self.assertEqual(output,"- Nội dung\n"); self.assertEqual(report["summary"]["SOURCE_KEPT"],1)
        self.assertEqual(report["units"][0]["final"]["penalty"],config.values["validator"]["weights"]["error"])
    def test_new_layer_failure_falls_back_without_empty_output(self):
        output,report=LegalTranslationPipeline(self.translator(raise_error=True),self.config()).translate("Nguồn",direction="vi2en",legacy=lambda text:("Baseline",{"chunks":1}))
        self.assertEqual(output,"Baseline"); self.assertTrue(report["fallback"])
    def test_budget_skips_retry_then_falls_back_after_first(self):
        config=self.config(); config.values["runtime"]["time_budget_per_doc"]=1e-12
        output,report=LegalTranslationPipeline(self.translator(""),config).translate("Nguồn",direction="vi2en",legacy=lambda text:(text,{"chunks":1}))
        self.assertTrue(report["fallback"]); self.assertEqual(report["fallback_reason"],"TimeoutError")
    def test_protected_only_unit_does_not_call_model(self):
        config=self.config()
        output,report=LegalTranslationPipeline(self.translator(raise_error=True),config).translate("`immutable_code`\r\n",direction="vi2en")
        self.assertEqual(output,"`immutable_code`\r\n"); self.assertEqual(report["summary"]["SOURCE_KEPT"],0)
    def test_generated_markdown_cannot_create_new_structure(self):
        config=self.config(); config.values["features"]["retry"]=False
        for translated in ("# invented heading", "- invented bullet", "1. invented list"):
            output,report=LegalTranslationPipeline(self.translator(translated),config).translate("Original text",direction="vi2en")
            self.assertTrue(report["invariants"]["structure_preserved"])
            self.assertIn("\\",output)


if __name__=="__main__": unittest.main()
