# DungeonMindBuddy

DungeonMindBuddy is a narrative knowledge graph and canon-reduction project for
TTRPG campaign material. Its current product architecture is a persistent
**World Supergraph**: one durable graph per world, with campaign-scoped
assertions, evidence, chronology, visibility, and projections for every
product surface.

## Current product model

```text
source artifacts and authored records
  → extraction / authoring
  → GraphContribution + identity resolution
  → proposed immutable graph revision
  → validation and atomic graph-head advancement
  → campaign / focus / admissibility projection
  → Plan, Play, Build, Graph Review, and Agent Interaction
```

The graph owns identity, provenance, contribution history, and durable
assertions. Surfaces consume projections; they do not own graph state or
silently mutate canon. Agents are graph consumers with typed capabilities, not
privileged graph writers. Conversation history is continuity, not campaign
truth.

## Current state

The durable World Graph, Graph Kernel, source and agent contracts, initial
Eldyrwild publication, projection engine, graph-first Hermes reads, and the
human confirm/reload authority path are in place. The current whole-world
DungeonMind work has advanced from broad compatibility inventory to an exact,
source-grounded relationship residual ledger with descendant-safe effective
conformance. The next semantic write gap is assertion-granular correction:
fixing one adjudicated durable assertion without retiring unrelated assertions
from the same source contribution. Surface integration, candidate-path cleanup,
Play migration, and governed agent writes remain separate active or blocked
workstreams under the Campaign Supergraph tracker.

The current phase status and critical path are maintained in the
[Campaign Supergraph roadmap](Docs/Roadmaps/ROADMAP-campaign-supergraph.md).
The [PR tracker](Docs/Plans/PR-TRACKER-campaign-supergraph.md) is the sole
implementation sequence. For a concise operational snapshot of what is true
and what remains false, use the
[World Graph continuity state guide](Docs/Design/STATUS-world-graph-continuity-spine.md).

## Authority and design-agent sources

The root README is a product overview, not an architecture or sequencing
authority. Use these documents for current design work:

- [Campaign Supergraph architecture](Docs/Design/ARCHITECTURE-campaign-supergraph.md)
- [Campaign Supergraph roadmap](Docs/Roadmaps/ROADMAP-campaign-supergraph.md)
- [Campaign Supergraph PR tracker](Docs/Plans/PR-TRACKER-campaign-supergraph.md)
- [World Graph continuity state guide](Docs/Design/STATUS-world-graph-continuity-spine.md)
- [Shared surface-interaction architecture](Docs/Design/ARCHITECTURE-surface-interaction-layer.md)
- [Graph document audit](Docs/Reports/graph-document-audit.md)
- [Design-agent source manifest](Docs/Design/INDEX-design-agent-source-set.md)

The manifest is the checked-in entry point for the exact Project Sources to
attach, their authority classes, refresh rules, and exclusions. Project
Sources are user-managed inputs; when they conflict with the current GitHub
tree, GitHub wins.

For corpus locations, use
[`Docs/Anchors/CORPUS-ANCHOR.md`](Docs/Anchors/CORPUS-ANCHOR.md). Corpus prose
is campaign-private source material and is not a substitute for the graph
authority model.

## Repository structure

- `src/graph_memory/` — durable graph contracts, Kernel semantics, storage,
  contributions, identity, and projections
- `apps/` — product surfaces and server adapters
- `schemas/` — versioned contracts and examples
- `tests/` — contract, runtime, and integration tests
- `evals/` — extraction, graph, corpus, and acceptance evidence
- `corpus/` — local campaign source material; keep private
- `Docs/` — architecture, roadmap, process, audit, and evidence documents
- `out/` — generated artifacts (gitignored)

## Setup

This repository uses `uv` for Python dependency and environment management.

```bash
uv sync
```

For local OpenAI-backed commands, put `OPENAI_API_KEY` in a repo-root `.env` or
`.env.development` file. The CLI, eval harnesses, and pytest load it through
`src.bootstrap_env.load_dungeonmindbuddy_dotenv()`; do not export or print the
key. See `.cursor/rules/dungeonbuddy-environment.mdc`.

## Baseline verification

```bash
uv run ruff check .
uv run pytest tests/ --maxfail=1
uv run python evals/canon_layering/run_benchmarks.py
```

For documentation-only work, also run `git diff --check` and the link,
Markdown-hygiene, and authority scans described by the relevant handoff.

## Corpus inventory tooling

Remote inventory and normalization helpers remain under
`evals/corpus_remote/`, with the local wrapper at
`scripts/run_remote_snapshot_from_env.sh`. They support corpus operations;
they do not define World Supergraph authority or product graph context.
