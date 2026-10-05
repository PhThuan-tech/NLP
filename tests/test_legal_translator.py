from types import SimpleNamespace
import unittest
from src.vinai_baseline.config import ExperimentConfig
from src.vinai_baseline.pipeline.config import PipelineConfig
from src.vinai_baseline.pipeline.translator import ModelTranslator


class GenerationProvenanceTests(unittest.TestCase):
    def test_eos_at_cap_is_not_a_clean_stop_and_order_is_retained(self):
        import torch
        class Tokenizer:
            pad_token_id=1
            def __call__(self,text,**kw):
                if isinstance(text,str): return {"input_ids":list(range(len(text.split())+2))}
                return {"input_ids":torch.tensor([[7,8] for _ in text])}
            def batch_decode(self,sequences,**kw): return ["Content." for _ in sequences]
        class Model:
            generation_config=SimpleNamespace(eos_token_id=2)
            def to(self,device): return self
            def eval(self): return self
            def generate(self,**kw): return SimpleNamespace(sequences=torch.tensor([[9,4,4,4,4,4,4,4,2]]*len(kw["input_ids"])))
        experiment=ExperimentConfig.from_json("submission/configs/vi2en.json")
        config=PipelineConfig.load("submission/configs/inference_pipeline.json",environment=False)
        translator=ModelTranslator(Tokenizer(),Model(),experiment,config,"cpu")
        results=translator.generate_many(["longer input source","short"],overrides={"max_new_tokens":8})
        self.assertEqual(len(results),2)
        for result in results:
            self.assertTrue(result[0].gen_finished_by_eos)
            self.assertTrue(result[0].reached_token_cap)
            self.assertEqual(result[0].generated_tokens,8)
        cached=translator.generate("short",overrides={"max_new_tokens":8},stage="retry")
        self.assertTrue(cached[0].provenance["cache_hit"])
        self.assertEqual(cached[0].stage,"retry")
        official=translator.generate("source")
        self.assertFalse(official[0].reached_token_cap)
        self.assertEqual(official[0].max_new_tokens,511)
    def test_new_decoding_requires_evidence_or_experimental_mode(self):
        config=PipelineConfig.load("submission/configs/inference_pipeline.json",environment=False)
        config.values["features"]["new_decoding"]=True
        config.values["features"]["enabled"]=True
        with self.assertRaisesRegex(ValueError,"promotion"): config.validate()


if __name__=="__main__": unittest.main()
