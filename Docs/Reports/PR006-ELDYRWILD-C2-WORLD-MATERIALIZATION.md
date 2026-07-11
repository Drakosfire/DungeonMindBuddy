# PR006 — Eldyrwild C2 World Materialization Report

**Verdict:** PASS — acceptance corpus materialized from content-derived candidates, published through an empty Kernel baseline plus `merge_contribution_to_revision` only, with provenance, integrity, rebuild equivalence, and source-locked revisions.

**Generated:** from `artifacts/graph_memory/pr006/eldyrwild-c2-materialization-report.json`

## Head revisions

| Field | Value |
|---|---|
| Empty baseline | `rev:fa7ed075db24b3fa9e893424c28ae63d` (`op:pr006-empty-baseline`) |
| Final head revision | `rev:7703cfb4fe54094b836f1ce5a9f56669` |
| Parent at materialize start | baseline revision above |

The baseline contains **no** corpus nodes, edges, evidence, or source artifacts. Every acceptance assertion reaches the head exclusively via Kernel `merge_contribution_to_revision`. Rebuild starts from that empty baseline and replays the contribution ledger.

Materialization imports **`graph_memory.kernel` package exports only**. Idempotency fingerprints are computed locally from the publicly loaded store.

> **Prerequisite:** structural-vs-density world publish validation lives in a separate Kernel/storage PR. PR006 consumes that contract; it does not claim those storage/validate files as in-scope under the original handoff allowlist.

## Inventory / required vs optional

Under `required_world_roots`, only each root's hub `README.md` is `required=True` (`world_root_required_hub_basename`). Expanded leaves are optional. Required sources that are not accepted fail acceptance.

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

### Authored contributions / identity decisions

Manifest requests active Graph Review contributions and identity decisions with `absence_is_reportable_not_fatal: true`.

**Result at materialization time:** reportable absence of:

- `active_graph_review_contributions`
- `identity_decisions`

No approved Graph Review assertions or durable identity decisions were present in the runtime store to merge. Absence is recorded; it is not a failed required source. Reconstruction therefore proves contribution-ledger rebuild for **source-extraction** contributions only for this run.

### Skipped sources (optional leaves)

- `…/Mirathorn/Sewers/Sewer Traps.md` — no_extractable_entity_from_content
- `…/Mirathorn/Sewers/allies_hideout.md` — no_extractable_entity_from_content
- `…/Mirathorn/Sewers/ritual_chamber.md` — no_extractable_entity_from_content
- `…/Mirathorn/Stormspire Academy/Stormspire Academy.md` — no_extractable_entity_from_content
- `…/Mirathorn/Stormspire Academy/What the Wolf knows.md` — no_extractable_entity_from_content
- `…/Mirathorn/Stormspire Academy/Wynna Mossglade _ Clerk.md` — no_extractable_entity_from_content

## Graph counts

| Metric | Value |
|---|---|
| Nodes | 51 |
| Edges | 174 |
| Evidence refs | (see machine report) |

## Representative examples (acceptance head)

| Kind | Examples |
|---|---|
| PCs | `pc_baergrom` Baergrom Stoutheart; `pc_bonogo`; `pc_caelynn`; `pc_ephanna`; `pc_karsemine`; `pc_stafl` |
| Locations | `loc_mirathorn` Mirathorn; `loc_mireward` Mireward; `loc_edge` Edge of the World |
| Threats / mechanical | `creature_latch_harrow` Latch-Harrow; `creature_tripod_null_calf` Tripod Null Calf |
| Cross-session | `event_session_1` … `event_session_23` plus journey event `event_journey_mireward_reach` |

## Extraction method

Deterministic content parse (no LLM in this PR): frontmatter/H1, party lexicon, roster ∩ text mentions for PC participation, lexicon/typed-subject worldbuilding; optional leaves may skip.

## Identity diagnostics

Ambiguous / blocked_collision / rejected outcomes fail closed (unresolved mention + rejected assertion; edges with deferred endpoints rejected). Remapped `resolved_existing` subjects rebuild assertion IDs via `kernel.build_assertion` and rewrite edge endpoints.

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

- World integrity: valid (structural publish bar)
- Contribution integrity: valid
- Rebuild equivalent to head: yes (empty baseline + contribution replay)
- Idempotent replay: head unchanged; `duplicate_graph_state_created=False`

## Unsupported projection requirements (explicit PR007+)

From the machine report:

- revision-pinned Projection Engine (PR007)
- Plan latest-ingest / preview selection migration (PR008)
- focus-session overlay semantics beyond read-model baseline
- production retrieval over graph head without projection contract

## Plan trust

**Can trust:** persistent `eldyrwild` head for longmont-c2; Sessions 1–23 inventoried with sha256; Mirathorn/Mireward hubs present; six PC hubs present; empty-baseline Kernel merge + rebuild equivalence; accepted assertions carry source artifact + revision; no `fixture://` URIs.

**Cannot trust:** revision-pinned projection (PR007); latest-ingest preview selection (PR008); Graph Review preview union as durable authority; autonomous agent writes without governed confirm (PR011).

## Retain / rewrite / delete ownership

```text
Retained temporarily:
  - apps/live-control-ui graph-preview route parameters
  - union_supergraph_projection_adapter preview selectors
Reason:
  - Named remaining consumers still use preview/latest-ingest until Projection Engine
    and Plan selection land.
Remaining consumer:
  - Graph Review / live-control preview paths; Plan surfaces not yet on world head.
Required deletion PR:
  - PR007 (projection selection APIs) / PR008 (Plan migration) / leftovers → PR012
```

## Required hubs

- Mirathorn: present
- Mireward: present
