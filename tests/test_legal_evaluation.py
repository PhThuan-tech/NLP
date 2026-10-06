from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
import random
from src.vinai_baseline.config import ExperimentConfig
from src.vinai_baseline.pipeline.config import PipelineConfig
from src.vinai_baseline.pipeline.evaluation import validate_selection, placeholder_run, score
from src.vinai_baseline.pipeline.promotion import behavior_hash, file_hash, model_identity, verify_promotion
from src.vinai_baseline.pipeline.report import code_version
from scripts.finalize_inference_promotion import finalize


class EvaluationGateTests(unittest.TestCase):
    def test_smoke_selection_cannot_promote_full_run_or_mismatched_config(self):
        config=PipelineConfig.load("submission/configs/inference_pipeline.json",environment=False)
        experiment=ExperimentConfig.from_json("submission/configs/vi2en.json")
        decision={"status":"selected","model_identity":None,"dev_sha256":"fixed","base_generation":asdict(experiment.generation),"code_sha256":"code","behavior_sha256":behavior_hash(config),"partial":True}
        validate_selection(decision,config,experiment,"fixed","code",allow_partial=True)
        with self.assertRaisesRegex(ValueError,"partial"): validate_selection(decision,config,experiment,"fixed","code",allow_partial=False)
        decision["partial"]=False; config.values["translator"]["dynamic_slope"]+=1
        with self.assertRaisesRegex(ValueError,"identity"): validate_selection(decision,config,experiment,"fixed","code",allow_partial=False)
    def test_missing_markup_is_not_fabricated_survival(self):
        config=PipelineConfig.load("submission/configs/inference_pipeline.json",environment=False)
        with tempfile.TemporaryDirectory() as temporary:
            report=placeholder_run([{"source":"Plain text","segment_id":"a"}],config,None,None,None,None,Path(temporary))
            self.assertEqual(report["status"],"insufficient_dev_markup"); self.assertIsNone(report["selected"])
            self.assertTrue(all(r["survival_rate"] is None for r in report["results"]))
    def test_metrics_record_signatures_and_document_ordering(self):
        rows=[{"sample_id":"doc","chunk_index":1},{"sample_id":"doc","chunk_index":0}]
        result=score(["second segment","first segment"],["second segment","first segment"],rows)
        self.assertEqual(result["chrF++"],100); self.assertIn("version:",result["signatures"]["chrF++"])
        self.assertEqual(result["documents"]["doc"]["segments"],2)
    def test_disabled_selected_config_can_be_reviewed_before_activation(self):
        config=PipelineConfig.load("submission/configs/inference_pipeline.json",environment=False)
        config.values["features"]["new_decoding"]=True
        config.validate()


