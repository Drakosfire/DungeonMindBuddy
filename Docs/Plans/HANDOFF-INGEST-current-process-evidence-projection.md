# HANDOFF — INGEST: project the acknowledged Process run into Evidence

**Status:** ACTIVE under the user-authorized Ingest-first goal and PRIME direction.
**Base:** fetched `origin/main@f467503ff3ba3f159ffe8897606d7372fdbe90a0`.
**Branch:** `codex/ingest-current-run-evidence`.
**Topology:** parallel-independent with open draft PR #1235. Its 10 changed files are confined to Graph Review/source-observation APIs and UI; none overlap this lease, and this Evidence projection does not depend on that review feature. PRIME owns independent review and runtime delivery; no merge or 5202 change is authorized here.

## Mission

When Process returns an acknowledged result for the selected campaign/session,
keep that exact result visible in the Evidence panel and graph status. A stale or
older `inspect_status` response must not erase, downgrade, or replace the result
from the operation the user just completed. Preserve request-generation fencing
across target changes, including A→B→A, and preserve existing failure and source
recovery behavior.

## Observed failure

The single authorized Session 29 Process attempt returned success and created
run `5dc9751f-fdda-46a8-88b3-fedf2551e8c2`. The Process UI reported the graph-
enriched recap ready for Graph Review, but the same page's Evidence & details
showed “Not run”, “Graph extraction: pending”, and “No ingestion result yet.”
The durable candidate preview is preview-only; no writes were proposed or
published. No additional Process/provider request is needed to reproduce this
projection mismatch.

## Invariants

- The acknowledged Process response is the authority for the current visible
  run result until a newer operation for the same selected target replaces it.
- Read-only status hydration may update source-file proof, but cannot overwrite
  an acknowledged Process result with an older or weaker response.
- Responses remain bound to the exact selected target and draft/request
  generation. A late response from A cannot affect B or a later A selection.
- Do not synthesize run IDs, candidate counts, statuses, model names, or token
  usage from unrelated status data. Render only evidence present in the
  response/trace.
- Preserve failed-run messaging, source conflict/reconciliation recovery, and
  the existing Process → Graph Review workflow.
- No API/schema/backend changes, source/candidate/corpus/database writes,
  graph admission/publication, additional provider calls, or runtime/server
  changes.

## Exclusive write lease

- `Docs/Plans/HANDOFF-INGEST-current-process-evidence-projection.md`
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`

Stop and return for a new lease if a shared component, API contract, server
registry, persistent run store, or any other path is required.

## Re-anchoring and coordination

This slice follows merged Ingest predecessors:

- #1259 at `70c894a25ab64a0b08dd2e7a4f293f5e262eff4b` — local navigation and
  evidence cleanup.
- #1266 at `7cd86c3a3fc875e0994ac53cbe5515bff43b27df` — retained-candidate
  source status.
- #1276 at `448e88d9006b19cfb607d4ac5afde14d6d44d856` — graph-enriched recap
  primary view.
- #1324 at `2b284ff96dea8bd42cf1e3dd6f3a647ab0a4f4f5` — truthful processing
  status.
- #1383 at `1c2df51b4b087d87c282e46e94e934eb029f1f84` — exact OpenRouter model
  pin.

The currently open Ingest PR #1235 changes `GraphReviewWorkbenchModule`,
`GraphReviewExactRunProjection`, Graph Review API/type/tests, and its own
handoff; none overlap this lease. No other open Ingest implementation PR was
found in the current GitHub scan.

## Verification

- `IngestionModule` now retains the last acknowledged operation result behind
  the exact selected-target identity and draft epoch. Evidence and graph
  projection prefer that result over a weaker read-only inspection; current
  file proof and source-recovery guidance still come from the newest
  selected-target inspection. Explicit source-unverified state continues to
  drive the overall status badge and disable Graph Review; the graph card keeps
  showing the exact status reported for the preview. Process, graph-preview
  build, materialization, and reconciliation are acknowledged operations;
  prior-source status inspection is not.
- Added a regression test that fails before this projection fix: Process returns
  a candidate-ready run, then a later `inspect_status` says graph missing. The
  graph status and result panel remain attached to the acknowledged run.
  Existing target-transition, A→B→A operation-fencing, and source-unverified
  status tests remain in the same suite.
- `npm test -- --run src/modules/IngestionModule.test.tsx --reporter=dot` —
  79/79 passed. Existing test-run `act(...)` warnings were emitted by unrelated
  tests.
- `npm run typecheck` — passed.
- `npm run build` — passed; Vite reported the existing large-chunk advisory.
- `git diff --check` — passed.
- Inspect the exact cumulative `origin/main`→head diff before commit and PR.
- Do not invoke Process, provider/model calls, review mutations, graph
  admission/publication, or server/runtime actions during implementation or
  verification. PRIME owns any later 5202 delivery.

## Evidence limit

This UI projection repair does not establish that the extracted facts faithfully
represent the recap. The exact run's model/stage ledger and candidate graph
remain available for a separate read-only gold-fidelity assessment. Candidate
preview counts alone are not a content-quality acceptance.
