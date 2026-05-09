# HANDOFF: Align Corpus Ingestion and Benchmarks with World/Campaign Hierarchy

**Date:** 2026-05-08
**Status:** Ready for next agent
**Scope:** Existing corpus ingestion, hub recall, sentence routing, and benchmark gates
**Anchor decision:** `Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md`

## Mission

Bring the current ingestion and benchmark surfaces inline with the accepted world/campaign hierarchy:

- `canon_layer: world`, `campaign_id: null` for setting-side knowledge.
- `canon_layer: campaign`, `campaign_id: longmont-cN` for table continuity.
- two sibling hubs when the same subject exists in both layers.
- recaps as canonical chronology; hub READMEs, dossiers, and timelines as projections.
- benchmark gates that catch layer drift instead of hiding it.

This is an alignment and falsification pass, not a broad corpus migration. Audit first, update tests/gates second, then migrate only the smallest corpus fixtures needed to prove the contract.

## Decision Context

Read these first, in order:

1. `Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md` — accepted decision and open questions.
2. `Docs/CONVENTION-Corpus-Subject-Schemas.md` — frontmatter and sibling-hub contract.
3. `Docs/CONVENTION-NPC-Hub-Package.md` — NPC-specific setting/campaign hub package.
4. `Docs/CONVENTION-PC-Hub.md` — campaign-only PC default and C1 PC gap reminder.
5. `Docs/CONVENTION-Location-Hub.md` — location hub shapes and nested location behavior.
6. `Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md` — why Lysandra two-hub layout works.
7. `evals/sentence_routing_retrieval_falsification/README.md` — current routing-only benchmark baseline.

## Current Baseline

The design is partially implemented.

Working or mostly working:

- Markdown frontmatter carries `canon_layer`, `campaign_id`, and temporal metadata.
- `src/cli.py` ingest reads frontmatter, rejects CLI/frontmatter conflicts, and requires campaign metadata for campaign-layer ingest.
- `src/agent/evidence_retriever.py` allows world evidence for all scopes and filters campaign evidence by `campaign_id`.
- `evals/canon_layering/run_benchmarks.py` proves world projection and campaign projection separately.
- `evals/llm_ingestion_slice/run_slice.py` has Gate A source/layer integrity for world vs campaign evidence units.
- `src/agent/corpus_writer.py` has `campaign_id` on `append_timeline_row`.
- Lysandra has a real sibling-hub example across `Elderwyld/.../NPCs/captain_lysandra_ironveil/` and `Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/`.
- The 2026-05-08 routing-only refresh is documented as the current cross-session breadcrumb baseline.

Known pressure points:

- Some campaign registries use a world hub as `hub_path` when no campaign hub exists.
- `setting_hub_path` is present but not consistently populated as the explicit world fallback.
- Cross-campaign slug collisions have already appeared in PC/NPC timeline paths.
- Location hierarchy is not yet settled: C1S3 showed a sublocation route (`rivers_edge_pub`) did not satisfy a parent-location expectation (`stonebridge`).
- C1 PC hubs are intentionally absent; do not create them as a side effect.
- Some tools infer layer/campaign from path in eval code, while core ingest prefers frontmatter.

## Files in Scope

Design and conventions:

- `Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md`
- `Docs/CONVENTION-Corpus-Subject-Schemas.md`
- `Docs/CONVENTION-NPC-Hub-Package.md`
- `Docs/CONVENTION-PC-Hub.md`
- `Docs/CONVENTION-Location-Hub.md`
- `.cursor/rules/corpus-layout-conventions.mdc`

Core ingestion and retrieval:

- `src/cli.py`
- `src/ingestion/frontmatter.py`
- `src/ingestion/frontmatter_inference.py`
- `src/ingestion/chunker.py`
- `src/ingestion/entity_extractor.py`
- `src/ingestion/fact_extractor.py`
- `src/store.py`
- `src/reducer/canon_projection.py`
- `src/agent/evidence_retriever.py`
- `src/agent/corpus_writer.py`
- `src/agent/planner.py`
- `src/agent/recap_context.py`

Benchmark and audit surfaces:

