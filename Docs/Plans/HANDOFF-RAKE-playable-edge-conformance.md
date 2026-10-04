# RAKE: Playable effect target conformance

Status: ACTIVE. PRIME explicitly transferred the unstarted RAKE lease to the bounded implementation worker on 2026-10-04.

## Authority and lane

Base: Buddy main `271e15177b5675c686b32f6ea1cfcd6fa25735a6`.
Branch: `codex/prime-playable-edge-conformance`; isolated checkout `/tmp/prime-playable-edge-conformance`.
Topology: parallel-independent, one implementation PR. Open #887/#869/#844/#826 and other listed research/document PRs do not own these paths. The first-card implementation remains blocked until this repair is independently reviewed by PRIME.

## Invariant and exact write lease

Reject repeated target IDs within either v2 Option activates or suppresses list, matching the existing Python source parser. Keep distinct targets and repeated targets in different Options valid. Existing cross-list overlap and missing-target rejection remain unchanged.

1. `Docs/Plans/HANDOFF-RAKE-playable-edge-conformance.md`
2. `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts`
3. `apps/live-control-ui/src/tiptap/playable/playableEdgeConformance.test.ts`
4. `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.test.ts` (only if needed)
5. `tests/fixtures/playable_edge_conformance.json`
6. `tests/test_playable_edge_conformance.py`

No server parser implementation, API, schema, editor host, Plan Page, global styles, corpus, provider or runtime changes. Persisted-manifest duplicate edge tuples are a separate future Run admission risk, excluded here.

## Verification and handback

Use synthetic shared Markdown fixtures through editor import/index/serialization/re-import and the existing Python parser. Assert exact IDs, membership, order and edges for valid v1/v2; prove duplicate activates/suppresses, cross-list overlap and dangling target rejection. A newly discovered grammar gap beyond this invariant must be reported without extending runtime scope.

No ports, databases, services, private corpus or model calls. Node dependencies may be linked locally from the existing isolated test fixture; Python verification uses an existing environment. Logs remain in `/tmp`. Inspect the cumulative diff, commit/push the intended paths, open one PR and return exact head plus evidence to PRIME. PRIME alone reviews and merges.
