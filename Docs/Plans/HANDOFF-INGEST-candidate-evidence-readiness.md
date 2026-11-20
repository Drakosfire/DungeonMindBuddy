# INGEST: surface candidate validation in readiness

**Status:** SETTLED — PR #1251 merged as `85b3949c5cb4fd6419767c7a6037e3002a20750e`; the candidate-validation response and readiness lease ended. The separate missing-source identity gap is tracked by `HANDOFF-INGEST-graph-candidate-source-status.md`.
**Base:** `origin/main@fc1daff4b7fc8f6ba7d35445dd22e9fca15f6d49`, refreshed after PR #1250 merged on 2026-10-16; #1250 changed only agent provider files and did not touch this lease.
**Branch:** `codex/ingest-evidence-readiness`.
**Checkout:** `/tmp/dmb-ingest-evidence-readiness`.
**Topology:** `parallel-independent` from open #1237 (Ingest local navigation), #1244 (candidate packaging reference repair), and #1235 (Worldbuilding source observation review). PR #1235 also edits the shared API `types.ts`; this lease deliberately avoids that file and keeps the small response shape local to the readiness model. The current write sets therefore do not overlap. The implementation only reads candidate validation artifacts; it does not modify extraction outputs. No live server, database, or corpus owner is introduced.

## Objective

Make Ingest readiness reflect the candidate validation report that belongs to the selected graph-ingest run. A candidate with unresolved evidence references must not appear to have “No blocking review items.” Show a compact, understandable validation state and counts, while retaining the candidate for inspection and leaving admission decisions to the existing server workflow.

The current retained Session 29 run proves the failure case: its manifest says `candidate_validation_ready` with no warnings, while the exact `candidate_validation_report.json` says `valid: true` and lists ten unresolved evidence-reference warnings. The server status adapter reads manifest status and health but omits the validation report; the UI readiness model only considers duplicate recaps, spelling audits, blocked extraction, and top-level errors.

## Contract and invariants

- The server reads only the candidate validation report named by the selected run manifest. Resolve the artifact path within the graph-memory repository, verify the report hash when supplied, and confirm its campaign/session and candidate identity match the selected run before using it.
- Missing, malformed, mismatched, or hash-invalid reports produce an explicit `unavailable` validation summary. They never silently become a clean/ready state.
- Return a compact typed summary: validation state, error count, warning count, and unresolved evidence-reference count. Do not return full source passages or raw reference identifiers through the readiness summary.
- Validation errors or unresolved references block “ready for review/admission” wording. Other warnings remain visible as attention requiring review. A clean report may say “candidate ready for review,” never “admitted” or “published.”
- Preserve existing non-mutating preview behavior. Do not add or alter any graph admission, save, rerun, extraction, publication, API write, or 5202/5204 behavior.
- Older runs lacking a trustworthy report must say validation is unavailable and direct the operator to inspect or rerun validation; do not infer success from `candidate_validation_ready` alone.

## Exclusive write set

- `Docs/Plans/HANDOFF-INGEST-candidate-evidence-readiness.md`
- `apps/live_control_server/services/recap_graph_preview_ingest.py`
- `tests/test_recap_graph_preview_validation_summary.py`
- `apps/live-control-ui/src/modules/ingestReadiness.ts`
- `apps/live-control-ui/src/modules/ingestReadiness.test.ts`

No extraction, packaging, route, Graph Review, corpus, database, lockfile, shared navigation, or runtime files are leased.

## Verification

- Unit tests cover clean validation, warnings, invalid reports, unresolved refs even when a legacy report incorrectly says valid, missing/malformed reports, wrong run identity, candidate/report hash mismatch, changed candidate bytes, and a missing candidate artifact on a candidate-ready run.
- Service status-adapter tests prove the graph-preview status payload includes the compact validation summary derived from the selected run’s exact report, and fails closed when its candidate or report is unavailable.
- UI tests prove the Attention and next-action copy cannot report “No blocking review items” or “candidate ready” when validation is invalid, unresolved, or unavailable.
- Run focused server/UI tests, affected typecheck, build where practical, and `git diff --check`.
- Do not mutate the retained candidate, corpus, database, or live service. The preserved Session 29 artifacts are read-only acceptance evidence; an end-to-end ingest/write remains a later authorized dogfood gate.

## Read-only retained-run check

The selected Session 29 run under `out/graph_memory/runs/longmont-c2/session-29/20261015T204654Z` was read through the new status adapter. Its manifest reports `candidate_validation_ready`; the referenced, hash-verified report contains zero errors, ten warnings, and ten unresolved evidence-reference warnings. The adapter returns `blocked`, `error_count: 0`, `warning_count: 10`, and `unresolved_evidence_reference_count: 10`. No run, corpus, database, or live service state was changed. This verifies the server summary against the real retained files; rendered live-UI acceptance is still pending deployment and review.

Focused verification on this branch: server unit tests pass (13); Ingest readiness tests pass (8); IngestionModule and MemoryIngestPage tests pass (70); both UI TypeScript projects pass; Ruff checks pass for the changed Python files; `git diff --check` passes. The whole service file is not Ruff-format clean at baseline, so it was not reformatted as that would create unrelated churn.
