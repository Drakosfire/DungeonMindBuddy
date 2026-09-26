# DungeonMindBuddy

DungeonMindBuddy is a narrative knowledge and campaign-operation product for
TTRPG material. Its durable World model remains one World per setting with
campaign-scoped assertions, evidence, chronology, visibility, and projections,
but durable World authority now lives in **DungeonMind**. DungeonBuddy owns the
GM-facing interaction, source/work surfaces, projections, and Agent product
boundary; **WorldKeeper** coordinates governed semantic World-change intent.

## Current product model

```text
source artifacts and authored records
  → Buddy extraction / authoring / reversible intent
  → WorldKeeper prepared semantic World change
  → explicit confirmation
  → DungeonMind validation + immutable World revision
  → Buddy campaign / focus / admissibility projection
  → Plan, Play, Build, Graph Review, and Agent Interaction
```

DungeonMind owns durable identity, provenance, contribution history, assertions,
revision/head authority, admission, and governed publication. WorldKeeper is a
thin change coordinator; it does not own durable identity or recovery.
DungeonBuddy surfaces consume and author through those boundaries rather than
owning World state. Agents are governed consumers/proposers, not privileged
World writers. Conversation history is continuity, not campaign truth.

Agent orchestration remains a DungeonBuddy product concern behind the
Buddy-owned `AgentRuntime` boundary. Hermes is the current production adapter
and PydanticAI remains a challenger/experiment; the next preferred harness
experiment is a thin `PiAgentRuntimeAdapter` over `pi-agent-core`, not a
migration of DungeonBuddy architecture into Pi. A future semantic-adjudication
layer may help with retrieval reranking, duplicate/entity alignment, assertion
verification, and tool preselection, but it must remain advisory rather than an
authority boundary. Jev / TypeSafe AI is the current research candidate for
that role, is not accessible to this project today, and creates no runtime or
dependency requirement.

## Current state

The World-model migration is complete: CUTOVER PR #667 removed the legacy Buddy
graph-engine ownership, and DungeonMind is the durable World authority. The
accepted source-to-World interaction boundary now places reversible product
intent and review UX in Buddy, semantic prepare/confirm coordination in
WorldKeeper, and durable identity/provenance/revision/publication in DungeonMind.
The old Campaign Supergraph tracker/status documents are retained as frozen
program records; they no longer authorize new dispatch. Current product
sequencing is workstream-specific (CON-READY, Play/Playable, Agent, UI, and
other explicitly active authorities).

The Plan/Build **DOGFOOD-POLISH** workstream closed on 2026-08-11 after
establishing the shared surface/document-authoring baseline. AppChrome now owns
persistent World Graph status and shared interaction hosts; a generic
`SurfaceContextHost` answers what each surface has loaded without learning
surface-specific semantics. Plan can select and intentionally create exact prep
workspace documents, including multiple distinct preps with the same session
affinity. Build no longer auto-creates a source on entry; it can select, create,
and rename exact worldbuilding sources while `MarkdownCanvasSession` remains
the sole content/revision/dirty-draft authority. Workspace `documentId` is the
opaque work-object identity; session affinity, graph lens, conversation
continuity, and document identity remain separate concepts.

The closeout deliberately leaves several product tracks open rather than
smuggling them into the finished workstream: Plan Ask continuity across prep
switches, shared Threat/Statblock projection and tool parity, Build lifecycle
and recovery UX, Play Surface Context, Hermes/graph-load performance, and
worldbuilding authority elevation. See
[DOGFOOD-POLISH closeout](Docs/Reports/DOGFOOD-POLISH-CLOSEOUT-2026-08-11.md)
for the completed PR chain and residual ownership.

The Campaign Supergraph roadmap/tracker/status set is now program history, not
whole-repository sequencing. The one remaining physical retirement is the
roadmap file itself; it is settlement-blocked while the current UI documentation
stack holds that path. Use the
[design-agent source manifest](Docs/Design/INDEX-design-agent-source-set.md)
to find current domain authorities, and the
[repository settlement report](Docs/Reports/REPORT-repository-settlement-2026-09-25.md)
for the exact retirement boundary.

## Authority and design-agent sources

The root README is a product overview, not an architecture or sequencing
authority. Use these documents for current design work:

- [Campaign / World model architecture](Docs/Design/ARCHITECTURE-campaign-supergraph.md)
- [Source-to-World authoring interaction](Docs/Design/DESIGN-source-to-world-authoring-interaction-contract.md)
- [Shared surface-interaction architecture](Docs/Design/ARCHITECTURE-surface-interaction-layer.md)
- [CON-READY stewardship anchor](Docs/Plans/STEWARDS-ANCHOR-con-ready.md)
- [CON-READY product roadmap](Docs/Roadmaps/ROADMAP-con-ready.md)
- [Playable/Play sequencing](Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md)
- [Graph/document authority audit](Docs/Reports/graph-document-audit.md)
- [E5A inference and knowledge boundary baseline](Docs/Reports/REPORT-E5A-buddy-boundary-baseline.md)
- [Agent context compilation decision](Docs/Design/DECISION-agent-context-compilation.md)
- [AgentRuntime and semantic-adjudication direction](Docs/Design/DECISION-agent-runtime-and-semantic-adjudication.md)
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

- `src/graph_memory/` — Buddy-side extraction, candidate/review, projection,
  retrieval, interaction, and compatibility helpers; durable World authority is
  owned by DungeonMind
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

## Local Play

Play stores Buddy application state in a **separate PostgreSQL logical
database**. It does not use the World Graph database, and FastAPI startup does
not create, migrate, or import that state.

1. Set `DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL` in repo `.env` or
   `.env.development` to a Buddy database such as
   `dungeonbuddy_application_state`.
2. Run `uv run python scripts/bootstrap_local_play.py apply` once (and again
   after application-state schema changes).
3. Start FastAPI and the Vite UI, then open `/play`.

See [`Docs/Runbooks/RUNBOOK-local-play-dogfood.md`](Docs/Runbooks/RUNBOOK-local-play-dogfood.md).
Inspect without mutating with
`uv run python scripts/bootstrap_local_play.py check`.

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
