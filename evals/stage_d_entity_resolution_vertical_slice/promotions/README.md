# Stage D — GM Promotion Sidecars

This directory holds the GM-review surface produced by
`scripts/promote_stage_d_proposals.py` from one or more Stage D propose-only
sidecars (`evals/stage_d_entity_resolution_vertical_slice/proposals/`) and/or
per-run sidecars (`evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/`).

Each promotion run writes two checked-in artifacts:

- `<campaign>_stage_d_promotion_<ts>.json` — full structured payload with
  per-slug aggregation, registry-collision flags, and (when LLM is enabled)
  a `recommendation` ∈ {`accept`, `reject`, `defer_to_gm`,
  `merge_into_existing`} plus `confidence`, `rationale`, and an optional
  `promote_payload` (NpcRegistryRecord-shaped).
- `<campaign>_stage_d_promotion_<ts>.md` — human-readable review surface,
  one table per bucket (proposed_new_records, proposed_aliases, unresolvable).

Mirrors the propose-only contract of the sibling `proposals/` directory:
this CLI **never** mutates `corpus/eldyrwild-markdown/<campaign>/_npc_registry.json`.
The GM reviews the sidecar and applies promotions by hand (or via a future
`--apply` flag — out of scope for v0).

Naming convention: `<campaign_id>_stage_d_promotion_<YYYYMMDDTHHMMSSZ>.{json,md}`.
The Markdown file's HTML header carries the schema, ISO timestamp, model id,
and total cost in USD for quick inspection without opening the JSON.

See `scripts/promote_stage_d_proposals.py` and `evals/stage_d_entity_resolution_vertical_slice/README.md`
("GM promotion workflow") for invocation examples.
