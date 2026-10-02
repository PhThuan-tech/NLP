"""Conservative degeneration checks, not a certification of translation accuracy."""
from collections import Counter
import re
import unicodedata

QUALITY_GATE_VERSION = 2


def _tokens(text):
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def _repeat_fraction(tokens):
    triples = [tuple(tokens[i:i + 3]) for i in range(len(tokens) - 2)]
    return 1 - len(set(triples)) / len(triples) if triples else 0.0


def quality_report(predictions, references, direction, segment_ids=None):
    if not predictions or len(predictions) != len(references):
        raise ValueError("Quality gate requires equal nonempty predictions/references")
    if direction not in {"en2vi", "vi2en"}:
        raise ValueError("Unknown translation direction")
    ids = segment_ids if segment_ids is not None else list(range(len(predictions)))
    if len(ids) != len(predictions):
        raise ValueError("Quality gate segment IDs do not match predictions")
    failures = []
    warnings = []
    for identifier, prediction, reference in zip(ids, predictions, references, strict=True):
        tokens, ref_tokens = _tokens(prediction), _tokens(reference)
        reasons = []
        warning_reasons = []
        ratio = len(tokens) / max(1, len(ref_tokens))
        repeat = _repeat_fraction(tokens)
        dominance = max(Counter(tokens).values(), default=0) / max(1, len(tokens))
        if not tokens:
            reasons.append("empty_output")
        if len(tokens) >= 12 and repeat > max(0.30, _repeat_fraction(ref_tokens) + 0.20):
            reasons.append("excessive_trigram_repetition")
        # A short legal clause can legitimately repeat words such as "Điều".
        # Dominance is only meaningful once the output is long enough.
        if len(tokens) >= 20 and dominance > 0.25:
            reasons.append("dominant_token")
        if len(ref_tokens) >= 8:
            if ratio > 3.0:
                reasons.append("excessive_length_ratio")
            elif ratio < 0.02:
                reasons.append("near_empty_relative_to_reference")
            elif ratio < 0.25:
                # Under-translation is a real quality issue, but unlike token
                # collapse it is exactly the behaviour fine-tuning may repair.
                # Surface it prominently without blocking a new training run.
                warning_reasons.append("under_translation")
        letters = [c for c in unicodedata.normalize("NFC", prediction) if c.isalpha()]
        # Accent absence is a heuristic only, restricted to longer EN->VI outputs.
        marked = sum(c in "đĐ" or any(unicodedata.combining(d)
                     for d in unicodedata.normalize("NFD", c)) for c in letters)
        if direction == "en2vi" and len(letters) >= 40 and marked / len(letters) < 0.01:
            reasons.append("almost_no_vietnamese_marks")
        if reasons:
            failures.append({"segment_id": identifier, "reasons": reasons,
                             "length_ratio": round(ratio, 4),
                             "repeat_fraction": round(repeat, 4),
                             "dominant_fraction": round(dominance, 4),
                             "prediction": prediction})
        if warning_reasons:
            warnings.append({"segment_id": identifier, "reasons": warning_reasons,
                             "length_ratio": round(ratio, 4),
                             "prediction": prediction})
    # Fail on any obvious degeneration. Inspect report; never silently drop bad rows.
    return {"gate_version": QUALITY_GATE_VERSION,
            "status": "failed" if failures else "passed",
            "evaluated_records": len(predictions), "failed_records": len(failures),
            "failed_rate": 100 * len(failures) / len(predictions), "failures": failures,
            "warning_records": len(warnings),
            "warning_rate": 100 * len(warnings) / len(predictions), "warnings": warnings,
            "note": ("Hard failures detect obvious generation degeneration. Warnings such as "
                     "under-translation remain quality problems but do not block fine-tuning; "
                     "a pass is not proof of translation accuracy.")}
