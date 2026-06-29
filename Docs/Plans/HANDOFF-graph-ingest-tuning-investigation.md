# HANDOFF — Graph ingestion tuning, inspection & gap analysis

**Status:** READY — fresh-agent workstream kickoff
**Workstream:** Graph Memory / Recap Ingest — extraction *quality* (not plumbing)
**Author context:** Written 2026-06-29 after wiring "load prior ingestion" + "replace existing graph" into the Ingest tool and manually verifying Session 23 runs against gold.
**Audience:** A fresh agent whose sole job is to work *with the operator* on tuning, investigating, and documenting the graph ingestion flow.

---

## 0. Re-anchor block (read this first, do not re-derive from chat)

- **Branch:** `codex/graph-memory-preview-candidate-review-queue`
- **HEAD:** `b2e657b Add Party Registry spike with editable session rosters and graph anchor wiring.`
- **Uncommitted (this session, NOT yet committed):**
  - `apps/live-control-ui/src/modules/IngestionModule.tsx` + `.test.tsx` — "load prior ingestion" (resume from on-disk normalized recap) and "replace existing preview graph" (`force_graph_run`) controls.
  - `apps/live-control-ui/src/styles.css` — styling for the above.
  - `apps/live_control_server/routes/recap_ingest.py` + `apps/live_control_server/services/recap_graph_preview_ingest.py` — `force_graph_run` threaded through `generate_recap_memory` → `materialize_recap_preview_supergraph`.
  - `tests/test_live_recap_ingest_graph_preview_api.py` — reuse-vs-force tests.
- **Verification state:** `apps/live-control-ui` Vitest `IngestionModule.test.tsx` = 26/26 green; the two new backend tests (`test_generate_recap_memory_reuses_preview_graph_without_force`, `test_generate_recap_memory_force_graph_run_starts_new_preview_run`) = green.
- **Current-state hypothesis (verified, in words):** The Ingest tool can now (a) load a previously-processed session's normalized recap without re-pasting raw notes, and (b) force a fresh category-graph extraction run over it. Session 23 has five real graph-ingest runs on disk. The party registry wiring measurably improves **node** identity resolution but does **not** yet produce gold-style **edges** or **beats**. That edge/beat gap is the substance of this workstream.
- **Decide before committing:** whether to commit the uncommitted ingest-tool changes as-is or fold them into this workstream's first PR. (The operator has not asked to commit yet.)

---

## 1. Mission & the three goals

The operator wants to move ingestion *closer to gold* and measure the impact of changes (party registry was the first such change). Three explicit goals:

1. **Review / visualize / inspect** the changes in graph ingestion — a repeatable way to see what a run produced and how it differs from gold and from the previous run.
2. **Characterize stochasticity** — the 7-pass category extraction is LLM-driven; quantify how much output varies run-to-run for the *same* input, so we can tell signal (a real improvement) from noise.
3. **Deep-dive what is missed** and improve it — currently the big misses are **edges** and **beats** (see §3 baselines).

These are investigation + tuning goals, **not** a plumbing rewrite. The plumbing (resume, force re-extract, run registry) largely works now.

---

## 2. How the ingestion flow works today (mental model)

One-click path (`POST /api/live/recap-ingest`, `operation: generate_recap_memory`):

```
raw recap (optional; skipped when resuming)
→ stage + apply/normalize  (canonical + normalized recap on disk)
→ graph: source span bundle      (paragraph spans)
→ graph: 7-pass category extraction (LLM)   ← the quality-critical step
       actor → location → collective → object → thread → beat → edge
→ graph: consolidation (dedup + party-anchor injection)
→ graph: preview union store
→ graph: projection payload      (markdown + node mentions for the Recap View)
```

Key seams the fresh agent will touch:

| Concern | File |
|---|---|
| One-click orchestration, `force_graph_run` | `apps/live_control_server/routes/recap_ingest.py` (`_generate_recap_memory_from_request`) |
| Run reuse vs. fresh run, materialization | `apps/live_control_server/services/recap_graph_preview_ingest.py` (`materialize_recap_preview_supergraph`, `build_recap_graph_preview_bundle`) |
| The actual 7-pass extractor | `src/graph_memory/extraction/category_candidate_graph_extractor.py` |
| Pass prompts (read holistically; do NOT casually edit) | `src/graph_memory/extraction/` + `src/prompts/**` |
| Party anchors injected into prompts + post-extraction | `src/graph_memory/party_context.py`, `src/graph_memory/session_graph_context.py` |
| Run registry / discovery | `apps/live_control_server/services/graph_ingest_run_registry.py` |
| Ingest UI (resume, force re-extract, advanced dogfood) | `apps/live-control-ui/src/modules/IngestionModule.tsx` |
| Recap View / graph projection UI | `apps/live-control-ui/src/planSurface/graphPreview/*.tsx` |

