# INGEST: prepare blinded semantic review inputs

Status ACTIVE. Study steward adopts independently reviewed projection design
(`blinded-packet-boundary-independent-review-v1.json`, SHA
`9f657dcc86dfcb955b6f0f7b655fe1b6aa38cdf571adc78163691797a9ad6bcd`).

Branch `codex/ingest-blinded-review-packet`, current isolated checkout, stacked on
#2160 exact `12529c0da6a3289a59e2f9a648f496b59eb77a94`. Merge evaluator chain
#2154 → #2155 → #2156 → #2160 → this child. Product #2164 is a separate lane.
No merge authority, providers, network, ports, databases or primary-state writes.

Outcome: one offline evaluator command replaces ad hoc future review packet
projection. Copy exact candidate bytes and every recorded response text into
neutral JSON artifacts; exclude operational envelopes, retain a private original
pointer mapping, and expose minimal run/revision/candidate binding usable by the
existing assessment assembler. Public references remain direct strict pointers;
no review rewriting or second assessment validator. Source/Gold/neutral contracts
are separately pinned reviewer inputs, unchanged by this command.

Write lease: `src/ingestion_evaluation/blinding.py`,
`scripts/evaluate_ingestion.py`, `tests/test_ingestion_evaluation_blinding.py`,
`Docs/Guides/ingestion-study-assessments.md`, and this handoff. No other active
lane edits these paths. Review producer/consumer invariants, source receipt hashes,
all-attempt preservation, author/host provenance, conflict/idempotence, and absence
of backend imports. Reject unexpected candidate operational fields; never redact
model-authored strings. Response count/length and possible self-disclosure remain
visible. File projection is not an access-control sandbox.

Validation: synthetic sentinel and tamper cases, existing assembler integration,
mechanical retained-run calibration (no semantic rereview/H1 rescore), cumulative
base→head inspection, independent subagent review, commit/push/PR. H2 remains
undispatched until all prospective gates are satisfied.

## Verification

65 focused tests pass (packet boundary, existing assembly, common assessment),
independently reproduced in working-diff review. Mechanical retained-run
calibration preserves all 12 response records and exact candidate bytes; 552
remapped references resolve to identical values, all judgment values and report
counts/limitations are unchanged, and original sealed review SHA remains pinned.
No semantic rereview or H1 rescoring occurred. Calibration first asserted whole
phase equality; that failed because provenance correctly points to the derivative
review. The final check explicitly verifies all semantic/reference values and
phase fields while separately recording the changed provenance pins.

Calibration receipt: `packet-mechanical-calibration-v1/verification.json`, SHA
`33cc0e6f02030674e3f76c9fee1eb8d8ca0862a1e509074172967e0ba8be4280`,
under the retained study review protocol evidence directory. Exact-head review
and delivery follow this working-diff check; no execution activation is implied.
