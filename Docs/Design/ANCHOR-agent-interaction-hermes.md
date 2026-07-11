# Anchor — Agent Interaction + Hermes

**Status:** Active anchor, re-anchored after local `/plan` P3.1 dogfood
**Created:** 2026-06-23
**Re-anchored:** 2026-06-26
**Scope:** Agent Interaction roadmap, Hermes-backed prep conversation, source-grounded trust surfaces, graph-safe retrieval boundary
**Parent:** `Docs/Design/ANCHOR-plan-surface-agent-interaction.md` (surface ladder, R10/P4 provider lift, ingestion vocabulary)

Start here to re-anchor or jumpstart an agent on **Agent Interaction as DungeonBuddy's GM companion**. This document is intentionally about the product interaction layer, not graph-memory infrastructure.

---

## Executive summary

Agent Interaction is becoming DungeonBuddy's app-level GM companion. The local `/plan` implementation has now dogfooded the conversational ladder through **P3.1**:

- The GM can ask natural-language campaign questions.
- Answers are corpus-grounded and can include citation cards.
- Citations can open a read-only source reader inside the Agent Interaction pane.
- Prep can happen in named local threads.
- Same-thread follow-up plumbing and thread context exist.
- Retrieval freshness is visible through `retrieval_freshness` and `RetrievalFreshnessPanel`.
- Older cited answers can run metadata-only source-currentness checks through `/api/live/citation-freshness` and `CorpusChangeSignalPanel`.

The implementation remains **local to `/plan`**. The next likely code rung is **R10 / P4: lift Agent Interaction state ownership into an app-level `AgentInteractionProvider` while preserving the current `/plan` UX**. React `/play` follows R10/P4 as the second-surface proof.

Hermes long-term memory remains **future and pointer-only continuity** — not campaign authority. Operator tool parity and proposal-bound write-preview flows remain **future** (contract in `Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md`; runtime implementation is PR011, not landed). Runtime graph retrieval remains **out of scope** for this workstream; future graph-backed retrieval must be consumed through source-vocabulary adapters.

**Dual authority:** corpus/source artifacts are **prose and evidentiary authority**; the World Supergraph head is **durable materialized knowledge state**; governed authored assertions and identity decisions survive reconstruction; Hermes/UI/thread memory is **non-canonical continuity** (pointer-only). Agents are not privileged writers.

---

## Roadmap status

| Phase | Status | Notes |
|-------|--------|-------|
| **P0 — conversational core** | Landed locally | Thread/turn model, same-thread follow-up, local persistence, trace toggle, Hermes session seam. |
| **P1 — citation trust surface** | Landed locally | Answer-first UI, citation cards, Open source action, in-pane source reader. |
| **P1.1 — source reader hardening** | Landed locally | Source endpoint OpenAPI/test coverage, allowlist, safe read-only lookup. |
| **P2.0 — named threads** | Landed locally | Thread index, create/rename/switch/delete, per-thread active state. |
| **P2.1 — thread quality** | Landed locally | Long-thread suggestion with explicit Start new thread / Keep going and persistence. |
| **P3.0 — retrieval freshness** | Landed locally | `retrieval_freshness` response object and `RetrievalFreshnessPanel`. |
| **P3.1 — corpus change signal** | Landed locally | `/api/live/citation-freshness`, `CorpusChangeSignalPanel`, evidence snapshots, metadata-only source-currentness checks. |
| **P4 / R10 — provider lift** | Future / next likely code rung | Move Agent Interaction state ownership above routes/surfaces while preserving current `/plan` UX. |
| **P5 — operator tool parity** | Future | Same-thread tool use beyond retrieval; typed capability categories (`read_only`, `draft_only`, `preview_write`, `confirm_commit`, `admin_diagnostic`); durable writes via preview_write → proposal-bound GM confirm → GraphContribution / Kernel / atomic graph-head (see PR005B contract). |
| **P6 — Hermes memory integration** | Future | Hermes long-term memory can help continuity/preferences only (pointer-only); campaign facts come from source artifacts and World Supergraph reads, not chat memory. |

