# A9a implementation note — authored graph gold/eval export foundation

Date: 2026-07-07  
Branch: `codex/authored-graph-gold-eval-export-foundation`

## What landed

- `apps/live_control_server/services/graph_authoring_gold_eval_export.py`
  - Schema `dmb.authored_graph_gold_eval_export.v1`
  - `AuthoredGraphGoldKnowledgeScope` (`session_local`, `campaign_retrospective`, `cross_session_context_required`)
  - `build_authored_graph_gold_eval_export`, `write_authored_graph_gold_eval_export`, `export_authored_graph_gold_eval`
  - Filters to `status == "authored"` and `include_in_gold_eval == true`
  - Maps object, link-existing, and relationship assertions with source anchors, visibility, graph scope, provenance, and gold eval notes
- `GraphAuthoringOverlayStore.exports_dir()` → `<campaign>/_graph_authoring/exports/`
- `tests/test_graph_authoring_gold_eval_export.py`

## What this does not claim

- Exported artifacts are **not** candidate graph gold and are **not** canonical campaign memory.
- No mutation of source recap markdown, extracted run artifacts, existing gold fixtures, event logs, or overlay assertions.
- No UI opt-in, prepare/commit payload fields, commit-time export, or automatic side effects.
- No extractor comparison against authored exports yet.
- A7 dogfood UX issues are out of scope.

## Where exports are written

```text
<corpus>/<campaign>/_graph_authoring/exports/authored_graph_gold_eval_export.<timestamp>.<digest>.json
```

Exports are explicit developer artifacts only. Nothing writes unless `write_authored_graph_gold_eval_export` or `export_authored_graph_gold_eval` is called.

When no assertions qualify, no file is written and the helper returns `diagnostic_code = no_gold_eval_assertions`.

## Fixture authority ledger

Per the eval fixture authority ledger:

- Candidate graph gold fixtures (`candidate_graph_gold.json` + manifest) remain the authority for extraction comparison benchmarks.
- Authored gold/eval exports are a **bridge artifact** carrying human-authored corrections with provenance for future eval work.
- Generated run artifacts and authored exports are not gold authority unless separately accepted and ledgered.

## Verification

```bash
uv run pytest tests/test_graph_authoring_gold_eval_export.py

uv run pytest tests/test_graph_authoring_overlay_models.py \
  tests/test_graph_authoring_overlay_projection.py \
  tests/test_graph_object_authoring_prepare.py \
  tests/test_graph_object_authoring_commit.py \
  tests/test_graph_authoring_visibility.py
```

## Deferred to A9b+

- Advanced UI opt-in for `include_in_gold_eval`, `gold_eval_notes`, and `knowledge_scope`
- Prepare/commit payload exposure
- Optional commit-time export
- Developer route or export button
- Conversion or comparison against candidate graph gold fixtures
