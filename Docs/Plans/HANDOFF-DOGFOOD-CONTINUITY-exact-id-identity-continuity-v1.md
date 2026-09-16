# HANDOFF — DOGFOOD-CONTINUITY exact-id identity continuity v1

**Created:** 2026-09-15  
**Status:** DONE — MERGED as PR #725 @ `28f4fb432c71553f2479e02fee851951e20c7ec9` (rebased head `0fd7f8c1ba8ec1a82799ead7fb1005a11506a6ea`); stewardship drain continues at #726  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-id-identity-continuity-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Original design authority base:** `main@68577114b3c8ec7e06bc0b0a8d382143fdc570ec`  
**Recovery authority:** `HANDOFF-STEWARDSHIP-drain-dogfood-continuity-pr-queue.md`  
**Activation gate:** `satisfied — #724 MERGED @ 45c98d425bb61746564f151c2b5adccaa1591898; activation base main@45c98d425bb61746564f151c2b5adccaa1591898`  
**PR topology:** `serial`  
**PR authorization:** `ACTIVE — rebase/update/review existing PR #725 only; do not open another implementation PR`  
**PR title:** `DOGFOOD-CONTINUITY: confirm existing objects by exact durable id`

**Activation facts:**
- Predecessor #724 merge SHA: `45c98d425bb61746564f151c2b5adccaa1591898`
- Rebased #724 head: `4a5f50da`
- Activation base: `main@45c98d425bb61746564f151c2b5adccaa1591898`
- Formal review cycles on #724 integration head: 1

> This slice was already implemented and dogfooded before the accidental PR fan-out
> was recognized. Its implementation is preserved; its lane is now intentionally
> parked. BLOCKED means no active §4 lease and no further implementation work until
> the recovery queue reaches #725.

## §1 Mission and merge-ready invariant

**Mission:** When a candidate reuses an exact same-kind durable object id already
present on the sealed parent head, identity resolution confirms that object
(`resolved_existing`) even if surface labels drifted or cross-kind aliases share
the label — so governed materialization does not CREATE_NEW into an occupied id.

**Merge-ready invariant:**

```text
proposed_node_id / candidate_id equals parent same-kind object_id
  → resolved_existing (before label match / cross-kind block)
label drift alone never invents CREATE_NEW for that durable id
wrong-kind exact id does not force confirm
```

## §2 Context and recovery sequencing

| Field | Content |
|---|---|
| Dogfood predecessor | C1S2 `parent_binding_mismatch` on `loc:rivers-edge-pub`; later combined runs also exercised exact-id class continuity. |
| Existing transport | PR #725, parked while this handoff is BLOCKED. |
| PR topology | `serial`. |
| Activation gate | #724 merged + synced; steward re-anchors and activates this handoff. |
| Action at activation | Rebase existing #725 onto exact current `main`; review the resulting exact head; merge only after formal approval. |
| Named successor | #726, which remains BLOCKED until #725 merges. |
| Explicit non-goals | Label-fuzzy identity redesign; cross-kind forced confirm; acceptance-harness repair; opening another PR. |

Synthetic/cherry-picked combined dogfood heads are diagnostic evidence only. They do not replace review of #725 rebased onto actual `main`.

## §3 Observable paths

| Path | Required behavior | Owning boundary |
|---|---|---|
| exact same-kind durable id, label drift | `resolved_existing` before label/alias matching | mutation identity context |
| exact durable id occupied by wrong kind | fail closed / blocked; never CREATE_NEW into occupied id | mutation identity context |
| free durable id | existing create/new policy unchanged | mutation identity context |

## §4 Write lease — prospective while BLOCKED

```text
apps/live_control_server/models/world_graph_mutation_context.py
tests/test_exact_id_identity_continuity.py
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-id-identity-continuity-v1.md
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-exact-id-identity-continuity-v1.md
```

No path above is actively leased while this handoff is BLOCKED.

**Serialization with #726:** #726 also touches
`apps/live_control_server/models/world_graph_mutation_context.py`. Recovery order
is strict: merge #725 first; then activate/rebase #726 onto the resulting real
`main`. No concurrent dual-write.

## §5–§6 Non-goals / stop signs

Do not broaden into fuzzy matching or graph repair. Do not run implementation work
while this handoff is BLOCKED. Do not open a new repair PR from a dogfood finding;
return it to the steward.

## §7 Evidence

```bash
uv run pytest tests/test_exact_id_identity_continuity.py tests/test_pc_identity_normalization.py tests/test_cutover_native_governed_write.py -q
uv run ruff check apps/live_control_server/models/world_graph_mutation_context.py tests/test_exact_id_identity_continuity.py
git diff --check
git diff --name-only <activation-dispatch-base>...HEAD
```

The final paid current-corpus acceptance rerun occurs once after #722–#726 are
merged onto actual `main`.

## §8 Review handback

Record exact rebased base/head, formal review cycle, evidence provenance, actual
changed paths, and confirmation that no additional PR was opened.

## §9 Acceptance rubric

- [ ] Handoff was activated only after #724 merge/sync/re-anchor.
- [ ] Existing #725 was rebased onto real current `main`.
- [ ] Exact same-kind durable-id continuity holds; wrong-kind occupancy still blocks.
- [ ] #726 remains parked until #725 merges.
- [ ] No successor/repair PR was opened from this lane.