- `evals/canon_layering/`
- `evals/llm_ingestion_slice/`
- `evals/sentence_routing_retrieval_falsification/`
- `evals/session_recap_ingest_vertical_slice/`
- `evals/session_events_extraction_vertical_slice/`
- `evals/session_recap_timeline_pass_vertical_slice/`
- `evals/stage_d_entity_resolution_vertical_slice/`
- `evals/npc_corpus_recall_audit/`
- `evals/corpus_remote/`
- `evals/lysandra_vertical_slice/gold/corpus_policy.json`

Corpus fixtures allowed for targeted proof only:

- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json`
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json`
- Lysandra world/campaign hubs.
- Small test fixtures under `evals/*/gold/` or temporary eval scenario fixtures.

Do not sweep-edit the whole corpus in this pass.

## Out of Scope

- Creating all missing C1 PC hubs.
- Moving large numbers of corpus files.
- Rewriting dossiers, seeds, statblocks, or canonical recaps.
- Changing planner prompt behavior unless a benchmark demonstrates the current prompt violates the hierarchy contract.
- Lowering benchmark thresholds to make old behavior pass.
- Replacing routing-only benchmarks with planner-discovery benchmarks.

## Work Plan

### Phase 1: Contract Audit

Goal: identify where current code or fixtures contradict the decision.

Audit questions:

- Does every ingest path preserve `canon_layer` and `campaign_id` from frontmatter?
- Does any eval path infer `campaign_1` instead of `longmont-c1` or otherwise invent a parallel campaign-id vocabulary?
- Does any store/projection/retrieval path treat campaign facts as globally visible?
- Do registries distinguish campaign authority (`hub_path`) from world fallback (`setting_hub_path`)?
- Do any tools accept only `slug` when multiple campaigns can own the same slug?
- Do benchmark gold files encode parent-location expectations that should belong to query expansion instead of route emission?

Expected deliverable:

- A short gap list grouped by `ingest`, `retrieval`, `writer`, `registry`, and `benchmark`.
- For each gap: current behavior, expected hierarchy behavior, file(s), and proposed falsification test.

### Phase 2: Deterministic Gates First

Goal: make layer mistakes fail without paying LLM cost.

Preferred gates:

- Add or tighten tests around frontmatter parsing and CLI conflict behavior.
- Add fixture checks that campaign records without `campaign_id` fail.
- Add registry audit checks for cross-layer subjects:
  - `hub_path` points to campaign hub when one exists.
  - `setting_hub_path` points to world hub when a world sibling exists.
  - using a world hub as campaign `hub_path` is either explicitly flagged as fallback or rejected.
- Add a slug-collision test where two campaign timelines share a slug and `campaign_id` selects the right one.
- Add a location-hierarchy regression fixture that documents whether parent location is required at route time or query time.

Good existing anchor:

- `evals/npc_corpus_recall_audit/npc_corpus_recall_audit.py` already inventories hubs, frontmatter location fields, `world_hub`, and `campaign_hub`. Extend this before inventing a new audit if it fits.

### Phase 3: Align Ingestion Surfaces

Goal: make all ingestion paths use one metadata contract.

Check these specific paths:

- `src/cli.py::compute_ingest_key_for_path`
- `src/cli.py::_cmd_ingest`
- `src/ingestion/chunker.py::chunk_document`
- `src/ingestion/frontmatter_inference.py::infer_frontmatter_metadata_heuristic`
- `tools/` or eval helpers that batch-ingest corpus files
- `evals/corpus_remote/build_remote_inventory.py::_infer_canon_layer`

Alignment rule:

- Prefer explicit frontmatter.
- Path inference is fallback only for manifest construction or legacy samples.
- Campaign IDs should use the project vocabulary: `longmont-c1`, `longmont-c2`.
- World-layer records must not carry `campaign_id`.
- Campaign-layer records must carry `campaign_id`.

If a code path intentionally uses a different campaign grouping (`campaign_1`, `campaign_unknown`, etc.), document whether it is a remote-inventory grouping key or a real `campaign_id`. Do not let both meanings share one field.

### Phase 4: Align Benchmarks

Goal: preserve current baseline value while making the hierarchy visible in failures.

Run or update deterministic benchmarks first:

