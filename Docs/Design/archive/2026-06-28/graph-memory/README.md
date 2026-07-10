# Graph Memory Design Archive (2026-06-28)

Historical fixture, prototype, and early-experiment design notes moved during the graph-memory cleanup review. **Nothing was deleted.**

These docs remain useful for understanding how eval fixtures and static prototypes were specified. They are **not** the current architecture authority.

## Canonical docs (stay in `Docs/Design/`)

- `ARCHITECTURE-campaign-supergraph.md` — campaign supergraph architecture authority
- `GRAPH-MEMORY-PROJECT-LAYOUT.md` — path boundaries and authority map
- `GRAPH-MEMORY-MULTI-PASS-EXTRACTION-CONTRACT.md` — intended extraction contract (not yet runtime)
- `GRAPH-MEMORY-CANDIDATE-GRAPH-PREVIEW-IR.md` — candidate graph preview IR
- `GRAPH-MEMORY-SOURCE-SPAN-EVIDENCE-RESOLVER.md` — evidence resolver
- `GRAPH-MEMORY-LIVE-EXTRACTOR-OUTPUT-RECONCILIATION.md` — reconciliation contract

Roadmap and operational tracking: `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`, `Docs/Plans/PR-TRACKER-campaign-supergraph.md`.

Superseded architecture docs (2026-07-10): stubs in `Docs/Design/` and `Docs/Experiments/` point to `Docs/Archive/Architecture/`.

## Archived here

| File | Why archived |
|------|----------------|
| `EXPERIMENT-dungeonbuddy-graph.md` | Early experiment; superseded by supergraph roadmap |
| `GRAPH-MEMORY-EVAL-ONLY-EXTRACTOR-HARNESS-FIXTURE.md` | Eval fixture spec; covered by evals README |
| `GRAPH-MEMORY-RICH-RECAP-DOGFOOD-FIXTURE.md` | Dogfood fixture spec |
| `GRAPH-MEMORY-QUERY-VOCABULARY-FIXTURE.md` | Static vocabulary fixture |
| `GRAPH-MEMORY-STATIC-EXTRACTOR-OUTPUT-COMPARISON-REPORT.md` | Static comparison report fixture |
| `GRAPH-MEMORY-STATIC-PREVIEW-GRAPH-UI-PROTOTYPE.md` | Static HTML prototype spec |
| `GRAPH-MEMORY-PREVIEW-GRAPH-UX-*.md` | UX design/wireframe/component specs (pre-runtime UI) |
| `GRAPH-MEMORY-SESSION-23-RECAP-INGEST-FIXTURE.md` | Session 23 fixture spec |
| `GRAPH-MEMORY-SESSION-23-CANDIDATE-GRAPH-GOLD-FIXTURE.md` | Gold fixture spec (gold lives in `evals/`) |
| `GRAPH-MEMORY-SESSION-24-MANUAL-PROJECTION-DOGFOOD.md` | Manual projection dogfood spec |

Fixture JSON and gold graphs remain in `evals/graph_memory_layer/examples/`.
