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

## Browser review UI

`viewer.html` is a single-file, dependency-free reviewer for any
`<campaign>_stage_d_promotion_<ts>.json` sidecar.

Two ways to open it:

```bash
# Easiest — drag-drop the JSON into the page after opening directly:
xdg-open evals/stage_d_entity_resolution_vertical_slice/promotions/viewer.html

# Or serve and auto-load via ?file= query (works because fetch() is allowed
# under http://):
cd evals/stage_d_entity_resolution_vertical_slice/promotions
python -m http.server 8765
# then open: http://localhost:8765/viewer.html?file=longmont-c1_stage_d_promotion_20260422T235629Z.json
```

Per row you get: slug + display_name, session range, descriptors-seen chips,
registry-collision flags, evidence summary, the LLM rationale (if present),
and Accept / Defer / Reject buttons. Decisions persist in `localStorage`
keyed by `(campaign_id, generated_at)`, so reloading the page does not
lose state.

Click **Download decisions JSON** to export a
`stage_d_promotion_decisions_v1` payload containing the promote_payloads
for every row you accepted — the GM can paste those records directly into
`_npc_registry.json` and re-run `scripts/lint_npc_registry.py`.

The viewer is fully deterministic: it needs no network, no LLM, and reads
only the fields the deterministic aggregation pass produces. The LLM
recommendation, if present in the sidecar, is shown as advisory.