```bash
uv run pytest tests/test_planner_turn_output_schema.py
uv run python evals/canon_layering/run_benchmarks.py
uv run python evals/llm_ingestion_slice/run_slice.py
uv run python evals/npc_corpus_recall_audit/npc_corpus_recall_audit.py
```

Then run the routing-only four-lane refresh only after a concrete routing or hierarchy change:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --ingest-routing-only \
  --retrieval-only \
  --corpus-root corpus/eldyrwild-markdown \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/<lane>.json
```

Use the documented 2026-05-08 routing-only baseline as the comparator:

- C1S1: 14/16, roster under-tagging.
- C1S2: 15/15, clean control.
- C1S3: 12/13, location hierarchy gap.
- C1S13: failing holdout, alias/identity bridge regression.
- Cost baseline: about `$0.136347` cohort sum; report any new run cost against this.

Do not summarize this as pass/fail only. Preserve the failure taxonomy.

### Phase 5: Update Docs Only Where They Drive Behavior

Update docs when the implementation settles a contract:

- If registry semantics are settled, update `Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md` and `Docs/CONVENTION-NPC-Hub-Package.md`.
- If path inference remains allowed for remote manifests, document the distinction in the relevant eval README or handoff.
- If location parent expansion is query-time behavior, update `Docs/Plans/DESIGN-Sentence-Routing-Stage-B-Hub-Routing.md` and the sentence-routing README.
- If route-time redundant parent tags are required, update the routing gold and explain why the duplication is intentional.

Do not write a completion report. Keep the handoff and conventions current.

## Acceptance Criteria

The pass is complete when:

- Core ingest rejects or flags world/campaign metadata violations consistently.
- Deterministic tests or evals prove campaign facts do not leak into world projection.
- Registry audit clearly distinguishes campaign hub authority from world fallback.
- Slug-collision writes are either campaign-disambiguated or explicitly blocked with a useful error.
- Routing benchmark docs and gold classify the C1S3 location case according to an explicit design choice.
- The four-lane routing-only baseline still has C1S2 as a clean control, or any loss is explained with artifact evidence.
- Any LLM-backed benchmark report includes cost and compares against the most recent baseline.

## Verification Commands

Run the narrowest command that proves the change, then broaden only when a shared contract moved.

Suggested deterministic set:

```bash
uv run pytest tests/test_planner_turn_output_schema.py
uv run python evals/canon_layering/run_benchmarks.py
uv run python evals/llm_ingestion_slice/run_slice.py
uv run python evals/npc_corpus_recall_audit/npc_corpus_recall_audit.py
git diff --check
```

If corpus files are edited, also run fingerprint hygiene:

```bash
uv run python -c "from pathlib import Path; from src.agent.planner_cache import corpus_fingerprint; print(corpus_fingerprint(Path('corpus/eldyrwild-markdown')))"
uv run pytest tests/test_lysandra_vertical_slice_step0.py
```

For LLM-backed routing reruns, report:

- artifact paths,
- pass shape by lane,
- exact violation strings for changed failures,
- cost per lane and cohort sum,
- comparison against the 2026-05-08 routing-only baseline.

## Known Risks

- **Gold deflation:** Do not edit gold to match current behavior unless the hierarchy decision supports that behavior.
- **Corpus migration creep:** Missing hubs are real gaps, but this handoff is not permission to create every hub.
- **Campaign-id drift:** `campaign_1` vs `longmont-c1` can silently split stores and evals.
- **Location hierarchy ambiguity:** parent-location expectations must be assigned to either route emission, query expansion, or hub metadata.
- **Prompt masking:** A prompt tweak can hide a metadata bug; prefer deterministic gates when the failure is structural.

## First Concrete Task

Start with `evals/npc_corpus_recall_audit/npc_corpus_recall_audit.py` and the two `_npc_registry.json` files. Produce an audit that answers:

- Which tracked NPCs have a campaign hub?
- Which tracked NPCs have a world hub?
- Which records use a world hub as `hub_path` because the campaign hub is missing?
- Which records should have `setting_hub_path` populated?
- Which records are ambiguous under the accepted decision?

That audit is the right first artifact because it exposes the hierarchy state without moving corpus files or paying LLM cost.
