# PR006 — Eldyrwild C2 World Materialization Report

**Verdict:** PASS — acceptance corpus materialized from **content-derived** candidates (deterministic parse of source markdown), published through Kernel contributions, with provenance, integrity, rebuild equivalence, and source-locked revisions.

**Generated:** from `artifacts/graph_memory/pr006/eldyrwild-c2-materialization-report.json`

## Head revisions

| Field | Value |
|---|---|
| Corpus-assembled baseline | `rev:09e65958c1a61d139b8fa3604ae86c9b` (`op:pr006-corpus-assembled`) |
| Final head revision | `rev:92afbd56b2c8e6114e029f2b0d3be071` |
| Parent at materialize start | baseline revision above |

No `fixture://` baseline objects. The first published revision is assembled only from acceptance-corpus contributions applied in memory, then durable contribution merges advance the head.

## Inventory / bundle honesty

| Metric | Count |
|---|---|
| Requested sources | 79 |
| Bundle accepted | 73 |
| Bundle skipped | 6 |
| Merged contributions | 73 |
| Failed required | 0 |
| Recaps accepted (sessions 1–23) | 23 |
| PC hubs | 6 |
| Mirathorn / Mireward hubs | present |

### Skipped sources (explicit)

Worldbuilding leaves without extractable hub/lexicon/typed-subject content are skipped rather than accepted with empty or filename-only graphs:

- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/Sewer Traps.md`: no_extractable_entity_from_content
- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/allies_hideout.md`: no_extractable_entity_from_content
- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Sewers/ritual_chamber.md`: no_extractable_entity_from_content
- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/Stormspire Academy.md`: no_extractable_entity_from_content
- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/What the Wolf knows.md`: no_extractable_entity_from_content
- `corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/Stormspire Academy/Wynna Mossglade _ Clerk.md`: no_extractable_entity_from_content

## Graph counts

| Metric | Value |
|---|---|
| Nodes | 52 |
| Edges | 174 |
| Accepted assertions | 481 |
| Assertions with source artifact linkage | 481 |

## Extraction method

Deterministic content parse (no LLM in this PR):

- Frontmatter title / H1 labels
- Party-registry lexicon + hub README display names for PC mention detection
- Recap participation = session roster ∩ in-text PC mentions (not unconditional six-PC edges)
- Locations/NPCs/creatures only when mentioned in that source's body
- Worldbuilding: hub READMEs + lexicon hits + typed subject docs (`statblock`/`dossier`/…); otherwise skip

## Identity diagnostics

{
  "unresolved_mention_count": 0,
  "rejected_assertion_count": 0,
  "provisional_identity_count": 0,
  "ambiguous_identity_count": 0,
  "blocked_collision_count": 0,
  "resolved_existing_count": 307
}

## Integrity

- World integrity: valid
- Contribution integrity: valid
- Rebuild equivalent to head: yes
- Idempotent replay: head unchanged; `duplicate_graph_state_created=False` (fingerprint-compared)

## Required hubs

- Mirathorn: present
- Mireward: present

## Plan trust

**Plan can trust:**

- Persistent eldyrwild world graph head exists for longmont-c2
- Session 1–23 recap sources inventoried with sha256 provenance
- Mirathorn and Mireward location nodes present in merged head
- Six C2 PC hub nodes present with worldbuilding domain mapping
- Kernel merge + rebuild equivalence for contribution ledger
- Every accepted assertion carries source_artifact_id + source_revision_id
- Corpus-assembled head has no fixture:// provenance URIs

**Plan cannot trust:**

- Revision-pinned projection slices (PR007 not landed)
- Latest-ingest preview graph selection (PR008 not landed)
- Graph Review preview union as durable authority
- Autonomous agent writes without governed confirm path (PR011)

## Retain / rewrite / delete

Retained temporarily:
- Graph-preview route parameters and preview projection adapters.
- Plan latest-ingest / preview selection consumers.

Reason:
- PR006 establishes persistent runtime graph availability but does not implement the revision-pinned Projection Engine or migrate Plan.

Remaining consumer:
- Existing Graph Review preview views.
- Existing Plan graph-preview/dogfood views.

Required deletion PR:
- PR007 removes production projection selectors.
- PR008 removes Plan latest-ingest / preview selection.
- PR012 catches only named leftovers.
