# INGEST: surface candidate validation in readiness

**Status:** ACTIVE — authorized by the persistent Ingest-first goal.
**Base:** `origin/main@8f54acee7ffe980a5a00573eed03009895a05384`, freshly cloned from current `main` on 2026-10-16.
**Branch:** `codex/ingest-evidence-readiness`.
**Checkout:** `/tmp/dmb-ingest-evidence-readiness`.
**Topology:** `parallel-independent` from open #1237 (Ingest local navigation), #1244 (candidate packaging reference repair), and #1235 (Worldbuilding source observation review). Their current write sets do not overlap this lease. The implementation only reads candidate validation artifacts; it does not modify extraction outputs. No live server, database, or corpus owner is introduced.

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
- `tests/test_live_recap_ingest_graph_preview_api.py`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/modules/ingestReadiness.ts`
- `apps/live-control-ui/src/modules/ingestReadiness.test.ts`

No extraction, packaging, route, Graph Review, corpus, database, lockfile, shared navigation, or runtime files are leased.

## Verification

- Unit tests cover clean validation, warnings, invalid reports, unresolved refs even when a legacy report incorrectly says valid, missing/malformed reports, wrong run identity, and hash mismatch.
- API-level test proves the current status response includes the compact validation summary derived from the selected run’s exact report.
- UI tests prove the Attention and next-action copy cannot report “No blocking review items” or “candidate ready” when validation is invalid, unresolved, or unavailable.
- Run focused server/UI tests, affected typecheck, build where practical, and `git diff --check`.
- Do not mutate the retained candidate, corpus, database, or live service. The preserved Session 29 artifacts are read-only acceptance evidence; an end-to-end ingest/write remains a later authorized dogfood gate.