There is no active Agent Interaction anchor where P0 is the next slice. P0-P3.1 are already landed locally in `/plan`.

---

## Target app shape

```text
AppChrome
  AgentInteractionProvider
    Route / Surface
      PlanSurfaceShell
      PlaySurfaceShell
      BuildSurfaceShell (future)

  AgentInteractionBar
  AgentInteractionPane
```

Surfaces publish ambient context. The provider owns continuity. Provider persistence stores **pointer-only continuity**: locators, summaries, thread metadata, citation locators, evidence snapshots, retrieval decision metadata, and tool-run proof pointers — **not** corpus bodies, normalized recap text, graph internals, raw prompts, unbounded source excerpts, or accepted graph truth.

---

## Trust surfaces to preserve

Current `/plan` trust surfaces include:

- Citation cards and the citation source reader.
- `RetrievalFreshnessPanel` for retrieval-decision metadata.
- `CorpusChangeSignalPanel` for compact source-currentness status.
- `GET /api/live/citation-source` for allowlisted read-only source lookup.
- `POST /api/live/citation-freshness` for metadata-only citation freshness checks.
- `retrieval_freshness` on live query responses.
- Evidence snapshots and source-line hashes as metadata-only checks.

These trust surfaces are adapter-compatible with future graph-backed retrieval because they store locators, hashes/status metadata, and retrieval decisions rather than graph internals or source bodies.

---

## Source-vocabulary and graph boundary

Agent Interaction consumes source-grounded envelopes:

```text
SourceArtifact -> SourceAnchor -> SourceUnit
```

Agent Interaction must **not** consume or persist:

- Graph internals.
- Graph summaries as source evidence.
- Raw ingestion internals.
- Corpus bodies.
- Raw prompts.
- Unbounded source excerpts.

Graph/ontology work is sibling derived-semantics infrastructure. It may eventually enrich or produce the same `SourceUnit` envelope through adapters, but graph summaries are navigational display material, not source evidence. No production retrieval behavior should depend on graph output until shadow-mode evidence and promotion gates exist.

---

## User-story anchors

Full catalog: `Docs/Design/UX-STORIES-agent-interaction-hermes.md`.

1. **Prep Q&A:** satisfied locally in `/plan`; future work hardens Hermes steady-state and cite-or-abstain policy.
2. **Same-thread follow-up:** partially satisfied locally; future work matures Hermes session continuity and re-retrieval policy.
3. **Parallel prep arcs:** satisfied locally with named thread operations; app-level persistence/cross-surface continuity waits for R10/P4.
4. **Citation trust:** satisfied locally with citation cards and hardened source reader; policy hardening remains future.
5. **Source freshness:** satisfied locally with P3.1 metadata-only checks and Current / Changed / Unknown / Unavailable states.
6. **Cross-surface continuity:** future; this is the R10/P4 provider lift.
7. **Graph-safe retrieval:** boundary exists now; graph-backed retrieval adapters remain future.

---

## Runtime path index

### Frontend

