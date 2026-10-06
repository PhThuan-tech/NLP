import os
from unittest.mock import patch
import unittest
import tempfile
from src.vinai_baseline.service import TranslationRuntime


class ServiceCompatibilityTests(unittest.TestCase):
    def test_disabled_pipeline_preserves_legacy_runtime(self):
        runtime=TranslationRuntime()
        with patch.dict(os.environ,{"VINAI_PIPELINE_CONFIG":"submission/configs/inference_pipeline.json"}), patch.object(runtime,"_load"), patch("src.vinai_baseline.service.split_markdown_document",return_value=[object()]), patch("src.vinai_baseline.service.translate_chunks",return_value=(["Translated"],{"chunks":1})), patch("src.vinai_baseline.service.assemble_document",return_value="Translated\n"):
            runtime._config=object()
            output,report=runtime.translate("Source\n","vi2en")
        self.assertEqual(output,"Translated\n"); self.assertEqual(report["chunks"],1); self.assertIsNone(runtime._pipeline)
    def test_setup_failure_falls_back_and_writes_reports(self):
        from pathlib import Path
        runtime=TranslationRuntime()
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ,{"VINAI_PIPELINE_CONFIG":"missing.json","VINAI_PIPELINE_REPORT_DIR":temporary}), patch.object(runtime,"_load"), patch("src.vinai_baseline.service.split_markdown_document",return_value=[object()]), patch("src.vinai_baseline.service.translate_chunks",return_value=(["Translated"],{"chunks":1})), patch("src.vinai_baseline.service.assemble_document",return_value="Translated\n"):
            runtime._config=object(); output,report=runtime.translate("Source\n","vi2en")
            self.assertEqual(output,"Translated\n"); self.assertTrue(report["fallback"])
            self.assertEqual(len(list(Path(temporary).glob("*.report.json"))),1)
            self.assertEqual(len(list(Path(temporary).glob("*.report.md"))),1)


if __name__=="__main__": unittest.main()
