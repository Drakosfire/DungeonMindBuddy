# PERF — preserve pending reads across passive recap inspection

**Status:** COMPLETE; source/runtime leases released. The full frontend-foundation goal remains ACTIVE.
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


## Accepted delivery

PR1484 merged0bc5cae8e6b5d4acfb34efed1d2cfcb8169292d5. Architecture Cycle1 source-approved exact67f0f9c9e61949f2292f29c5bc028bc4c79e812f; independent255-test cohort passes. Author271-test/tsc/build evidence remains separate. Chatreviewreceipt only; no remote check runs were configured.

Current5202 UI index59df42d48db54e2e816a0bb053ac40e43a54d66bd723480eaac08c3bdbbac36e on unchangedPID17085/API8000, prior assets retained. Same six-second warm/uncontrolled-cache Ingest sample now has11 resource entries,3,282,895 API body bytes, one managed graph request, one session-evidence request and one candidate request. Prior1483 sample had5,434,977 bytes/two graph requests; original assessment had5,892,126 bytes/two each graph/evidence/candidate. No visible Ingest alert. All17 protected JSON responses match the fresh before baseline. No provider request, source edit, extraction, publication or API restart. Probes/tabs removed; exact request traces and after-sample are private existing experiment evidence. No target-laptop CPU or latency distribution is claimed.

This closes the1483 Ingest live-count gate. Serializer normalization remains accepted; the actual remaining duplicate cause was passive POST invalidation during graph bootstrap. Pending-wave sharing and current inspection semantics are now proven together. History demand/recovery scheduling, bounded lists/payloads, surface/tool code loading, user+Agent Rules lookup and native Combat remain outstanding.
