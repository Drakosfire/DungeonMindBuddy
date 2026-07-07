# A10b implementation note — authored alias prose grounding

Date: 2026-07-07  
Branch: `codex/graph-authoring-authored-alias-prose-grounding`

## A10a dogfood finding addressed

C1S2 dogfood showed `gang → the group` link-existing commits succeeded (overlay, event log, node alias enrichment) but opening recap prose still rendered **“The gang survived”** as plain text. The GM had to open the group node card to infer success.

## User story improved

After prepare, commit, and reload, eligible **link-existing alias** assertions now ground the selected source phrase in the **graph review projection** as a clickable `dmb-node` mention/pill. The mention resolves to the existing target node and carries authored-overlay metadata for debug/tooling.

## What changed

- `apply_authored_overlay_to_graph_review_projection` now adds authored alias mentions for eligible `link_existing` assertions.
- Mentions respect audience visibility filtering (GM-private aliases do not appear for table/player audiences).
- Duplicate and conflicting overlap with existing markdown links is handled deterministically with diagnostics.
- `AuthoredOverlayProjectionSummary` adds `projected_link_existing_count`; `projected_node_count` now counts **new object** assertions only.
- `GraphAuthoredOverlaySummary` UI copy distinguishes linked aliases from new objects.

## What remains deferred

- Player UI, LLM assist, eval export UI, identity merge, broad node-detail redesign.
- Global alias scanning (every instance of a word in recap) — A10b grounds **one** conservative mention per assertion at the selected anchor.
- Prose grounding for **new object** assertions (object kind) — this PR targets link-existing aliases only.
- Table/player visibility preview toggle in UI.

## Safety / no-mutation

- Source recap markdown on disk is unchanged.
- Graph ingest run artifacts and candidate graph gold fixtures are unchanged.
- Grounding is projection-only: markdown in the API response is enriched for review display, not written back to corpus files.

## Verification

```bash
uv run pytest tests/test_graph_authoring_overlay_projection.py -q
uv run pytest tests/test_graph_authoring_visibility.py -q
uv run pytest tests/test_graph_object_authoring_prepare.py tests/test_graph_object_authoring_commit.py -q
cd apps/live-control-ui && npm test -- --run GraphAuthoredOverlaySummary
```
