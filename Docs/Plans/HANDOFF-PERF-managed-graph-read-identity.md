# PERF — canonical managed graph read identity

**Status:** SOURCE ACCEPTED / MERGED; serializer adopted. Ingest count-reduction gate UNMET; follow-on semantic read classification is required. Source/runtime leases released.
**Base:** mainc3900ece56c2e92f0d359b195a85f3ccb689e269; branchcodex/canonical-managed-graph-reads in the existing buddy-context-loop checkout.
**Topology:** serial successor to accepted1482; no other implementation PR in this read-efficiency lane.

## Invariant and critique

The current managed graph contract has exactly schema, managedWorldId, optional revisionPin and optional queryText. The server's strict ManagedWorldGraphProjectionRequest defaults both optional fields to null. The app provider supplies nulls; the Worldbuilding publication producer omits them. Pending transport sharing uses exact bytes, so equivalent current-contract reads can miss sharing. Serialize current-contract defaults consistently at the owning API wrapper, preserving World, schema, explicit empty strings, distinct pins/queries and unexpected runtime fields (so server extra=forbid still rejects them). Do not generalize equivalence across endpoints or change the server contract, authority, settled cache, revision or error handling. Do not change producer lifecycle in this slice.

## Exclusive write lease and acceptance

- This handoff.
- apps/live-control-ui/src/api/liveApi.ts: postManagedWorldGraphProjection serializer only.
- apps/live-control-ui/src/api/liveApi.readEfficiency.test.tsx: omitted/null concurrency, scope/pin/query separation and unknown-field/error preservation proof.

Current open pausedRules763–765 do not own an active transport lease; Ingest1235 owns source observations, not this wrapper. Re-anchor exact open work before edits/review/merge. No dependency, backend, schema, data or provider changes. Preserve the accepted access/wave/cancellation invariants from1482; rerun its owner cohort and typecheck/build. Independently review exact cumulative diff, merge under PRIME authority, adopt only established5202 UI assets with old assets retained and current before/after17-state snapshots. Compare the Ingest graph requests; a reduction is a measurement gate, not assumed from helper tests. Source serializer acceptance alone is not the full frontend goal. Release leases and record actual evidence after acceptance.

Author evidence: the omitted/null wrapper test fails on the base with two fetches and passes after canonical serialization with one. The261-test transport/recovery/provider/cache cohort passes; TypeScript and production build pass. Unknown runtime fields are retained for strict server rejection; explicit empty query strings and distinct pins/Worlds remain distinct. Independent review and the Ingest rendered-count gate remain pending.


PR1483 merged f11029dbf0d35725454015544a7074c367513743 after Architecture Cycle1 source approval of221eaca50683b3608b5e1a8f8edc72beb54cc6c1; independent245-test cohort passes. Source accepted, actual Ingest measurement remains two graph requests (5,434,977 API body bytes), so this is not represented as live duplicate removal. Current UI index6bf22d9af150ee8f35e0228146fda99c4f5327b40e472eb4016c5ae4eeb4d6a8 on unchanged5202PID17085/API8000. All17 protected JSON responses unchanged, no provider submission/source editing. Temporary probes/tabs removed.

Native request traces change the next action: both managed graph requests already have the same four canonical fields; a recap inspect_status POST begins between acquisition registration and cookie-bootstrap dispatch. Treating every nonshared POST as a mutation discards the first pending wave. Routepost_recap_ingest dispatches inspect_status to read-only inspect_recap_ingest_status and inspect_recap_graph_preview_status. A successor must explicitly exempt this current read operation from mutation invalidation while keeping commands conservative and unshared; this serializer PR does not expand operation classification.
