# Manual legal review

Status: pending full R0–R5 generation. No new full-dev translation is available
for a baseline-versus-R5 review yet.

The evaluation runner exports 30 examples selected deterministically with seed 67:
source, R0, R5 and checks in `manual_review.md`; editable verdicts in
`manual_review.json`. The user reviews each example and sets `verdict=approved`
only after checking legal meaning. Approval of glossary entries is separate.

BLEU, chrF++, structure and entity checks do not replace this review.
