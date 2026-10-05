# Decoding A/B

Status: pending full paired-dev generation. A one-record actual-model CPU smoke
has exercised all six candidates; it is not configuration-selection evidence.
No official generation configuration changed.

| Candidate | Changes relative to experiment | Status |
|---|---|---|
| A0 | Current configuration | Pending |
| A1 | A0: no_repeat_ngram_size=0 | Pending |
| A2 | A0: dynamic max_new_tokens from train p99 | Pending |
| A3 | A1 plus dynamic length | Pending |
| A4_lp1.0 | A3: length_penalty=1.0 | Pending |
| A4_lp1.2 | A3: length_penalty=1.2 | Pending |

Paired sample: all baseline E2/E3/E4 heuristic positives plus a fixed clean sample.
Every candidate receives identical texts, IDs and references; metrics include
sacreBLEU signatures, taxonomy rates and latency. Candidate selection rejects a
chrF++ decrease and requires lower combined E2/E3/E4 rates. Submission promotion
additionally requires full R0–R5 evidence and a declared runtime budget.

The generation wrapper records EOS and cap separately: a **forced EOS at the
token cap still counts as a cap hit**. Saved text alone cannot supply this signal.

Constrained beam search moved to custom generation code in transformers 5.x.
The offline pipeline consequently keeps constrained retry disabled and reports
it as unsupported in that environment; n-best reranking is available locally.
It never downloads remote generation code. Reference:
[Hugging Face generation documentation](https://huggingface.co/docs/transformers/main/en/main_classes/text_generation).
