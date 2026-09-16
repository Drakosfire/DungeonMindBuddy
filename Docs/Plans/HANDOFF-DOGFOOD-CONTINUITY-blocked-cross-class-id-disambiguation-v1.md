# HANDOFF — DOGFOOD-CONTINUITY blocked cross-class id disambiguation v1

**Created:** 2026-09-15  
**Status:** DONE — MERGED as PR #724 @ `45c98d425bb61746564f151c2b5adccaa1591898` (rebased head `4a5f50da`); stewardship drain continues at #725  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-blocked-cross-class-id-disambiguation-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Original design authority base:** `main@68577114b3c8ec7e06bc0b0a8d382143fdc570ec`  
**Recovery authority:** `HANDOFF-STEWARDSHIP-drain-dogfood-continuity-pr-queue.md`  
**Activation gate:** `satisfied — #723 MERGED @ ba0f781b6b3effb4770db3bf171a89da1ce18bae; activation base main@ba0f781b6b3effb4770db3bf171a89da1ce18bae`  
**PR topology:** `serial`  
**PR authorization:** `ACTIVE — rebase/update/review existing PR #724 only; do not open another implementation PR`  
**PR title:** `DOGFOOD-CONTINUITY: disambiguate shared ids on blocked cross-class collisions`

**Activation facts:**
- Predecessor #723 merge SHA: `ba0f781b6b3effb4770db3bf171a89da1ce18bae`
- Rebased #723 head: `70749ca8d4e6ae8c5c600218089dfaab47ace99d`
- Activation base: `main@ba0f781b6b3effb4770db3bf171a89da1ce18bae`
- Formal review cycles on #723 integration head: 1

> This handoff was originally created inside PR #724 instead of being landed on
> `main` before dispatch. The 2026-09-15 stewardship recovery makes the design
> durable and parks the already-open PR. BLOCKED means its §4 paths are not an
> active write lease until the steward activates this handoff at its queue turn.

## §1 Mission and merge-ready invariant

**Mission:** When cross-class exact-label collisions are policy-blocked and kept
as separate identities, production reconciliation must not leave two kept nodes
sharing one `node_id`, so candidate-document integrity remains fail-closed for
true duplicates without failing on blocked actor/collective pairs.

**Merge-ready invariant:**

```text
blocked cross-class exact-label collision
  → both identities kept
  → node_ids unique among kept members
  → highest-priority type class retains the original id
  → other colliding members rewritten to {node_type}:{label}
  → ambiguous edges that still name the original id address the survivor
  → true same-id same-class duplicates remain integrity failures
```

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes — deterministic disambiguation of blocked cross-class collisions. |
| Most likely adversarial sequence | Actor + collective keep separate semantics but retain the same minted node id → candidate integrity fails. |
| Will §7 detect that failure? | Identity-resolution + preview + candidate-admission regression tests. |
| Easiest owning boundary to under-test | Edge references after one collision member is rewritten. |
| PR topology | Serial recovery queue. #724 activates only after #723 closes. |
| Fact that forces stop/split | Merging actor+collective semantics or weakening true duplicate integrity. |

## §2 Context and recovery sequencing

| Field | Content |
|---|---|
| Parent authority | Candidate generation/integrity after #721 plus repaired admission eligibility #723. |
| Dogfood predecessor | C1S2 STOP at `production_extraction` / `duplicate_node_id: node:glowkindle`. |
| Existing transport | PR #724, parked while this handoff is BLOCKED. |
| PR topology | `serial`. |
| Activation gate | #723 merged + synced; steward re-anchors and activates this handoff. |
| Action at activation | Rebase existing #724 onto exact current `main`; review the resulting exact head; merge only after formal approval. |
| Named successor | #725, which remains BLOCKED until #724 merges. |
| Explicit non-goals | Ontology expansion; actor/collective merge; admission redesign; prompt changes; duplicate-integrity weakening. |

Synthetic/cherry-picked combined dogfood heads are diagnostic evidence only. They do not replace review of #724 rebased onto actual `main`.

## §3 Observable paths

| Path | Current | Required | Owning boundary |
|---|---|---|---|
| blocked actor/collective exact-label collision | separate semantic nodes can share minted id | deterministic unique kept ids | identity resolution |
| edge still naming original id | ambiguous after rewrite | original id addresses retained survivor deterministically | identity resolution |
| same-class true duplicate | integrity failure | still integrity failure | candidate integrity |

## §4 Write lease — prospective while BLOCKED

```text
src/graph_memory/identity_resolution.py
tests/test_graph_memory_identity_resolution.py
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-blocked-cross-class-id-disambiguation-v1.md
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-blocked-cross-class-id-disambiguation-v1.md
```

No path above is actively leased while this handoff is BLOCKED.

**Out of scope:** ontology expansion, merging actor+collective, admission changes,
extraction prompts, weakening `duplicate_node_id` integrity, and opening any
successor PR.

## §5–§6 Non-goals / stop signs

Do not use label heuristics to collapse the blocked identities. Do not weaken
candidate integrity to tolerate true duplicate IDs. Do not open a new repair PR
from any newly observed STOP; return it to the steward.

## §7 Evidence

```bash
uv run pytest tests/test_graph_memory_identity_resolution.py tests/test_graph_preview_runner.py tests/test_candidate_graph_admission_contract.py -q
uv run ruff check src/graph_memory/identity_resolution.py tests/test_graph_memory_identity_resolution.py
git diff --check
git diff --name-only <activation-dispatch-base>...HEAD
```

The full paid acceptance rerun is deferred until #722–#726 are all merged onto
real `main`; do not spend another full run merely to advance from one parked
repair to the next.

## §8 Review handback

Record exact rebased base/head, formal review cycle, evidence provenance, actual
changed paths, and confirmation that no additional PR was opened.

## §9 Acceptance rubric

- [ ] Handoff was activated only after #723 merge/sync/re-anchor.
- [ ] Existing #724 was rebased onto real current `main`.
- [ ] Cross-class disambiguation is deterministic and true duplicates remain failures.
- [ ] No unrelated identity/admission semantics changed.
- [ ] No successor/repair PR was opened from this lane.