Runs land under `out/graph_memory/runs/<campaign>/<session-id>/<UTC-timestamp>/` with a `graph_ingest_run_manifest.json` and sibling `candidate_graph.json`, `pass_telemetry.json`, `pass_outputs.json`, `consolidation_diagnostics.json`, `preview_union_supergraph.json`, `projection_payload.json`.

---

## 3. Verified current state — Session 23 (the baseline to beat)

**Gold fixture:** `evals/graph_memory_layer/examples/session_23_candidate_graph_gold/candidate_graph_gold.json`
Gold totals: **42 nodes / 21 edges / 14 beats / 16 proposed writes / 3 ignored / 6 deferred**. The gold is hand-authored and weighted toward **structural relationships** (`member_of` party roster, `located_in` containment, `governs`, `leads`, `parent_of`, `threatens`, `knows_about`).

**Runs on disk** (`out/graph_memory/runs/longmont-c2/session-23/`), oldest→newest, raw manifest counts:

| Run (UTC) | nodes | edges | evidence refs | Notes |
|---|---|---|---|---|
| `20260629T040747Z` | 12 | 8 | 35 | early |
| `20260629T040935Z` | 10 | 14 | 46 | early |
| `20260629T125244Z` | 48 | 20 | 81 | pre-party-registry |
| `20260629T125401Z` | 43 | 15 | 68 | pre-party-registry |
| `20260629T144508Z` | **56** | **19** | **91** | **latest — party registry active** |

