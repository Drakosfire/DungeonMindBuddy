# HANDOFF — DOGFOOD-CONTINUITY exact-edge-id continuity v1

**Created:** 2026-09-15  
**Status:** DONE — MERGED as PR #726 @ `23a00dfd1d7eca788e9a3db7875e7443ac83a7dc` (rebased head `a42ced95c82892751b1d22cfbdc64e30d1d03d0a`); final pristine acceptance pending  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Original design authority base:** `main@68577114b3c8ec7e06bc0b0a8d382143fdc570ec`  
**Recovery authority:** `HANDOFF-STEWARDSHIP-drain-dogfood-continuity-pr-queue.md`  
**Activation gate:** `satisfied — #725 MERGED @ 28f4fb432c71553f2479e02fee851951e20c7ec9; activation base main@28f4fb432c71553f2479e02fee851951e20c7ec9`  
**PR topology:** `serial`  
**PR authorization:** `ACTIVE — rebase/update/review existing PR #726 only; do not open another implementation PR; MERGE required`  
**PR title:** `DOGFOOD-CONTINUITY: confirm existing relationships by exact edge id`

**Activation facts:**
- Predecessor #725 merge SHA: `28f4fb432c71553f2479e02fee851951e20c7ec9`
- Rebased #725 head: `0fd7f8c1ba8ec1a82799ead7fb1005a11506a6ea`
- Activation base: `main@28f4fb432c71553f2479e02fee851951e20c7ec9`
- Formal review cycles on #725 integration head: 1
- Required finish: MERGE #726; then pristine full acceptance from real main

> This slice was already implemented, reviewed twice, and exercised on a synthetic
> combined dogfood head before the accidental PR fan-out was recognized. Preserve
> that evidence, but do not treat the synthetic head as integration authority.
> BLOCKED means no active §4 lease until #725 is merged and #726 is rebased onto
> actual `main`.

## §1 Mission and merge-ready invariant

**Mission:** When a candidate reuses the derived durable write
`relationship_id` already present on the sealed parent with compatible admitted
relationship semantics, including endpoint orientation after any admitted reverse
mapping, identity gating confirms that relationship and does not emit CREATE_NEW
into the occupied id. Incompatible occupancy is rejected as `blocked_collision`.

**Merge-ready invariant:**

```text
derived durable write relationship_id equals an existing parent relationship_id
  + same published canonical endpoints
    (Buddy endpoints normalized through admitted predicate mapping,
     including reverse_endpoints)
  + same admitted relationship predicate
→ confirm existing relationship

derived durable write relationship_id already occupied
  + incompatible published endpoints or predicate
→ explicit conflict / rejection

never CREATE_NEW into an occupied relationship_id
```

Continuity is keyed on the **derived durable write relationship id**
(`edge:{resolved buddy subject}:{buddy predicate}:{resolved buddy target}` sealed
into `value.edge_id` / DungeonMind `relationship_id`), not extractor-local
`CandidateEdge.edge_id`.

## §2 Context and recovery sequencing

| Field | Content |
|---|---|
| Dogfood predecessor | C1S6 `relationship_id_collision` on `edge:node:torbin:located_in:loc:hempholm`. |
| Existing transport | PR #726, parked while this handoff is BLOCKED. |
| Prior review | Cycle 1 HOLD on `289ae015…`; Cycle 2 code-clean/HOLD on sequencing. Preserve as historical evidence, but final merge review must target the rebased head. |
| PR topology | `serial`. |
| Activation gate | #725 merged + synced; steward re-anchors and activates this handoff. |
| Action at activation | Rebase existing #726 onto exact current `main`; ensure the cumulative diff contains #726's edge slice rather than duplicating already-merged #725; review the new exact head; merge only after formal approval. |
| Named successor | Fresh pristine 44-session structural acceptance on actual `main`; no new implementation PR unless that run STOPs and a new handoff is designed after queue closure. |
| Explicit non-goals | Fuzzy relationship matching; ontology expansion; predicate invention; ID regeneration; acceptance-run repair; graph redesign. |

Synthetic/cherry-picked combined heads are diagnostic evidence only. The recorded
44/44 PASS from a combined head does **not** close structural acceptance for real
`main`; the authoritative rerun happens after this queue drains.

## §3 Observable paths

| Path | Required behavior | Owning boundary |
|---|---|---|
| compatible repeated direct predicate | omit CREATE_NEW / confirm existing | identity gate |
| `belongs_to` repeated after reverse publish as `dnd5e:owns` | normalize orientation and confirm existing | identity gate |
| occupied id, incompatible endpoint/predicate | `blocked_collision` | identity gate |
| free durable relationship id | CREATE_NEW behavior unchanged | identity gate |
| parent relationship facts | loaded from exact sealed parent projection/payload | mutation context / DungeonMind adapter |

## §4 Write lease — prospective while BLOCKED

```text
apps/live_control_server/models/world_graph_mutation_context.py
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
src/graph_memory/extract_identity_gate.py
tests/test_exact_edge_id_continuity.py
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md
```

No path above is actively leased while this handoff is BLOCKED.

**Serialization with #725:** both slices touch
`apps/live_control_server/models/world_graph_mutation_context.py`. Recovery order
is strict: #725 merges first; then #726 rebases onto that real `main`. No concurrent
unserialized dual-write.

## §5–§6 Non-goals / stop signs

Do not invent alternate relationship ids. Do not remap predicates beyond the
existing admitted write-path mapping. Do not repair acceptance runs mid-flight.
Do not widen into general relationship merge logic. Do not open a new repair PR
from a newly observed STOP; return it to the steward.

## §7 Evidence

```bash
uv run pytest tests/test_exact_edge_id_continuity.py -q
uv run ruff check \
  apps/live_control_server/models/world_graph_mutation_context.py \
  apps/live_control_server/integrations/dungeonmind/world_graph_writes.py \
  src/graph_memory/extract_identity_gate.py \
  tests/test_exact_edge_id_continuity.py
git diff --check
git diff --name-only <activation-dispatch-base>...HEAD
```

Prior author evidence includes the reverse-endpoint regression (`belongs_to` →
`dnd5e:owns`) and a synthetic combined 44/44 PASS. Those are supporting evidence,
not substitutes for final rebased review or the post-queue pristine acceptance run.

## §8 Review handback

Record exact rebased base/head, formal review cycle, prior-finding disposition,
evidence provenance, actual changed paths, and confirmation that no additional PR
was opened.

## §9 Acceptance rubric

- [ ] Handoff was activated only after #725 merge/sync/re-anchor.
- [ ] Existing #726 was rebased onto real current `main` and no already-merged #725 code remains as duplicate diff.
- [ ] Direct and reverse-endpoint relationship continuity both hold.
- [ ] No fuzzy matching/predicate invention/ID regeneration was introduced.
- [ ] No successor/repair PR was opened from this lane.
