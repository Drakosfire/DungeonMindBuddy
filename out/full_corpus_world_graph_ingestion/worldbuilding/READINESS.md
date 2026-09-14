# Worldbuilding readiness — full-corpus slice

**Decision:** **DEFER** worldbuilding ingestion for this slice.

**Candidate root inspected:** `corpus/eldyrwild-markdown/Elderwyld/` (128 Markdown files)

## What already exists

Source metadata is present on most Elderwyld files:

- `document_class`: `world`, `reference`, `planning`, occasionally `play`
- `source_class`: mostly `seed_reference`; also `planning_document`, `roll_table`, `authored_dossier`, `character_seed`, `observed_session_recap`
- `canon_layer`: mostly `world`
- `temporal_scope`: mostly `evergreen`

Production also has a worldbuilding *write-plan* owner (`dmb_worldbuilding_write_plan_v2`) and SourceDomain mapping (`worldbuilding` → `SourceDomain.WORLDBUILDING`).

## Why that is not enough

1. **Recap extraction would flatten setting into played canon.** `recap_category_v1` stamps `canon_state: played_canon` on every extracted object. Running that profile over Elderwyld would make a seed sentence such as “The Wolf is second in command” indistinguishable from a later observed-session assertion.

2. **The worldbuilding publication path is not a general Elderwyld ingest path.** `WorldbuildingWritePlanResponse.extraction_profile` is locked to `worldbuilding_shepherds_flock_v0@0.1`. That is a bounded Shepherd's Flock experiment, not a corpus-wide worldbuilding extractor.

3. **The Elderwyld tree is mixed authority.** It contains setting hubs, planning scaffolds (`Mireward_PLACE_BUILD_SCAFFOLD.md`, `source_class: planning_document`), and at least one nested play recap (`Battle with The Wolf and Aftermath.md`, `source_class: observed_session_recap`). Admitting the tree as one class would mix those layers.

4. **Session Prep is already correctly classified as planning** and is excluded from played-history ingest. Worldbuilding must meet at least that bar.

## Missing capability (named)

A general worldbuilding extraction/publication owner that:

- admits `source_domain=worldbuilding` documents without using `recap_category_v1`;
- preserves `source_class` / epistemic kind through candidate → contribution → World Graph;
- distinguishes setting fact, GM plan, rumor, secret, and played event at publication time;
- is not locked to a single flock-specific profile.

That is a new source-authority architecture, not a narrow integration. Per the slice contract, worldbuilding is deferred and campaign recaps continue.

This is not a failed slice.
