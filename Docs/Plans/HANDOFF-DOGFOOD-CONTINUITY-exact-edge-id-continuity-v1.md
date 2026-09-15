# HANDOFF — DOGFOOD-CONTINUITY exact-edge-id continuity v1

**Created:** 2026-09-15  
**Status:** ACTIVE — one implementation capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `main@68577114b3c8ec7e06bc0b0a8d382143fdc570ec`  
**Activation gate:** `none — satisfied` (predecessor dogfood STOP on combined acceptance head is observational evidence, not a merge gate)  
**Dispatch base rule:** fresh current `main` containing this checked-in handoff; record exact implementation branch base at dispatch/review.  
**PR title:** `DOGFOOD-CONTINUITY: confirm existing relationships by exact edge id`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Relationship analogue of
> `HANDOFF-DOGFOOD-CONTINUITY-exact-id-identity-continuity-v1.md` (#725).
> Successor to stochastic acceptance HOLD at `longmont-c1/session-6`
> (`relationship_id_collision` on `edge:node:torbin:located_in:loc:hempholm`).

## §1 Mission and merge-ready invariant

**Mission:** When a candidate edge reuses an exact durable `relationship_id`
already present on the sealed parent with the same canonical endpoints and an
admitted compatible relationship predicate, identity gating confirms that
relationship and does not emit CREATE_NEW into the occupied id. When the id is
occupied incompatibly, the edge is rejected as `blocked_collision`.

**Merge-ready invariant:**

```text
candidate edge_id equals an existing parent relationship_id
  + same canonical endpoints
  + same admitted relationship predicate
→ confirm existing relationship

candidate edge_id already occupied
  + incompatible endpoints or predicate
→ explicit conflict / rejection

never CREATE_NEW into an occupied relationship_id
```

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes — exact edge-id continuity only |
| Most likely adversarial sequence | Compatible re-extract still emits CREATE_NEW → DM `relationship_id_collision` |
| Will §7 actually detect that failure? | Classify + identity-gate tests with Torbin/Hempholm witness |
| Easiest owning boundary to under-test | `classify_edge_against_parent` vs gate omit/reject |
| Fact that forces stop/split | Fuzzy edge matching / predicate remapping / ID regeneration |

## §2 Context

| Field | Content |
|---|---|
| Parent authority | Exact object-id continuity (#725); acceptance dogfood HOLD |
| Predecessor | Stochastic C1S6 `relationship_id_collision` after C1S1–S8 best depth |
| Named successor | Fresh pristine current-corpus acceptance `--execute` (no resume) |
| Explicit non-goals | Fuzzy edge matching; predicate remapping; ID regeneration; acceptance-run repair; graph redesign |
| State-authority sync set after merge | Update acceptance REPORT after pristine rerun (separate) |

## §3 Observable paths

| Path | Current | Required | Owning boundary |
|---|---|---|---|
| Compatible re-extract of occupied edge | always `created_new` → write collision | omit / confirm existing | identity gate |
| Occupied id, incompatible endpoints/predicate | would CREATE_NEW | `blocked_collision` reject | identity gate |
| Free durable edge id | CREATE_NEW | still CREATE_NEW | identity gate |
| Parent relationships on mutation context | missing / unused | populated from DM payload/projection | world_graph_writes |

## §4 Write lease (exclusive while ACTIVE)

```text
apps/live_control_server/models/world_graph_mutation_context.py
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
src/graph_memory/extract_identity_gate.py
tests/test_exact_edge_id_continuity.py
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-exact-edge-id-continuity-v1.md
```

**Out of scope:** fuzzy matching, ontology expansion, acceptance harness,
`src/prompts/*.py`, gold fixtures, #723/#724/#725 object/admission slices.

## §5–§6 Non-goals / stop signs

Do not invent alternate edge ids. Do not remap predicates onto different
semantics. Do not repair acceptance runs mid-flight. Do not widen this into a
general relationship merge/graph redesign.

## §7 Evidence

```bash
uv run pytest tests/test_exact_edge_id_continuity.py -q
uv run ruff check \
  apps/live_control_server/models/world_graph_mutation_context.py \
  apps/live_control_server/integrations/dungeonmind/world_graph_writes.py \
  src/graph_memory/extract_identity_gate.py \
  tests/test_exact_edge_id_continuity.py
```

## Predecessor STOP (handback; not yet durable acceptance REPORT)

`longmont-c1/session-6` / `dungeonmind_write` /
`relationship_id_collision` /
`edge:node:torbin:located_in:loc:hempholm`
(parent already holds matching endpoints + `dnd5e:located_in`).