**Identity-resolution scores vs gold** (via the repo's own comparator, tolerant path — see §4):

| Run | node_recall | edge_recall | beat_recall | node_precision_proxy |
|---|---|---|---|---|
| `125244` (pre-registry) | 0.262 | **0.0** | **0.0** | 0.229 |
| `125401` (pre-registry) | 0.262 | **0.0** | **0.0** | 0.256 |
| `144508` (registry) | **0.429** | **0.0** | **0.0** | 0.321 |

**What this proves (and does not):**

- ✅ The party-registry change is **real and measurable**: node recall jumped **0.26 → 0.43**. `consolidation_diagnostics.json` for the latest run shows `inserted_party_anchor_slugs` = baergrom, bonogo, caelynn, ephanna, karsemine, stafl (+ companions thrin_branchborn, captain_lysandra_ironveil) with resolved `corpus_ref` hub paths. Earlier runs had **0** corpus-ref node matches against gold; the latest has 8.
- ❌ **Edges and beats are at 0.0 recall** even under identity-resolution / predicate-family folding. The live extractor emits *generic* relations (`is in`, `arrived at`, `concerns`) and the gold wants *structural* ones (`member_of`, `located_in`, `governs`). The party anchors became **nodes** but never became **`member_of` party edges**.
- ❌ Live **beats** have `involved_node_ids: []` (empty), so beat matching has nothing to align on.

This is the deep-dive target: **the relationship/beat layer, not the node layer.**

---

## 4. Jumpstart resources — exact commands & files per goal

> All `python` commands below assume repo root and `.venv`. The live server (if you want UI/API) runs as:
> `export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_22 && uv run uvicorn apps.live_control_server.main:app --reload`
> UI: `cd apps/live-control-ui && npm run dev`.

### Goal 1 — Review / visualize / inspect runs

- **The comparator already exists:** `evals/graph_memory_layer/live_vs_gold_compare.py` (identity-resolution, predicate-family folding, candidate dedup) + CLI `evals/graph_memory_layer/report_live_vs_gold.py`.
- **⚠️ Known bug (fix early, it unblocks everything):** the CLI's strict path crashes on live runs:
  ```
  TypeError: SemanticState.__init__() got an unexpected keyword argument 'canon_status'. Did you mean 'canon_state'?
  ```
  Live extractor output uses `semantic_state: {canon_status, lifecycle, memory_status}` while `CandidateGraphPreview` / gold use `{canon_state, lifecycle_state, ...}`. The **tolerant path bypasses this**:
  ```python
  from evals.graph_memory_layer.live_vs_gold_compare import compare_parts, parts_from_raw_graph
  import json
  from pathlib import Path
  gold = json.loads(Path("evals/graph_memory_layer/examples/session_23_candidate_graph_gold/candidate_graph_gold.json").read_text())
  live = json.loads(Path("out/graph_memory/runs/longmont-c2/session-23/20260629T144508Z/candidate_graph.json").read_text())
  rep = compare_parts(parts_from_raw_graph(live), parts_from_raw_graph(gold))
  print(rep["scores"]); print(len(rep["soft_misses"]), "soft misses")
  ```
  **First task candidate:** reconcile the `semantic_state` schema (extractor output vs `CandidateGraphPreview`) OR make `candidate_graph_preview_from_dict` tolerant, then make `report_live_vs_gold.py` work on any `out/graph_memory/runs/.../candidate_graph.json`. That single fix turns the CLI into a per-run scorecard.
- **Run inventory via API** (server running): `GET /api/live/graph-preview/graph-ingest/runs?campaign_id=longmont-c2&session_id=session-23` returns every run with status + counts. `GET /api/live/graph-preview/artifacts?campaign_id=longmont-c2` is the recap-artifact registry behind the Ingest dropdown.
- **Static HTML graph visualizer prototype** (no network, inspectable): `evals/graph_memory_layer/static_preview_graph_ui_prototype.py` →
  `evals/graph_memory_layer/examples/static_preview_graph_ui_prototype/session_23_preview_graph_ui_prototype.html`. Good reference for an explorer view (nodes/edges/beats with evidence + risk columns).
- **In-product Recap View / graph chips:** `apps/live-control-ui/src/planSurface/graphPreview/` (`RecapGraphModule.tsx`, `UnionSupergraphRecapProjection.tsx`, `GraphNodePresentation.tsx`). Deep link: `/plan?tool=recap&session=session-23`.
- **Benchmark review canvas convention** (if you want a rich side-by-side review surface): skill `.cursor/skills/benchmark-review-canvas/SKILL.md` + `/home/drakosfire/.cursor/skills-cursor/canvas/SKILL.md`. A "run vs gold vs previous-run" canvas is a strong fit for Goal 1.

### Goal 2 — Characterize stochasticity

- **Multi-run cohort runner already exists:** `evals/graph_memory_layer/run_category_graph_model_study.py` (`--models ... --n N` runs N times per model, writes per-run `comparison_report.json` + `run_summary.json` + `cohort_summary.json`).
  ⚠️ It is currently **hard-gated to session 22** (`if args.session != 22: sys.exit(2)`). Generalizing it to session 23 (or any session with a gold fixture) is a natural Goal-2 task.
- **Prior evidence of variance:** `evals/graph_memory_layer/artifacts/category_graph_model_study/2026-06-26/anchor_quote_n3/` holds an n=3 `gpt-5.4-mini` cohort for S22 (node recall ~0.80–0.88). Read `cohort_summary.json` for the shape of a variance report.
- **Cheapest path to a stochasticity signal without new code:** use the now-working Ingest "Replace existing preview graph" toggle (or `force_graph_run: true`) to produce K runs of Session 23 from the *same* normalized recap, then score each with the §4-Goal-1 comparator and report mean/stdev/min/max per metric. The five existing runs are already a (confounded) starter sample — but they mix pre/post party-registry, so treat them as illustrative only; generate a clean same-config cohort for real numbers.
- **Cost discipline:** each full 7-pass run ≈ `$0.05` (see `health.estimated_cost_usd` in the latest manifest). A K=10 cohort is ~`$0.50`. Report token/dollar cost in any cohort summary (`cost-as-signal.mdc`).

### Goal 3 — Deep-dive what is missed

- **Where the misses are enumerated:** `compare_parts(...)["soft_misses"]` lists every missing gold node/edge/beat with id + label. The static sample report `evals/graph_memory_layer/examples/static_extractor_output_comparison_report/session_23_static_comparison_report.json` shows the same shape (node_recall 0.79 / edge_recall 0.095 on that sample) and is a good template for a written gap report.
- **The two concrete gaps already isolated:**
  1. **No party `member_of` / structural edges.** Party PCs exist as nodes with corpus refs but the `edge_pass` does not emit `member_of <party>` (gold expects 7). The party anchors are injected at consolidation but a "Heroes / party" collective node + roster edges are not. Investigate: does `party_context` inject a party *node*? Does the `edge_pass` prompt know the roster? (`src/graph_memory/extraction/category_candidate_graph_extractor.py`, the edge pass + `party_context.py`.)
  2. **Empty `involved_node_ids` on beats** kills beat recall. The `beat_pass` emits beats with evidence spans but no node linkage; the comparator's `beat_match_score` needs endpoints. Investigate the beat pass output contract vs `src/graph_memory/identity_resolution.py: beat_match_score`.
- **Gold authoring rationale** (so you tune toward the *right* target, not just higher numbers): the gold manifest `notes[]` in `evals/graph_memory_layer/examples/session_23_candidate_graph_gold/session_23_candidate_graph_gold_manifest.json` explains the edge-layer philosophy (durable structural/semantic relationships; moment-to-moment combat stays in beats, not edges) and the corpus-resolvability model for entities.
- **Reference contracts:** `evals/graph_memory_layer/examples/multi_pass_extraction_contract/` (broader 9-pass design) and `evals/graph_memory_layer/FIXTURE-STATUS.md`.

---

## 5. Reproduce the operator's loop

To re-run Session 23 ingestion and measure impact (the loop the operator just did manually):

1. **Server + UI up** (commands in §4 header).
2. **Ingest tool** (`/plan` → Raw Recap Ingestion): "Load prior ingestion" → pick Session 23 → "Load processed recap" (loads on-disk normalized recap, no raw paste).
3. Check **"Replace existing preview graph"** → click **"Replace preview graph (re-extract)"**. This issues `generate_recap_memory` with `force_graph_run: true` and writes a new timestamped run.
4. **Score the new run** with the §4-Goal-1 comparator against gold; diff against the prior run's scores.

API-only equivalent (no UI), once a normalized recap exists on disk:

```bash
curl -sS -X POST http://127.0.0.1:8766/api/live/recap-ingest \
  -H 'content-type: application/json' \
  -d '{"operation":"generate_recap_memory","campaign_id":"longmont-c2","session":23,
       "title":"Session 23 - Mireward Gate Battle","check":true,
       "include_graph_extraction":true,"include_legacy_breadcrumb":false,
       "graph_model_id":"gpt-5.4-mini","force_graph_run":true}'
```

(Port matches whatever uvicorn bound — the operator's session used 8766.)

---

## 6. Suggested first session (proposed, confirm with operator)

1. **Unblock the scorecard (Goal 1):** fix the `semantic_state` schema drift so `report_live_vs_gold.py` runs on any live run; add a tiny "score this run dir" wrapper that prints the metric table + writes a `comparison_report.json` next to the candidate. *Falsifiable:* CLI prints non-crashing scores for `20260629T144508Z`.
2. **Same-config cohort (Goal 2):** generalize `run_category_graph_model_study.py` past the S22 gate (or script K forced re-extracts), produce a clean K≥5 Session 23 cohort at `gpt-5.4-mini`, report mean/stdev per metric + dollar cost. *Falsifiable:* a `cohort_summary.json` with variance bands.
3. **Edge/beat gap write-up (Goal 3):** from the soft-miss lists, document why `member_of`/structural edges and node-linked beats are absent, propose one targeted change (prompt or party-node injection), and predict its effect before running. *Falsifiable:* edge_recall or beat_recall moves off 0.0 on a re-extract.

Do these in the **plan-then-delegate** pattern (`.cursor/rules/subagent-delegation.mdc`): design with the operator using the strong model; hand mechanical edits to `composer-2` with explicit file allowlists; verify by re-running the comparator yourself.

---

## 7. Guardrails (non-negotiable)

- **Corpus is real-person PII** (`.cursor/rules/corpus-pii-and-llm-payloads.mdc`): never paste recap/corpus prose, player names, or run artifacts into `WebSearch`/`WebFetch` or any external tool. Keep `evals/**/artifacts/**` local. When quoting misses in chat, prefer ids + labels over prose.
- **Responses API + json_schema for any extraction change** (`.cursor/rules/responses-api-structured-extraction.mdc`): no prompt-only JSON.
- **Model policy** (`MODEL_POLICY.json`, `model-policy.mdc`): resolve models via policy roles; request overrides (`graph_model_id`) still win. Default graph extract model in the live path is `gpt-5.4-mini`.
- **Prompt files** (`src/prompts/**`, the extraction passes): read the *whole* numbered pass workflow before editing; an insertion shifts how the LLM reads neighbors. Do not casually "improve" adjacent passes.
- **No time estimates** (`no-time-estimates.mdc`): rank work by scope/dependencies/falsifiability and dollar/token cost, not hours.
- **Don't commit** the §0 uncommitted changes or any run artifacts under `out/graph_memory/runs/` or `evals/**/artifacts/**` unless the operator asks.

---

## 8. References

- Dogfood friction log (items #1–#10, the product gaps this workstream sits on top of): `Docs/Plans/GRAPH-MEMORY-RECAP-INGEST-DOGFOOD-NOTES.md`
- Prior implementation handoff (graph-first ingest, category pipeline rationale): `Docs/Plans/HANDOFF-graph-first-recap-ingest.md`
- Workstream anchor + layout: `Docs/Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md`, `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md`
- Fixture status: `evals/graph_memory_layer/FIXTURE-STATUS.md`
- Re-anchor discipline (for the next session bridge): `.cursor/rules/anchor.mdc`