class PromotionTests(unittest.TestCase):
    def fixture(self, root):
        config=PipelineConfig.load("submission/configs/inference_pipeline.json",environment=False)
        config.values["runtime"]["time_budget_per_doc"]=60
        config.values["features"]["inline_placeholders"]=False
        experiment=ExperimentConfig.from_json("submission/configs/vi2en.json")
        model=root/"model"; model.mkdir(); (model/"adapter_model.safetensors").write_bytes(b"fixture")
        evaluation=root/"evaluation"; evaluation.mkdir()
        expected={"model_identity":model_identity(experiment,model),"generation":asdict(experiment.generation),"behavior_sha256":behavior_hash(config),"code_sha256":code_version(),"glossary_sha256":file_hash(config.resource(config.values["glossary"]["file"])),"dev_sha256":config.values["evaluation"]["fixed_dev_sha256"]}
        ids=[f"record-{i}" for i in range(32)]
        indices=random.Random(config.values["seed"]).sample(range(32),config.values["evaluation"]["manual_review_records"])
        review={"units":[{"segment_id":ids[i],"verdict":"approved"} for i in indices]}
        summaries=[{"name":f"R{i}","records":32,"code_changed_during_run":False,"round_trip_rate":100,"structure_preservation_rate":100,"unit_coverage_rate":100,"metrics":{"BLEU":50,"chrF++":70},"max_document_seconds":2} for i in range(6)]
        evidence={**expected,"status":"pending","records":32}
        for name,value in (("promotion_evidence",evidence),("ablation",summaries),("subset",{"limit":None,"record_ids":ids}),("manual_review",review)):
            (evaluation/f"{name}.json").write_text(json.dumps(value),encoding="utf-8")
        smoke={"environment":{"device":"cuda:0"},"invariants":{"structure_preserved":True,"unit_coverage":True},"summary":{"units":2,"SOURCE_KEPT":0},"versions":{k:v for k,v in expected.items() if k not in {"generation","dev_sha256"}},"generation":expected["generation"],"runtime":{"stages_seconds":{"total":2}},"fallback":False}
        deployment=root/"deployment.json"; deployment.write_text(json.dumps(smoke),encoding="utf-8")
        return evaluation,config,experiment,model,deployment,smoke

    def test_exact_reviewed_evidence_promotes_and_remains_verifiable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); evaluation,config,experiment,model,deployment,_=self.fixture(root)
            result=finalize(evaluation,config,experiment,model,deployment,root/"approved")
            self.assertEqual(result["status"],"passed")
            approved=PipelineConfig.load(root/"approved/approved_pipeline.json",environment=False)
            self.assertTrue(approved.values["features"]["enabled"])
            self.assertFalse(approved.values["evaluation"]["experimental"])
            verify_promotion(approved,experiment,model)
            (model/"adapter_model.safetensors").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError,"does not match"): verify_promotion(approved,experiment,model)

    def test_inline_mode_requires_measured_real_dev_survival(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); evaluation,config,experiment,model,deployment,smoke=self.fixture(root)
            config.values["features"]["inline_placeholders"]=True
            evidence_path=evaluation/"promotion_evidence.json"
            evidence=json.loads(evidence_path.read_text()); evidence["behavior_sha256"]=behavior_hash(config)
            evidence_path.write_text(json.dumps(evidence)); smoke["versions"]["behavior_sha256"]=behavior_hash(config)
            deployment.write_text(json.dumps(smoke))
            with self.assertRaisesRegex(ValueError,"survival evidence"): finalize(evaluation,config,experiment,model,deployment,root/"absent")
            ph=root/"placeholder.json"; ph.write_text(json.dumps({"status":"insufficient_dev_markup","available":0,"results":[],"selected":None}))
            with self.assertRaisesRegex(ValueError,"incomplete"): finalize(evaluation,config,experiment,model,deployment,root/"insufficient",ph)

    def test_deployment_mismatch_and_partial_or_unreviewed_results_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); evaluation,config,experiment,model,deployment,smoke=self.fixture(root)
            for name,change in (("generation",lambda r:r["generation"].update(num_beams=99)),("behavior",lambda r:r["versions"].update(behavior_sha256="changed")),("cpu",lambda r:r["environment"].update(device="cpu")),("budget",lambda r:r["runtime"]["stages_seconds"].update(total=61))):
                with self.subTest(name=name):
                    altered=json.loads(json.dumps(smoke)); change(altered)
                    deployment.write_text(json.dumps(altered),encoding="utf-8")
                    with self.assertRaises(ValueError): finalize(evaluation,config,experiment,model,deployment,root/name)
                    self.assertFalse((root/name).exists())
            deployment.write_text(json.dumps(smoke),encoding="utf-8")
            subset_path=evaluation/"subset.json"; subset=json.loads(subset_path.read_text()); subset["limit"]=32; subset_path.write_text(json.dumps(subset))
            with self.assertRaisesRegex(ValueError,"Partial"): finalize(evaluation,config,experiment,model,deployment,root/"partial")
            subset["limit"]=None; subset_path.write_text(json.dumps(subset))
            review_path=evaluation/"manual_review.json"; review=json.loads(review_path.read_text()); review["units"][0]["verdict"]="pending"; review_path.write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError,"approval"): finalize(evaluation,config,experiment,model,deployment,root/"unreviewed")


if __name__=="__main__": unittest.main()
