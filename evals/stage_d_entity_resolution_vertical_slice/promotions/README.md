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

## Embeddable review component

`viewer.html` is an **embeddable component** that surfaces one proposal at
a time with **Back / Next** navigation and **Accept / Defer / Reject**
decisions. Designed to be dropped inline into any host context (a
conversation surface, a notebook cell, a static review page) — it ships
with a thin standalone harness for local file review but the component
itself does not require drag-drop, file pickers, or a server.

### Standalone use (auto-discovers sidecars)

```bash
cd evals/stage_d_entity_resolution_vertical_slice/promotions
python serve.py
# then open: http://localhost:8765/viewer.html
```

`serve.py` exposes a `/api/sidecars` endpoint that scans this directory
for every `*_stage_d_promotion_*.json` file (newest first, with
campaign_id / generated_at / counts already extracted). The viewer calls
it on load and mounts the most recent sidecar automatically — no file
picker, no `?file=` parameter required. If multiple sidecars are present,
a tiny dropdown appears so you can switch between them; otherwise it
stays hidden. Hit **↻ refresh** after a new promotion run to re-scan.

`?file=<name>` is still honored as an explicit override for non-server
contexts (e.g. opening directly under `python -m http.server`).

### Per-proposal view

The card shows: slug + display_name (or alias text → target slug, or
unresolvable descriptor), session range, descriptors-seen chips, registry-
collision flags, evidence summary, and the LLM rationale (if present,
clearly tagged as advisory). A collapsible **raw record** section exposes
the full JSON entry for deep inspection.

### Keyboard shortcuts

| Key | Action |
|---|---|
| `A` | Accept |
| `D` | Defer |
| `R` | Reject |
| `U` | Undo current decision |
| `J` / `→` / `N` | Next |
| `K` / `←` / `P` | Back |
| `E` | Toggle raw evidence |

Decisions persist in `localStorage` keyed by
`(campaign_id, generated_at)` so reloading does not wipe state.

**Export decisions** writes a `stage_d_promotion_decisions_v2` blob with
`promote_payloads` (NpcRegistryRecord-shaped, ready to paste into
`_npc_registry.json`) and `accepted_aliases` (target_slug + alias_text
pairs).

### Embedding API

The component exposes a minimal mount API for inline embedding:

```js
const handle = window.StageDProposalReview.mount(hostEl, payload, {
  autoAdvance: true,             // advance to next item after a decision
  persistKey:  "my-custom-key",  // override the localStorage key
  onDecision:  (entry, value) => { /* … */ },
  onComplete:  (decisions)      => { /* fired when all items decided */ },
});
handle.getDecisions();   // returns current decisions object
handle.goTo(0);          // jump to a specific index
handle.destroy();        // detach key handler + clear host
```

The component is fully deterministic: it makes no network calls, requires
no LLM, and reads only the fields the deterministic aggregation pass
produces. The LLM recommendation, if present in the sidecar, is shown as
advisory under the "Model take" label.
