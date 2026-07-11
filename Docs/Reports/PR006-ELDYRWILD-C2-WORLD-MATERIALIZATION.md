# PR006 — Eldyrwild C2 World Materialization Report

**Verdict:** PASS — acceptance corpus materialized from **content-derived** candidates, published through an **empty Kernel baseline** plus `merge_contribution_to_revision` only, with provenance, integrity, rebuild equivalence, and source-locked revisions.

**Generated:** from `artifacts/graph_memory/pr006/eldyrwild-c2-materialization-report.json`

## Head revisions

| Field | Value |
|---|---|
| Empty baseline | `rev:fa7ed075db24b3fa9e893424c28ae63d` (`op:pr006-empty-baseline`) |
| Final head revision | `rev:6fbddd0f9a05d44a8a36c27e4f00bd83` |
| Parent at materialize start | baseline revision above |

The baseline contains **no** corpus nodes, edges, evidence, or source artifacts. Every acceptance assertion reaches the head exclusively via Kernel `merge_contribution_to_revision`. Rebuild starts from that empty baseline and replays the contribution ledger — proving reconstruction is not circular.

Materialization imports **`graph_memory.kernel` package exports only** (no private `contribution_merge` / `contribution_rebuild` / identity submodule imports). Idempotency fingerprints are computed locally from the publicly loaded store.

## Inventory / required vs optional

`required_world_roots` still expand Mirathorn/Mireward trees for inventory coverage, but only each root's hub `README.md` is `required=True` (`world_root_required_hub_basename`). Expanded leaves are optional and may be skipped. The materializer does not reinterpret `required=True`: any required source that is not accepted fails acceptance.

| Metric | Count |
|---|---|
| Requested sources | 79 |
| Bundle accepted | 73 |
| Bundle skipped (optional leaves) | 6 |
| Merged contributions | 73 |
| Failed required | 0 |
| Recaps accepted (sessions 1–23) | 23 |
| PC hubs | 6 |
| Mirathorn / Mireward hubs | present |

### Skipped sources (optional leaves)

- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/Sewer Traps.md`: no_extractable_entity_from_content
- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/allies_hideout.md`: no_extractable_entity_from_content
- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/ritual_chamber.md`: no_extractable_entity_from_content
- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/Stormspire Academy.md`: no_extractable_entity_from_content
- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/What the Wolf knows.md`: no_extractable_entity_from_content
- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/Wynna Mossglade _ Clerk.md`: no_extractable_entity_from_content

## Graph counts

| Metric | Value |
|---|---|
| Nodes | 51 |
| Edges | 174 |
| Accepted assertions | 480 |
| Assertions with source artifact linkage | 480 |

## Extraction method

Deterministic content parse (no LLM in this PR):

- Frontmatter title / H1 labels
- Party-registry lexicon + hub README display names for PC mention detection
- Recap participation = session roster ∩ in-text PC mentions
- Locations/NPCs/creatures only when mentioned in that source's body
- Worldbuilding: hub READMEs + lexicon hits + typed subject docs; otherwise skip (optional leaves only)

## Identity diagnostics

Ambiguous / blocked_collision / rejected Kernel outcomes are **fail-closed**: unresolved mention + rejected assertion, accepted node omitted, edges using that endpoint rejected. They are never promoted to `created_new`.

```json
{
  "unresolved_mention_count": 1,
  "rejected_assertion_count": 1,
  "provisional_identity_count": 0,
  "ambiguous_identity_count": 0,
  "blocked_collision_count": 1,
  "resolved_existing_count": 255
}
```

## Integrity

- World integrity: valid (structural; demo-density is fixture-acceptance, not incremental publish)
- Contribution integrity: valid
- Rebuild equivalent to head: yes (empty baseline + contribution replay)
- Idempotent replay: head unchanged; `duplicate_graph_state_created=False` (local fingerprint compared)

## Required hubs

- Mirathorn: present
- Mireward: present

## Plan trust

This graph is the PR006 acceptance World Supergraph for Eldyrwild / Longmont C2 Sessions 1–23. Projection (PR007), agent tooling (PR011), and Plan UI migration remain out of scope. Preview selectors remain quarantined until PR007.

## Retained preview paths (not deleted this slice)

- `apps/live-control-ui` graph-preview route parameters
- `union_supergraph_projection_adapter` preview selectors
