"""Opt-in CPU integration using cached VinAI tokenizer and a tiny random mBART.

Set RUN_VINAI_INTEGRATION=1 and HF_HUB_OFFLINE=1. No pretrained model download,
no full training, and no assumptions about the quality of a random model.
"""
import os
import tempfile
import unittest


@unittest.skipUnless(os.environ.get("RUN_VINAI_INTEGRATION") == "1", "Opt-in cached tokenizer integration")
class NativeLanguageTests(unittest.TestCase):
    def test_real_target_tokens_collation_lora_and_reload(self):
        import torch
        from transformers import MBartConfig, MBartForConditionalGeneration, AutoTokenizer
        from peft import LoraConfig, TaskType, get_peft_model
        from src.vinai_baseline.language import configure_tokenizer, configure_model
        from src.vinai_baseline.data import DynamicSeq2SeqCollator
        torch.set_num_threads(2)
        tokenizer = AutoTokenizer.from_pretrained("vinai/vinai-translate-en2vi-v2",
            revision="1e47495b5dac16097b1d9e7b4133c27e1f40504f", local_files_only=True)
        for direction, source, target in [("en2vi", "en_XX", "vi_VN"), ("vi2en", "vi_VN", "en_XX")]:
            configure_tokenizer(tokenizer, direction)
            self.assertEqual(tokenizer("Test")["input_ids"][-1], tokenizer.convert_tokens_to_ids(source))
            self.assertEqual(tokenizer(text_target="Xin chào")["input_ids"][-1], tokenizer.convert_tokens_to_ids(target))
            config = MBartConfig(vocab_size=len(tokenizer), d_model=16,
                encoder_layers=1, decoder_layers=1, encoder_attention_heads=2,
                decoder_attention_heads=2, encoder_ffn_dim=32, decoder_ffn_dim=32,
                max_position_embeddings=64, pad_token_id=tokenizer.pad_token_id)
            model = configure_model(MBartForConditionalGeneration(config), tokenizer, direction)
            model = get_peft_model(model, LoraConfig(task_type=TaskType.SEQ_2_SEQ_LM,
                r=2, lora_alpha=4, target_modules=["q_proj", "v_proj"]))
            collator = DynamicSeq2SeqCollator(tokenizer, model=model,
                max_source_length=64, max_target_length=64, truncate=False)
            batch = collator([{"source_text": "Hello", "target_text": "Xin chào bạn hôm nay thế nào?"},
                              {"source_text": "This is a longer sentence", "target_text": "Chào"}])
            self.assertTrue(torch.all(batch["decoder_input_ids"][:, 0] == tokenizer.convert_tokens_to_ids(target)))
            # Label smoothing removes labels before forward; shapes must still match.
            labels = batch.pop("labels")
            logits = model(**batch).logits
            self.assertEqual(logits.shape[:2], labels.shape)
            self.assertTrue(torch.isfinite(logits).all())
            logits.mean().backward()
            self.assertTrue(any(p.grad is not None for p in model.parameters() if p.requires_grad))
            model.eval()
            with torch.inference_mode():
                generated = model.generate(**tokenizer("Hello", return_tensors="pt"), max_new_tokens=2)
            self.assertEqual(generated[0, 0].item(), tokenizer.convert_tokens_to_ids(target))
            with tempfile.TemporaryDirectory() as directory:
                tokenizer.save_pretrained(directory)
                loaded = configure_tokenizer(AutoTokenizer.from_pretrained(directory), direction)
                self.assertEqual(loaded(text_target="Xin chào")["input_ids"][-1], tokenizer.convert_tokens_to_ids(target))
