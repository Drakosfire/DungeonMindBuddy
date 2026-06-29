# Graph Memory Project Layout

This note records the current path boundary for graph-memory work. It is intentionally short: durable contracts should be easy to find without turning evaluation directories into architecture owners.

**Canonical anchors:** [`GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md`](GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md) · [`GRAPH-MEMORY-WORKSTREAM-ANCHOR.md`](../Experiments/GRAPH-MEMORY-WORKSTREAM-ANCHOR.md)

## Boundaries

- `src/graph_memory`: reusable graph-memory contracts, validators, reports, read-model helpers, and infrastructure.
- `tests/fixtures/graph_memory`: deterministic fixture data for reusable graph-memory contracts and tests.
- `evals/graph_memory_layer`: evaluation harnesses, benchmark fixtures, prompt dogfood, comparison reports, generated previews, and static review artifacts.
- `apps/live_control_server` / `apps/live-control-ui`: runtime/API/UI consumers of graph-memory contracts.

## Authority map (2026-06-28 cleanup)

### Active runtime (graph-first target)

| Path | Role |
|------|------|
| `apps/live_control_server/routes/recap_ingest.py` | Recap ingest API orchestration (`generate_recap_memory`, graph hooks) |
| `apps/live_control_server/services/recap_graph_preview_ingest.py` | Preview graph-ingest bundle build + union materialization |
| `apps/live_control_server/services/graph_ingest_run_registry.py` | Discover graph-ingest run manifests |
| `apps/live_control_server/services/union_supergraph_projection_adapter.py` | Build projection payload from union store |
| `apps/live_control_server/routes/graph_preview.py` | Graph preview API for `/plan` and ingest UI |
| `apps/live-control-ui/src/modules/IngestionModule.tsx` | One-click recap + graph projection UI |
| `evals/graph_memory_layer/graph_preview_runner.py` | Source-span bundle + candidate extraction runner (used by runtime) |
| `evals/graph_memory_layer/category_graph_model_study.py` | **Proven** category-decomposed extraction (`run_category_pipeline`); target for product runtime |
| `src/graph_memory/extraction/preview_candidate_graph_extractor.py` | **Temporary bridge** — single compact GPT call (~12-node cap); not the quality path |

**Proven extraction pipeline** (category study, `anchor_quote_n3` n=3 on Session 22, `gpt-5.4-mini`, node recall ~0.80–0.88):

```text
normalized recap
→ source span bundle (paragraph spans)
→ 5 category node passes (actor, location, collective, object, thread)
→ beat pass
→ edge pass (node list injected)
→ deterministic consolidate + assemble → live-extractor envelope
→ candidate validation
→ preview union store materialization
→ projection payload (recap chips / node views)
```

**What one-click ingest runs today** (stub until category pipeline is wired):

```text
normalized recap → source spans → preview_candidate_graph_extractor (single gpt-5-mini call, ~12-node cap) → …
```

### Durable graph contracts (`src/graph_memory`)

| Subpath | Role |
|---------|------|
| `union_supergraph/` | Union supergraph model, load, validate, preview import/materialize |
| `projection/` | Recap projection, focus overlay, node view |
| `ingestion/` | Graph ingest run manifest, validation |
| `evidence/` | Source artifact, evidence ref, source domain |
| `extraction/` | Preview candidate graph extractor (stub; graduate `run_category_pipeline` here) |
| `candidate_graph_preview.py` | Candidate graph preview IR helpers |

### Proof / eval only (`evals/graph_memory_layer`)

| Bucket | Paths | Status |
|--------|-------|--------|
| Active validators | `validate_*.py`, `report_*.py` at eval root | Contract gates and diagnostic reports |
| Manual gold fixtures | `examples/session_23_candidate_graph_gold/`, `examples/session_24_manual_projection_dogfood/` | Hand-authored gold; **not** runtime extractor output |
| Category-decomposed extraction (proven, eval harness) | `category_graph_model_study.py`, `artifacts/category_graph_model_study/2026-06-26/anchor_quote_n3/` | 7-pass pipeline (5 category node + beat + edge); **target for product runtime** |
| Multi-pass contract (design reference) | `examples/multi_pass_extraction_contract/`, `examples/eval_only_extractor_harness/` | Broader 9-pass contract sketch for Session 23; category study is the graduated slice |
| Preview compact extractor (runtime stub) | `src/graph_memory/extraction/preview_candidate_graph_extractor.py` | Single-call bridge wired today; replace with category pipeline |
| Generated graph runs | `artifacts/graph_ingest_runs/`, `out/graph_memory/runs/` | Local/generated; gitignored or artifact-only |
| Static UI prototypes | `examples/static_preview_graph_ui_prototype/` | Review-only HTML |
| Live extractor harness | `examples/live_extractor_prompt_harness/`, `runs/live_extractor_prompt_harness/` | Manual prompt render + untrusted candidate output |

See [`evals/graph_memory_layer/README.md`](../../evals/graph_memory_layer/README.md) for command inventory.

### Legacy breadcrumb / session-memory (compatibility)

Graph projection is replacing breadcrumbing as the primary recap-memory surface. These paths remain for old ingest steps and corpus compatibility:

| Path | Role |
|------|------|
| `src/live_play/recap_ingest_pipeline.py` | Stage/apply/normalize/breadcrumb/materialize orchestration |
| `scripts/materialize_session_memory.py` | Session memory JSONL materializer |
| `corpus/.../Session Recaps/_breadcrumbed/` | Breadcrumbed recap derivatives |
| `corpus/.../Session Recaps/_session_memory/` | Derived session memory records |
| `corpus/.../Session Recaps/_normalized/` | Normalized recap (still input to graph extraction) |

**Do not treat** `_breadcrumbed` or `_session_memory` as the graph read model. They are legacy derived artifacts.

### Generated / local outputs

| Path | Role |
|------|------|
| `out/graph_memory/runs/` | Runtime graph-ingest run output (local, may be empty in repo) |
| `evals/graph_memory_layer/artifacts/graph_ingest_runs/` | Checked-in dogfood run artifacts (e.g. Session 24 manual projection) |
| `evals/graph_memory_layer/runs/` | Gitignored live harness outputs |

## Current relocation proof

The union supergraph read-model validator and report live under `src/graph_memory/union_supergraph`, while the checked-in minimal contract fixture lives under `tests/fixtures/graph_memory/union_supergraph`. This keeps the durable read-model contract outside evaluation-only space while leaving benchmark and dogfood machinery in `evals/graph_memory_layer`.

## Historical docs

Superseded fixture/prototype design notes and one-off gate reports live under:

- `Docs/Design/archive/2026-06-28/graph-memory/`
- `Docs/Reports/archive/2026-06-28/graph-memory/`

See each archive's `README.md` for what was moved and why.

## Roadmap pointer

`Docs/Design/GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md` is the current architecture roadmap for this layout. It treats this file as the short boundary note and records the longer target hierarchy, lifecycle, and PR sequence for graduating reusable contracts into `src/graph_memory`.

## Follow-up implementation

Graph-first recap ingest (skip breadcrumb gating for graph projection): see `Docs/Plans/HANDOFF-graph-first-recap-ingest.md`.
