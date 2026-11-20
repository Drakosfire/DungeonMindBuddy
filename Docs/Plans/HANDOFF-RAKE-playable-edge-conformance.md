# RAKE: Playable effect target conformance

Status: SETTLED. PR #908 merged at `e7b1464af6474e64a0f36c8a2fc57927b85db190` from exact reviewed head `fb866cd707ffc622b6be053822b0ffb03e0901b7`; the RAKE implementation lease is closed.

## Authority and lane

Authorization base: Buddy main `271e15177b5675c686b32f6ea1cfcd6fa25735a6`.
Publication base after re-anchor/rebase: `9cce6aaefced5f4429eb9e01b0bb4c8158fa229c`. The intervening authority settlements are disjoint from this five-path cumulative change.
Branch: `codex/prime-playable-edge-conformance`; isolated checkout `/tmp/prime-playable-edge-conformance`.
Topology: parallel-independent, one implementation PR. Open #887/#869/#844/#826 and other listed research/document PRs did not own these paths. At dispatch, the first-card implementation remained blocked pending this independent review. PRIME accepted and merged #908, then activated the separate DEMO card handoff at the merge commit.

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

## Review evidence

The shared fixture contains seven cases: valid Scene-first v1; distinct multiple v2 targets; reuse of a target across different Options; duplicate activates; duplicate suppresses; cross-list overlap; dangling target. Three accepted fixtures serialize byte-for-byte to the original shared source, then reopen with the same identity, membership, document order and effects. Python checks those exact bytes against explicit membership expectations. Its v2 arrays are intentionally ID-sorted and do not assert document order; the UI owns the document-order projection.

Before repair: the new UI suite had four failures (both duplicate source cases and both direct attribute validations), five passes. The unchanged Python source parser passed all seven cases. After the one-line uniqueness guard: UI identity/index/conformance suites pass 53/53; Python passes 7/7; Python lint passes. Invalid source cases return BLOCKED from the owning UI index. No tests were skipped or weakened. Logs: `/tmp/playable-edge-before.log`, `/tmp/playable-edge-after.log`, `/tmp/playable-edge-roundtrip.log`, `/tmp/playable-edge-python.log`.

This bounded packet proves these effect-target cases, not complete grammar equivalence, persisted-manifest validation, Run admission or card implementation. The optional existing index test path was not needed; the cumulative change used five of the six leased paths. PRIME's independent review accepted the exact head and merged PR #908 at `e7b1464af6474e64a0f36c8a2fc57927b85db190`. Its lease is closed. The successor card projection has its own ACTIVE DEMO handoff and does not inherit parser/test write authority.