| Path | Role |
|------|------|
| `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` | Current `/plan` bar/pane shell, ask flow, history, thread UI, citation actions. |
| `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts` | Local thread/turn persistence. |
| `apps/live-control-ui/src/planSurface/components/RetrievalFreshnessPanel.tsx` | P3.0 retrieval freshness trust panel. |
| `apps/live-control-ui/src/planSurface/components/CorpusChangeSignalPanel.tsx` | P3.1 corpus change signal UI. |
| `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | `/plan` Agent Interaction coverage. |
| `apps/live-control-ui/src/api/types.ts` | API response and Agent Interaction types. |
| `apps/live-control-ui/src/api/liveApi.ts` | Live query, citation source, citation freshness API calls. |
| `apps/live-control-ui/src/planSurface/planSurface.css` | Agent Interaction bar/pane styling. |

### Backend

| Path | Role |
|------|------|
| `apps/live_control_server/services/live_agent_loop.py` | Live/Hermes query loop, retrieval metadata, response shaping. |
| `apps/live_control_server/services/citation_source_reader.py` | Safe read-only citation source lookup. |
| `apps/live_control_server/services/citation_freshness.py` | Metadata-only source-currentness checks. |
| `apps/live_control_server/routes/live.py` | `/api/live/query`, `/api/live/citation-source`, `/api/live/citation-freshness`. |
| `tests/test_live_control_server.py` | Server route and response coverage. |
| `src/live_play/source_bundle.py` | `SourceArtifact -> SourceAnchor -> SourceUnit` ingestion proof bundle. |

### Hermes/plugin

| Path | Role |
|------|------|
| `.hermes.md` | Hermes policy: corpus canon, memory rules, plugin install. |
| `integrations/hermes/plugins/dungeonbuddy/__init__.py` | DungeonBuddy corpus lookup plugin. |
| `integrations/hermes/plugins/dungeonbuddy/skills/dungeonbuddy-corpus-qa/SKILL.md` | Corpus Q&A skill; cite-or-abstain hardening target. |
| `scripts/hermes_spike_install_plugin.sh` | Local Hermes plugin install helper. |

### Graph/ontology surfaces to know but not consume directly

- `src/graph_memory/**`
- `evals/graph_memory_layer/**`
- `tests/test_graph_memory_*.py`
- `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md`
- `Docs/Design/ANCHOR-dungeonBuddy-graph-retrieval.md`

---

## Invariants

1. `/plan` is a consumer, not graph infrastructure.
2. `AgentInteractionProvider` should eventually live above routes/surfaces in `AppChrome`.
3. Agent Interaction stores pointers, summaries, thread metadata, citation locators, evidence snapshots, retrieval decision metadata, and tool-run proof pointers.
4. Agent Interaction must not store corpus bodies, normalized recap text, graph internals, raw prompts, or unbounded source excerpts.
5. Source vocabulary remains `SourceArtifact -> SourceAnchor -> SourceUnit`.
6. Ontology/taxonomy owns derived semantics, controlled vocabulary, graph IR, validation, reports, deterministic materialization, and later shadow retrieval.
7. Graph outputs should eventually enrich or produce the same `SourceUnit` envelope.
8. Graph summaries are navigational display material, not source evidence.
9. **Dual authority:** corpus/source artifacts are prose and evidentiary authority; the World Supergraph head is durable materialized knowledge state; governed authored assertions and identity decisions survive reconstruction; Hermes/UI/thread memory is non-canonical continuity (pointer-only).
10. No production retrieval behavior should depend on graph output until shadow-mode evidence and promotion gates exist.
11. **Agents are not privileged writers.** Durable writes use typed capability categories (`read_only`, `draft_only`, `preview_write`, `confirm_commit`, `admin_diagnostic` per `Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md`): preview_write proposal → explicit **proposal-bound / revision-bound** GM confirm → GraphContribution / Kernel / atomic graph-head. No autonomous writes. Graph Review/Ingest is the correction cockpit; Plan is a consumer surface that may draft and launch preview_write.
12. Runtime PR011 tool registry is **not** implemented; this anchor describes product direction and local `/plan` dogfood only.

---

## Verification for docs-only re-anchors

```bash
rg -n "Next slice to implement|Not done|P0|P1|P2|P3|P4|R10|retrieval_freshness|citation-freshness|CorpusChangeSignal|SourceArtifact|SourceAnchor|SourceUnit|ontology|taxonomy|graph" Docs/Design Docs/Experiments Docs/Plans
rg -n "AgentInteractionProvider|SourceArtifact|SourceAnchor|SourceUnit|retrieval_freshness|citation-freshness|evidence_snapshots|CorpusChangeSignalPanel" Docs/Design Docs/Experiments Docs/Plans
```

If only docs changed, no full UI/backend suite is required.
