# PERF — canonical managed graph read identity

**Status:** ACTIVE; PRIME design/implementation/delivery under the operator's frontend goal.
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
