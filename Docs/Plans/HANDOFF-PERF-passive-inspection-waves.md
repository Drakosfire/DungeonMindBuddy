# PERF — preserve pending reads across passive recap inspection

**Status:** ACTIVE; PRIME owns this serial correction under the frontend-foundation goal.
**Base:** mainab584018b; branchcodex/passive-recap-inspection, existing buddy-context-loop checkout.
**Topology:** serial successor to1483; no open predecessor implementation PR.

## Verified cause and boundary

1483 canonical defaults are accepted but did not reduce live Ingest's two graph requests. Native request metadata shows recap-ingest POST beginning during graph registration/cookie bootstrap, followed by two identical graph bodies. Shared transport conservatively clears its read wave for every nonshared POST. The current recap inspect_status dispatch is read-only: routes/recap_ingest.py routes it to inspect_recap_ingest_status (documented read-only artifact probe) and inspect_recap_graph_preview_status (no file writes).

Treat only the current frontend inspection shape (POST exact /api/live/recap-ingest, operation inspect_status, valid campaign/session, optional slug/title, no other keys) as passive for invalidation. This exemption does not coalesce the inspection itself, add graph authentication to the historically unprotected probe, or change request/retry/response semantics. All process/reconciliation/materialization/generation, malformed or unknown operations/shapes and near-miss paths retain conservative mutation waves at dispatch and settlement. Keep the1482 authority, error and cancellation guarantees.

## Exclusive expected write lease / proof

- This handoff.
- apps/live-control-ui/src/api/liveApi.ts: passive inspection classification only.
- apps/live-control-ui/src/api/liveApi.readEfficiency.test.tsx: real wrapper read→inspect→read sharing and command/unknown-shape isolation.

No backend/schema/dependency/producer changes. Prior transport leases released; pausedRules candidates and active Ingest1235 observation review do not own this slice's active paths. Verify failing base reproduction, current owner cohort, tsc/build and independent exact-head review. Merge only after source approval, adopt established5202 assets atomically with old assets retained. Live gate: Ingest graph2→1, evidence/candidate remain1, no visible errors,17 protected state responses unchanged. Retain private native request traces; do not claim a broader history cleanup from this correction. Mutable1483/1482 handoff corrections settle after actual browser results.

Author evidence: passive inspect read-wave test fails on base and passes after classification.271 transport/recovery/provider/cache owner tests pass, including inspection settlement, unchanged unprotected inspection authentication, commands/unknown shapes and prior credential/cancellation/overlapping-write regressions. TypeScript/build pass. The live Ingest gate remains required after independent source review and merge.
