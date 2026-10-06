# Full fixed-dev ablation

Status: pending Kaggle GPU execution. CPU smoke results verify code execution only.

| Run | Parser | Chunker | New decoding | Glossary | Retry | Full-dev result |
|---|---|---|---|---|---|---|
| R0 | off | off | off | off | off | Pending |
| R1 | on | off | off | off | off | Pending |
| R2 | on | on | off | off | off | Pending |
| R3 | on | on | selected A/B | off | off | Pending |
| R4 | on | on | selected A/B | approved only | off | Pending |
| R5 | on | on | selected A/B | approved only | on | Pending |

Run notebook `05_inference_pipeline_kaggle.ipynb`. Every row receives the same
2,783 fixed dev records. No public/private-test records enter selection. Reports
contain BLEU/chrF++ with signatures, E1–E7 rates, coverage, structure, retries,
per-record and aggregate document latency, environment, and artifact hashes.

There are no approved entries yet, so R4 cannot demonstrate glossary benefit.
Document metric aggregation uses exact segment order with synthetic double
newlines; original document Markdown layouts are unavailable in the frozen data.

Submission promotion remains pending until full-dev metrics, user review of the
30 fixed random examples, exact-model deployment GPU smoke, and a declared runtime
budget are validated. Adapter evidence is not automatically valid for merged weights.
Inline placeholders also require an exact-candidate real-dev survival report;
the frozen corpus currently lacks the required paired markup units.
