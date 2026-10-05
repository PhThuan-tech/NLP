# Legal translation inference: assumptions and acceptance status

Updated 2026-10-05. Implementation follows the supplied SPEC v1.0. No frozen
dataset, adapter, training configuration, or official decoding file is modified.

## Repository discovery (SPEC section 14)

| # | Finding and evidence |
|---|---|
| 1 | `src/vinai_baseline/config.py:22` selects VinAI Translate v2 for each direction. `offline_training_assets/models/vinai-translate-vi2en-v2/config.json:44` declares 1,024 position embeddings. Language token handling is in `src/vinai_baseline/language.py:7`. |
| 2 | `modelAI/*en2vi*094600380389Z_result.zip` and `modelAI/*vi2en*013129101193Z_result.zip` contain `best_model/adapter_model.safetensors`. Loading uses `src/vinai_baseline/inference.py:load_inference_model`, with base identity/revision validation. EN→VI reverse checks are possible but optional and disabled. |
| 3 | `src/vinai_baseline/inference.py:translate_chunks` sorts by token length, runs deterministic generation, and reorders outputs. `submission/configs/vi2en.json` is the official configuration. Its beams=4, length penalty=1.1, ngram=3 differ from the saved training evaluation (beams=2, penalty=1.0, ngram=3). These baselines must not be mixed. |
| 4 | `src/vinai_baseline/service.py:SubmissionHandler` accepts POST `/translate`, `/translate/en2vi`, `/translate/vi2en`, raw UTF-8 Markdown or the existing JSON body; returns raw UTF-8 Markdown. `submission/translate.sh` keeps its three arguments. No route or payload changes. |
| 5 | `artifacts/processed_clean_semantic_seed67_v3/segments_dev_vi2en.jsonl`: 2,783 aligned segments, grouped by `sample_id`, not one original Markdown file per document. Structural checks operate on exact segment strings. Aggregated document scores use `chunk_index` order and explicitly synthetic separators; they do not represent recovered original document layouts. |
| 6 | The adjacent `segments_train_vi2en.jsonl` has 27,756 aligned paragraph/segment pairs. It supplies length calibration and pending glossary evidence only. No new split/filtering. |
| 7 | `src/vinai_baseline/metrics.py:TranslationMetricSuite` uses sacreBLEU/chrF++ (`word_order=2`). Evaluation reports also record metric signatures and version. |
| 8 | User confirmed submission GPU/RAM/time limits are not yet available. `time_budget_per_doc=null`; deployment acceptance remains pending. The local venv has CPU-only PyTorch and no CUDA. |
| 9 | User confirmed they review glossary CSV. All mined entries start `pending`; only explicit `approved` rows participate in inference. |
| 10 | Local `.venv`: Python 3.13.5, PyTorch 2.14.1+cpu, transformers 5.18.0, PEFT 0.21.2. Existing Docker pins differ; reports record installed versions. Parser uses the standard library; no additional dependency is needed. |

## Resolved conflicts and limits

- Saved validation outputs are a **snapshot baseline**, not a fresh rerun of the
  current document service. They have no generated token IDs. EOS and cap causes
  cannot be recovered from those strings. M0 cause probes and a fresh R0 run are
  provided for Kaggle; no cause is asserted before those measurements.
- The suggested ngram=0 configuration is a candidate, not an official change.
  New decoding has a separate feature flag and needs matching A/B evidence.
- Retry selection follows the strict rule in section 9.5: lower penalty, no new
  error, and at least one original error fixed. Warning-only terminology retries
  may generate candidates but cannot win on warnings alone. Both are reported.
- Batched related units remain distinct model inputs. Concatenating them without
  reliable output alignment would violate coverage; no guessed alignment is used.
- Fewer than 200 markup units or ten `/ND` examples are reported as insufficient
  evidence; examples are never manufactured to meet a count.
- Runtime budget checks occur at stage boundaries. A model generation already in
  progress cannot be safely interrupted by this synchronous service. Retries are
  skipped when budget is exhausted; the first translation always runs. If a new
  layer fails or exceeds budget, the legacy path is used and the fallback logged.
- Partial inline markup lost by `strip_spans` is reported as a structural failure;
  it does not silently count as 100% preservation. Protected code/URLs must survive
  or the original unit is retained with an error.
- Glossary co-occurrence is candidate evidence, not word alignment or legal
  endorsement. Multilingual entity equivalence checks are heuristics; dates,
  canonical identifiers, and number formatting have explicit normalization tests.
- Clinical or legal translation correctness requires user review. Metric gains
  and entity preservation do not establish correctness.

## Acceptance gates

Local tests and dev round-trip checks can be completed on CPU. Actual placeholder
survival, EOS cause probes, decoding A/B, R0–R5 model evaluations, Docker GPU smoke,
and declared time-budget checks require execution on the deployment environment.
Reports label these measurements `pending` until generated. The submission service
keeps the legacy route by default. No model or metric result is fabricated.
