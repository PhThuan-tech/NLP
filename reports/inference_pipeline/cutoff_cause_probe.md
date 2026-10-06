# VI2EN cutoff cause probe

Measured on 2026-10-05 with the immutable saved adapter and offline base on CPU.
Ten deliberately selected old predictions ending `/ND`; this is not full-dev evaluation.

| Run | Change | BLEU | chrF++ | E2 % | E3 % | E4 % | EOS before cap | Seconds/unit |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A0 | ngram3 baseline | 21.0670 | 41.9001 | 60.0 | 100.0 | 0.0 | 10/10 | 17.833 |
| A1 | only ngram3 to zero | 57.2895 | 72.9127 | 0.0 | 0.0 | 0.0 | 10/10 | 24.403 |

## Per-case termination evidence

| Segment | A0 tokens | A1 tokens | A0 EOS/cap | A1 EOS/cap |
|---|---:|---:|---|---|
| `Bat_dong_san/2::segment-0000::vi2en` | 70 | 395 | True/False | True/False |
| `Bat_dong_san/2::segment-0030::vi2en` | 108 | 181 | True/False | True/False |
| `Bat_dong_san/81::segment-0000::vi2en` | 192 | 290 | True/False | True/False |
| `Bat_dong_san/9::segment-0024::vi2en` | 182 | 185 | True/False | True/False |
| `Bat_dong_san/9::segment-0041::vi2en` | 236 | 254 | True/False | True/False |
| `Bat_dong_san/9::segment-0067::vi2en` | 259 | 339 | True/False | True/False |
| `Dich_vu_phap_ly/64::segment-0000::vi2en` | 73 | 303 | True/False | True/False |
| `Quyen_dan_su/197::segment-0002::vi2en` | 197 | 284 | True/False | True/False |
| `Quyen_dan_su/284::segment-0000::vi2en` | 70 | 176 | True/False | True/False |
| `Quyen_dan_su/54::segment-0011::vi2en` | 49 | 201 | True/False | True/False |

## Interpretation

All baseline outputs ended with EOS before the 448-new-token cap. The paired change
removed E2/E3/E4 heuristic cutoff signals on these ten cases. This supports ngram
sensitivity in this subset; it does not establish a cause for every short output.
A1 still has one E1 language signal, one E6 entity signal and four E5 structure
signals. Disabling ngram constraints is a candidate requiring fixed-dev A/B and
full R0?R5; it is not an official submission setting.

Saved-evaluation generation: beams=2, length_penalty=1.0, max_new_tokens=448.
The service baseline uses beams=4 and length_penalty=1.1; compare those separately.
Full metadata, signatures, model hash, historical code hash and endings:
[`cutoff_cause_probe.json`](cutoff_cause_probe.json).
Raw paired JSONLs remain locally under `evaluation/causes_cpu/`.
