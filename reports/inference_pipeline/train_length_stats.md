# Train token length calibration

Read-only calibration of frozen VI→EN train, using the actual local tokenizer.

```json
{
  "records": 27756,
  "source_percentiles": {
    "0.5": 211.0,
    "0.9": 254.0,
    "0.95": 264.0,
    "0.99": 297.4500000000007
  },
  "token_ratio_p99": 1.2978418717224696,
  "target_minus_source_p99": 55,
  "word_ratio_p01": 0.5422303183906225,
  "english_vi_density_p99": 0.0013394956052987655,
  "by_kind_word_ratio_p01": {
    "point": {
      "records": 484,
      "threshold": 0.46073124406457744
    },
    "clause": {
      "records": 570,
      "threshold": 0.4395238095238095
    },
    "list_item": {
      "records": 44,
      "threshold": 0.5010665818490246
    },
    "title": {
      "records": 587,
      "threshold": 0.45243396226415095
    },
    "article_heading": {
      "records": 261,
      "threshold": 0.45454545454545453
    },
    "preamble": {
      "records": 11,
      "threshold": 0.5061156235069278
    }
  },
  "train_sha256": "24119e6b9043252ab39eae9b749400983d2fad54802ed951562434c14443d95d",
  "tokenizer_sha256": "cdbd2277deee13a943b702c0131ea9034d00c2288f332ee0c5fea520b07ea936",
  "stored_length_matches": 27756,
  "calibration_method": "local fast tokenizer encode_batch with special tokens; p95 target, half retry, p99 target/source linear slope and residual margin"
}
```

Target budget: 264; hard budget: 1024; retry budget: 132.

Dynamic generation is disabled until A/B. Thresholds come from train, not public test.
Kind-specific length ratios use only single-unit aligned train pairs.
