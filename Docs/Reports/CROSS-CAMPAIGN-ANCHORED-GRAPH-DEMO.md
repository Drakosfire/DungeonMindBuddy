# Report — Cross-Campaign Anchored World Graph Demo

Operator runbook for proving world-scope graph visibility across `longmont-c1` and `longmont-c2` under `worldId=eldyrwild`, with campaign-qualified session focus and Hermes grounding.

## Verdict

World scope (`scope_mode=world`) lets Plan/Hermes see committed graph nodes from any campaign in the same world while keeping the narrative anchor on the selected campaign/session. Campaign scope (`scope_mode=campaign`) still isolates foreign-campaign objects. Preview ingest nodes are not agent-visible until extract-promote confirms durable head.

## Proof points (operator checklist)

### 1. Preview ingest nodes are NOT agent-visible

- Open **Ingest → Graph Review** for a session with a completed ingest run.
- Confirm candidate/preview nodes appear in the workbench projection only.
- Run Hermes or Plan world-graph search **before** Review & merge / extract-promote confirm.
- Expected: preview-only nodes do **not** appear in Hermes answers or Plan Edit World Graph search results tied to durable head.

### 2. After Review & merge / extract-promote confirm, nodes are durable head

- In Graph Review, complete **Review & merge** (or **Extract → Promote → Confirm**).
- Expected: promote emits browser event `dmb:world-graph-revision-committed` (see vitest in `GraphReviewExtractPromoteSheet.test.tsx`).
- Plan surfaces listening for that event refresh world-graph context against the new head revision.
- Receipt shows committed revision, affected object count, and **Continue in Plan (world scope)** linking to `/plan?campaign=…&scopeMode=world&session=…&revision=…`.

### 3. Plan Edit World Graph search (world scope) finds committed nodes from either campaign anchor

- Open Plan **Edit World Graph** with default **world** scope (not campaign-only).
- With live packet on `longmont-c2`, search for a C2-only node (e.g. Tripod Null-Calf).
- Switch narrative anchor to `longmont-c1` (same world) and search for C1 curated nodes from the additive bundle.
- Expected: world scope returns nodes from both campaigns; node cards show campaign provenance (`Longmont C1` / `Longmont C2` / `world`) where applicable.

### 4. Insert `#dmb-ref:graph-node:<node-id>` chip; Markdown save unchanged

- From Edit World Graph search, insert a graph-node reference chip into plan markdown.
- Save the document.
- Expected: markdown on disk retains the `#dmb-ref:graph-node:…` token unchanged; no silent rewrite to prose or loss of node id.

### 5. Hermes answers biased to selected campaign/session anchor; may crawl other campaigns with provenance

- Ask Hermes a question with world scope and a qualified session focus (e.g. C1 `session-3`).
- Expected: answers prefer claims anchored to the focus session/campaign; cross-campaign facts may appear when world scope permits, with provenance/campaign scope preserved in grounding (not flattened into anonymous lore).

## Automated falsification

### Python (kernel + agent + Hermes validate)

```bash
python -m pytest \
  tests/test_graph_kernel_world_projection.py::test_world_scope_projection_includes_c2_objects_from_c1_anchor \
  tests/test_graph_kernel_world_projection.py::test_campaign_scope_mode_still_isolates_foreign_campaign \
  tests/test_graph_kernel_world_projection.py::test_qualified_session_focus_does_not_match_bare_session_across_campaigns \
  tests/test_graph_kernel_world_projection.py::test_foreign_campaign_filters_to_world_universal_only \
  tests/test_live_query_hermes_graph.py::test_validate_rejects_missing_context_and_legacy_fields \
  tests/test_agent_world_graph_query_context.py \
  tests/test_cross_campaign_anchored_graph_demo.py \
  -q --tb=short
```

Expected: all tests pass (`… passed` summary, exit code 0).

Key contracts exercised:

| Area | Test file | What it proves |
|------|-----------|----------------|
| Kernel projection | `test_graph_kernel_world_projection.py` | World vs campaign scope; qualified session focus (C1 negative + C2 positive) |
| Agent envelope | `test_agent_world_graph_query_context.py` | `scope_mode` + `campaign_scope` on nodes; C1 nested under C2 outer |
| Demo contract | `test_cross_campaign_anchored_graph_demo.py` | End-to-end scope/focus/validate wiring |
| Hermes validate | `test_live_query_hermes_graph.py` | World scope allows nested C1 under outer C2 |

### Vitest (Plan UI request builders + promote event)

```bash
cd apps/live-control-ui && npm test -- --run \
  src/planSurface/reference/planGraphContextRequest.test.ts \
  src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx \
  2>&1 | tail -40
```

Expected: vitest reports passing tests for:

- Default `scopeMode: "world"` and agent/projection request shapes (`planGraphContextRequest.test.ts`)
- `WORLD_GRAPH_REVISION_COMMITTED_EVENT` on extract-promote confirm (`GraphReviewExtractPromoteSheet.test.tsx`)

## Hygiene

**Do not paste corpus PII** (player names, private session notes, real-name mappings) into external tools, public gists, or web search. Benchmark artifacts and LLM traces under `evals/` stay local.

## Non-goals

- Full corpus parity across C1 and C2 (curated demo bed only).
- URL `?campaign=` override of Plan live-packet campaign.
- Live Hermes subprocess in unit tests (host execution remains manual dogfood).
