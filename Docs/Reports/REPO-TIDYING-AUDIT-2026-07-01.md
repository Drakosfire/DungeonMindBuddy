# Repo Tidying Audit — DungeonMindBuddy

Date: 2026-07-01  
Branch: `audit/repo-tidying-map-2026-07-01`  
Scope: documentation-only audit and cleanup proposal; no runtime changes.

## Purpose

This report documents the current repository shape, identifies dated or ambiguous areas, and proposes a safe cleanup sequence. It is intended to support a future cleanup ladder, not to authorize broad deletes or hidden migrations.

The repo has grown from a pipeline-first graph/canon reducer into a mixed product workspace: Python graph-memory contracts and evals, FastAPI runtime consumers, Vite/React plan/play surfaces, corpus markdown, generated dogfood artifacts, handoff machinery, and several living design ladders. The cleanup goal should be to make those boundaries obvious without erasing useful dogfood history.

## Evidence reviewed

Primary repo files and docs inspected:

- `README.md`
- `pyproject.toml`
- `package.json`
- `apps/live-control-ui/package.json`
- `apps/live_control_server/main.py`
- `apps/live-control-ui/src/App.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx`
- `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`
- `apps/live-control-ui/src/agentInteraction/agentInteractionStorage.ts`
- `.gitignore`
- `Backlog.md`
- `report/REPORT-current-status.md`
- `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md`
- `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`
- `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`
- recent PR metadata, especially PRs #201 and #239–#248.

This audit was connector/search based rather than a local clone scan. Before deletion/move PRs, run a local inventory script to compute exact file counts, last-touch dates, imports, and references.

## Current repo map

### 1. Root project contract

Current root metadata says the repo is `dungeonmindbuddy`, Python `>=3.13`, with dependencies for Pydantic/jsonschema/OpenAI/FastAPI/uvicorn, plus frontend scripts delegated to `apps/live-control-ui`.

Root scripts:

```text
npm run dev      -> npm --prefix apps/live-control-ui run dev --
npm run build    -> npm --prefix apps/live-control-ui run build
npm run test:ui  -> npm --prefix apps/live-control-ui run test
```

Python verification still uses:

```text
uv run ruff check .
uv run pytest tests/ --maxfail=1
```

Problem: `README.md` still describes a pipeline-first repo with “no API or UI layer,” which no longer matches the existing FastAPI and React app surface.

### 2. Runtime apps

`apps/live_control_server/main.py` now exposes a FastAPI app named `DungeonMindBuddy Live Control` and includes routers:

- `routes/live.py`
- `routes/graph_preview.py`
- `routes/recap_ingest.py`
- `routes/party_registry.py`

The React app currently routes between:

- `/` launcher
- `/surface` / `/live-control`
- `/plan`
- `/tiptap-callout-spike`

The current `App.tsx` already wraps route content in `AgentInteractionProvider`, which aligns with the Plan Surface direction. However, `PlanSurfaceShell.tsx` still contains local `ProjectionProvider` and `AdaptiveProjectionContainer`, so projection ownership appears only partially migrated to the app-level interaction architecture.

### 3. Plan surface / agent interaction

The Plan Surface architecture says the durable target is:

- `/plan` as first intentional configured surface
- Surface as the top-level work abstraction
- one projection registry
- one adaptive container
- one edit capability
- one resolver
- one theme
- Agent Interaction as app-level continuity host

Current implementation appears mid-migration:

- `AgentInteractionProvider` is mounted app-wide.
- Provider owns thread/scope/pane state and localStorage-backed thread persistence.
- `agentInteractionStorage.ts` is a facade over existing `planSurface/components/agentInteractionHistory`, which is a sensible transition but leaves ownership naming backwards.
- Plan-specific shell still owns projection container/provider locally.

This is not wrong; it is a transitional seam. Cleanup should make the transition explicit and reduce the chance of a second projection stack hardening by accident.

### 4. Graph memory

`Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` is the strongest current path-boundary document.

Current intended ownership:

```text
src/graph_memory/                  durable graph-memory contracts and infrastructure
tests/fixtures/graph_memory/       deterministic contract fixtures
evals/graph_memory_layer/          proof machinery, dogfood, generated previews, comparison artifacts
apps/live_control_server/          runtime/API consumer of graph-memory contracts
apps/live-control-ui/              runtime/UI consumer of graph-memory contracts
```

Important current tension:

- The proven category-decomposed extraction pipeline still lives in `evals/graph_memory_layer/category_graph_model_study.py`.
- The runtime path still has a temporary bridge extractor under `src/graph_memory/extraction/preview_candidate_graph_extractor.py`.
- The documented next cleanup is to graduate `run_category_pipeline` or its product-shaped subset into `src/graph_memory/extraction/` behind explicit preview gates.

### 5. Corpus and derived artifacts

`Docs/Anchors/CORPUS-ANCHOR.md` says the canonical prose source is:

```text
corpus/eldyrwild-markdown/
```

Derived paths include:

- `_normalized/`
- `_breadcrumbed/`
- `_session_memory/`
- `_archive/`

Graph-memory docs explicitly say `_breadcrumbed` and `_session_memory` are compatibility/derived artifacts and should not be treated as the graph read model.

Cleanup should not delete derived corpus artifacts casually. The right move is to label, index, and gate them so agents stop treating them as canonical source by accident.

### 6. Evals and dogfood

The repo has accumulated several eval families:

- `evals/graph_memory_layer/`
- `evals/canon_layering/`
- `evals/corpus_remote/`
- `evals/c2_live_prep/`
- `evals/lysandra_vertical_slice/`
- `evals/mirathorn_vertical_slice/`
- `evals/session_events_extraction_vertical_slice/`
- sentence-routing / retrieval falsification work
- legacy ingestion slice outputs

The graph-memory project layout already separates “proof machinery” from durable contracts. That boundary should become the model for all eval cleanup.

### 7. Docs, plans, handoffs, and reports

Current docs are high-value but dense. There are several classes mixed together:

- Current architecture contracts in `Docs/Design/`
- Active plans/handoffs in `Docs/Plans/`
- Experiments/tracking in `Docs/Experiments/`
- Reports in `Docs/Reports/`
- Historical handoffs under `Docs/Plans/archive/...`
- Historical design/report archives under `Docs/Design/archive/...` and `Docs/Reports/archive/...`
- Agent transcripts under `Docs/Agent Transcripts/`
- Root status report under `report/REPORT-current-status.md`

Problem: the root status report is dated 2026-03-29 and is now materially stale relative to Plan Surface, Agent Interaction, and Graph Memory PRs.

### 8. Backlog

`Backlog.md` is current and very rich, but it is carrying deep narrative reports inline. That is useful for human continuity, but it also makes the file heavy and hard to scan.

Recommendation: keep the Backlog as the status index, but move long investigation writeups to `Docs/Reports/` and leave compact refs in Backlog.

## Main cleanup findings

### Finding A — README is stale and actively misleading

The README says current scope is schema contracts, reducer, remote corpus inventory, and that no API/UI layer is implemented. The repo now has FastAPI, Vite/React, Plan Surface, graph preview APIs, recap ingest APIs, Agent Interaction, and graph review workbench PRs.

Cleanup value: high. Risk: low.

Recommended fix:

- Rewrite README as a current orientation map.
- Keep the old pipeline-first material as “historical foundation” or move it into `Docs/Design/archive/` if still useful.
- Add explicit quickstart sections:
  - Python setup
  - backend server
  - frontend dev server
  - common tests
  - corpus caution / source-of-truth rules
  - where current architecture lives.

### Finding B — status report is stale

`report/REPORT-current-status.md` is useful but dated. It predates the current architecture shift and recent PRs.

Cleanup value: high. Risk: low.

Recommended fix:

- Move old root report to `Docs/Reports/archive/2026-03-29/REPORT-current-status.md` or leave it in place with a clear stale banner.
- Create a new `Docs/Reports/REPORT-current-status.md` or root `STATUS.md` that points to current workstreams:
  - Plan Surface
  - Graph Memory union supergraph
  - Agent Interaction
  - Corpus conventions
  - Backlog.

### Finding C — graph-memory boundaries are mostly documented; code should now follow them

The graph-memory layout doc is strong. The cleanup should enforce it:

- durable contracts in `src/graph_memory`
- deterministic fixtures in `tests/fixtures/graph_memory`
- proof/dogfood in `evals/graph_memory_layer`
- runtime adapters in apps

Cleanup value: high. Risk: medium if mixed with behavior changes.

Recommended fix:

- Keep this as a series of tiny PRs.
- Do not move extraction code and change extraction behavior in the same PR.
- First add import/package cleanup and path docs; then graduate product-ready extraction seams; then update runtime adapters.

### Finding D — Plan Surface migration is mid-state

Recent PRs have lifted Agent Interaction state into a provider, but the Plan shell still owns local projection pieces. That is acceptable as a transition, but it should be tracked as transition state.

Cleanup value: medium-high. Risk: medium because it touches frontend composition.

Recommended fix:

- Add a tracking note or update Plan Surface ladder status with “implemented / transitional / remaining.”
- Rename or relocate provider-owned storage away from `planSurface/components/agentInteractionHistory` once the provider is truly app-level.
- Hoist projection state/container only after tests prove no behavior drift.

### Finding E — eval artifacts and dogfood outputs need a consistent promotion/archive rule

`.gitignore` covers `out/`, many eval caches, and local generated outputs. But checked-in dogfood artifacts still exist and are sometimes useful. The repo needs a simple rule that tells agents when an artifact is:

- deterministic fixture
- checked-in review proof
- local/generated run output
- stale historical output
- forbidden-to-commit cache

Cleanup value: high. Risk: medium because deleting useful artifacts would hurt continuity.

Recommended fix:

- Add `Docs/CONVENTION-Eval-Artifacts.md`.
- Add per-eval README files where missing.
- Prefer archive stubs and indexes over deletion.

### Finding F — Backlog is doing too much

`Backlog.md` has become both an index and an investigation log.

Cleanup value: medium. Risk: low.

Recommended fix:

- Keep current top-level statuses in Backlog.
- Move long writeups to reports.
- Use compact entries with: status, surfaces-when, next action, refs.

### Finding G — corpus derived artifacts are correctly cautioned in docs, but repo structure still invites misuse

The corpus anchor says canonical prose is `corpus/eldyrwild-markdown`, and graph-memory layout says breadcrumb/session-memory are not the graph read model. Still, derived folders are close to canonical recaps and easy for agents to over-read.

Cleanup value: medium. Risk: medium if automation depends on current paths.

Recommended fix:

- Keep derived artifacts, but add local README/stub markers in derived folders where feasible.
- Add a lint/report command that flags direct references to `_breadcrumbed` and `_session_memory` outside approved legacy paths.
- Update README and agent rules to point to `Docs/Anchors/CORPUS-ANCHOR.md` first.

## Proposed cleanup sequence

### PR 1 — Repo orientation refresh

Type: docs-only  
Risk: low

Files:

- `README.md`
- maybe `STATUS.md` or `Docs/Reports/REPORT-current-status.md`

Work:

- Replace stale pipeline-only README with current repo map.
- Add “current surfaces and services” section.
- Add “where to put things” section that points to Graph Memory Project Layout and Corpus Anchor.
- Add command matrix:
  - backend
  - frontend
  - Python tests
  - UI tests
  - graph-memory focused tests.

Verification:

- Markdown-only review.
- Optional: confirm commands listed still exist in package configs.

### PR 2 — Documentation index and stale-report archive

Type: docs-only  
Risk: low

Files:

- `Docs/README.md` or `Docs/INDEX.md`
- `Docs/Reports/README.md`
- old `report/REPORT-current-status.md` handling

Work:

- Create a docs entrypoint with active docs vs historical docs.
- Mark March report stale or move it under archive with forward pointer.
- Define active docs:
  - Graph Memory Project Layout
  - Graph Memory Supergraph Roadmap
  - Plan Surface Toolbox
  - Source Vocabulary Contract
  - Corpus Anchor
  - Corpus Subject Schemas.

Verification:

- Link/path check if available; otherwise manual path existence check.

### PR 3 — Eval artifact convention

Type: docs + small ignore audit  
Risk: low-medium

Files:

- `Docs/CONVENTION-Eval-Artifacts.md`
- `.gitignore` only if obvious gaps are found
- per-eval README stubs only where needed

Work:

- Define artifact states: fixture, proof, generated-local, cache, stale-historical.
- Document when checked-in dogfood artifacts are allowed.
- Document required README metadata for eval directories.

Verification:

- No behavior changes.
- Grep for common generated-output paths and classify them.

### PR 4 — Graph-memory package/import cleanup

Type: code/package cleanup  
Risk: medium

Files likely under:

- `src/graph_memory/`
- `tests/fixtures/graph_memory/`
- import shims if any

Work:

- Follow the roadmap PR A: normalize `src/graph_memory` import layout.
- Do not change graph schemas or extraction behavior.

Verification:

```bash
python -m graph_memory.union_supergraph.validate
uv run pytest tests/test_graph_memory_* --maxfail=1
```

### PR 5 — Plan Surface transition note and naming cleanup

Type: frontend docs/code organization  
Risk: medium

Files likely under:

- `apps/live-control-ui/src/agentInteraction/`
- `apps/live-control-ui/src/planSurface/`
- Plan Surface docs/tracking

Work:

- Document what has moved app-level and what remains local.
- Consider moving `agentInteractionHistory` out of `planSurface/components` after provider ownership is complete.
- Do not hoist projection container in the same PR unless that is the scoped goal.

Verification:

```bash
cd apps/live-control-ui && npm test -- --run src/agentInteraction src/planSurface
cd apps/live-control-ui && npm run typecheck
```

### PR 6 — Backlog slimming pass

Type: docs-only  
Risk: low

Files:

- `Backlog.md`
- new or existing `Docs/Reports/*.md`

Work:

- Move long completed investigation narratives into reports.
- Leave compact active entries with direct refs.
- Do not lose accepted follow-up tasks.

Verification:

- Manual review only.

### PR 7 — Derived corpus marker pass

Type: docs + lint/report  
Risk: medium

Files:

- derived corpus folder READMEs if appropriate
- a report/lint script, not destructive cleanup

Work:

- Add markers explaining `_normalized`, `_breadcrumbed`, `_session_memory`, `_archive`.
- Add a non-mutating report command that surfaces direct usage of legacy derived paths.
- Do not move/delete derived corpus files in this PR.

Verification:

```bash
PYTHONPATH=. python scripts/build_corpus_index.py
# plus the new non-mutating report command, if added
```

## What not to do yet

- Do not delete checked-in dogfood artifacts until each has an explicit replacement or archive index.
- Do not collapse `evals/graph_memory_layer` into `src/graph_memory`; only durable contracts graduate.
- Do not move corpus derived folders as a cleanup shortcut.
- Do not combine README refresh, graph-memory import cleanup, Plan Surface projection hoisting, and Backlog slimming in one PR.
- Do not treat generated/session-memory artifacts as canon while tidying.
- Do not rename `/surface`, `/plan`, or live-play static routes until routing transition status is captured.

## Recommended immediate next action

Start with PR 1 and PR 2. They reduce confusion without touching behavior:

1. Refresh root README.
2. Create a docs index.
3. Mark or archive the stale March status report.

Then use that new orientation as the checklist for safer code cleanup PRs.
