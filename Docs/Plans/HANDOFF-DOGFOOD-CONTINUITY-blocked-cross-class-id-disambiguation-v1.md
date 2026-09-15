# HANDOFF — DOGFOOD-CONTINUITY blocked cross-class id disambiguation v1

**Created:** 2026-09-15  
**Status:** ACTIVE — one implementation capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-blocked-cross-class-id-disambiguation-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `main@68577114b3c8ec7e06bc0b0a8d382143fdc570ec`  
**Activation gate:** `none — satisfied`  
**PR title:** `DOGFOOD-CONTINUITY: disambiguate shared ids on blocked cross-class collisions`

## §1 Mission and merge-ready invariant

**Mission:** When cross-class exact-label collisions are policy-blocked (kept as
separate identities), production reconciliation must not leave two kept nodes
sharing one `node_id`, so candidate-document integrity can stay fail-closed for
true duplicates without failing the dogfood on blocked actor/collective pairs.

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

## §4 Write lease

```text
src/graph_memory/identity_resolution.py
tests/test_graph_memory_identity_resolution.py
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-blocked-cross-class-id-disambiguation-v1.md
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-blocked-cross-class-id-disambiguation-v1.md
```

**Out of scope:** ontology expansion; merging actor+collective; admission;
extraction prompts; weakening `duplicate_node_id` integrity.

## §7 Evidence

```bash
uv run pytest tests/test_graph_memory_identity_resolution.py tests/test_graph_preview_runner.py tests/test_candidate_graph_admission_contract.py -q
uv run ruff check src/graph_memory/identity_resolution.py tests/test_graph_memory_identity_resolution.py
```

## Dogfood predecessor STOP

`longmont-c1/session-2` / `production_extraction` /
`duplicate_node_id: node:glowkindle` (character + faction, same minted id).
