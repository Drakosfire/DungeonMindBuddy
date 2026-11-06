# INGEST: audit normalized source-anchor receipts

Status: ACTIVE. Root adopts the confirmed evaluator-contract defect under the user's standardization and ingestion implementation authorization.

## Lane and topology

Branch `codex/ingest-normalized-anchor-audit`, stacked on PR #2130 at `e4233c8e0c6c2ddff3ba0126bbd9c7d3459fad82`. Merge/rebase #2130 first. Sibling PR #2131 owns recap wording and remains independent; conversation-loading PR #2132 owns unrelated paths. Root explicitly transfers the expected write lease for `src/ingestion_evaluation/evidence.py` from the completed implementation lane of #2130 to this bounded successor. No concurrent writer owns these paths. No merge/deployment authority.

## Evidence and invariant

Fresh Session 5 run `4a7c8fcb-6980-492a-b92d-5b90fa9b1912` completed. The original standard audit (`ebd2fafb7c17dcf8884d018e5636d2655c303c8451b16ff581057974f057e3c4`) incorrectly calls an allowed case-normalized anchor a coordinate mismatch. Source characters 503:577 equal retained `match_text` exactly; the model anchor differs only in initial capitalization. Independent owner-contract critique: `57961c6295078f886770a26d817ffef1ea1d38d94ef58104800a458910f62f4b`.

The owning anchor contract permits case, whitespace and selected punctuation normalization, while retaining exact source text and raw coordinates for highlighting. Independently check those raw coordinates/text and normalized correspondence using the owner's normalization primitive, not the owner's match verdict. Require each authored anchor to have a verified occurrence receipt. Report nonverbatim authored anchors separately; never alter the candidate or imply its authored string was byte-verbatim. Keep exact-unique canonical rebinding proofs unchanged.

## Exclusive expected writes

- `src/ingestion_evaluation/evidence.py`
- `tests/test_ingestion_evaluation_evidence.py`
- This handoff.

No product matching, quote guard, prompts, schemas, Gold, providers, source authority, database lifecycle or publication changes. No relaxed semantic evidence or alternate evidence producer.

## Validation and delivery

Exercise real owning normalized matches with synthetic case/whitespace/punctuation variants. Reject forged coordinates/text, altered words, missing receipts and wrong source frames; preserve exact-unique canonical-binding negative controls. Run the existing runner tests. Inspect the cumulative diff, obtain exact-head independent review, commit/push/open one PR. Preserve the original failed audit and capture pins. After review, qualify a new read-only retained-run audit with exact run IDs and historical conservation evidence; do not replay ingestion to repair an audit defect.
