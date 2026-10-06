# Offline model placement

The final package must replace the placeholder directories with two complete,
merged Hugging Face model directories:

```text
submission/models/en2vi/config.json
submission/models/en2vi/model*.safetensors
submission/models/en2vi/tokenizer.json
submission/models/vi2en/config.json
submission/models/vi2en/model*.safetensors
submission/models/vi2en/tokenizer.json
```

Do not place model weights in Git. Use `src.vinai_baseline.merge_lora` after
each direction has passed the frozen evaluation, then pass both output
directories to `scripts/package_submission.ps1`.
