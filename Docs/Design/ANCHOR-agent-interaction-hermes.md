# Anchor — Agent Interaction + Hermes

**Status:** Active anchor  
**Created:** 2026-06-23  
**Updated:** 2026-06-26  
**Scope:** Plan-mode Agent Interaction bar/pane, Hermes-backed conversation, manifest retrieval, local thread UX, citation/source trust surfaces, graph-aligned source-vocabulary consumption  
**Parent:** `Docs/Design/ANCHOR-plan-surface-agent-interaction.md` (surface ladder, R10/R11, ingestion vocabulary)

Start here to re-anchor or jumpstart an agent on **conversational Hermes prep** — not chat-history reconstruction and not graph-memory implementation.

---

## Executive summary

**What it is:** A bottom **Agent Interaction** surface on `/plan` where the GM preps at the desk before session and reviews after ingestion. Hermes is the target default backing agent: multi-turn conversation, corpus-grounded answers, operator-tool orchestration, and inspectable trust surfaces. Manifest retrieval (`dungeon_context_lookup`) remains the evidence layer; corpus markdown is canon, not Hermes memory.

**Current state on `main` after PR #185:** `/plan` now has a dogfooded local Agent Interaction ladder through P3.1. The surface supports local conversation threads, named thread switching, citation cards, in-pane source reading, retrieval-freshness decisions, and explicit corpus-change checks for stored turns. P3.1 landed in PR #185 (`feat(hermes): show corpus change signals on stored turns`).

**What remains future:** app-level R10/P4 provider lift, cross-surface continuity, full operator tool parity, write-preview tool flows, React `/play` migration, and Hermes long-term memory integration. Hermes long-term memory is still non-canon and future-only.

---

## Landed Agent Interaction ladder

| Phase | Status | Established behavior |
|-------|--------|----------------------|
| **P0 — Hermes Conversation Core** | Landed in PR #173 | `AgentInteractionThread` / `AgentInteractionTurn`, same-thread follow-up plumbing, localStorage persistence, trace toggle, Hermes session-handle seam / CLI fallback warning. |
| **P1 — Citation Trust Surface** | Landed in PR #176 | Answer-first UI, citation cards, Open source action, in-pane current source reader, frontend/backend citation-source client. |
| **P1.1 — Citation Source Reader Hardening** | Landed in PR #177 | `/api/live/citation-source` OpenAPI coverage, file extension allowlist, unsupported/missing/truncation tests, read-only source lookup contract. |
| **P2.0 — Named Thread Switcher** | Landed in PR #179 | Thread index, named local prep threads, new / rename / switch / delete, per-thread active turn/backend/trace preference, source-reader reset on thread switch. |
| **P2.1 — Thread Quality Guardrails** | Landed in PR #181 | Long-thread suggestion after threshold, explicit Start new thread / Keep going, per-thread dismissal persistence, helper-level thread index tests, reload/remount coverage. |
| **P3.0 — Retrieval Freshness Decision** | Landed in PR #183 | `retrieval_freshness` response object; Fresh retrieval / Blended / Thread context / Insufficient grounding panel; lightweight persistence on turns; backend decision builder; tests proving no source/prompt leakage. |
| **P3.1 — Corpus Change Signals** | Landed in PR #185 | Metadata-only `/api/live/citation-freshness`; backend source-line evidence snapshots; locator fallback snapshots labeled `locator-v1`; explicit Check current source state action; Corpus signal Current / Changed / Unknown / Unavailable; turn-level metadata persistence without source bodies. |

The current implementation is still intentionally local to `/plan`. R10/P4 is the next code lift that turns this into an app-level affordance.

---

## Trust surfaces now available

The post-P3 Agent Interaction surface has three separate trust layers:

1. **Citation source reader** — opens current source documents inside the Agent Interaction pane, using read-only validated repo-relative paths.
2. **Retrieval freshness** — records why a turn used fresh retrieval, blended retrieval + thread context, thread-only context, or insufficient grounding.
3. **Corpus change signal** — lets the GM explicitly check whether evidence snapshots from a stored turn still match current source state.

Persistence remains intentionally lightweight: thread state may keep Q/A, pointers, citation locators, evidence snapshots, status metadata, and trace preferences. It must not persist corpus bodies, normalized recap text, raw prompts, graph internals, or unbounded source excerpts.

---

## Graph / ontology alignment

`/plan` is a future graph-memory consumer, not the owner of graph memory.

Agent Interaction consumes stable source-grounded envelopes and pointers:

```text
SourceArtifact -> SourceAnchor -> SourceUnit
```

The ontology/taxonomy branch owns derived semantics, controlled vocabulary, graph IR/model, validation, reports, deterministic materialization, and later shadow retrieval. Agent Interaction should consume graph-backed retrieval only through adapters that produce or enrich the same source-vocabulary envelope.

Design rules to preserve:

- Agent Interaction may store pointers, summaries, thread metadata, citation locators, evidence snapshots, and tool-run proof pointers.
- Agent Interaction must not store corpus bodies, normalized recap text, graph internals, raw prompts, or unbounded source excerpts.
- Graph summaries are navigational display material, not source evidence.
- Corpus markdown/on-disk canonical artifacts remain source of truth until explicit write APIs promote changes.
- No production retrieval behavior should depend on graph output until shadow-mode evidence and promotion gates exist.

---

## Example user stories (acceptance anchors)

Full catalog: `Docs/Design/UX-STORIES-agent-interaction-hermes.md`

**Journey — Mireward inn prep**

1. *As a GM*, I ask: *"What is the name of the Inn in Mireward Reach and who owns it, what are its prices and what does it offer?"*  
   → Prose answer with corpus-linked facts; click link → source reader opens the current source in the Agent Interaction pane.

2. *As a GM*, I follow up in the **same thread**: *"Does the owner know Lysandra? If so how?"*  
   → Uses thread context plus retrieval-freshness decision metadata; cites new evidence where needed.

3. *As a GM*, I keep **"Inn prep"** and **"S23 ingest"** as two named threads and switch same day.  
   → Each resumes its local thread state; source-reader state resets honestly on thread switch.

4. *As a GM*, I open an older cited answer after corpus changed.  
   → The stored turn can run **Check current source state** and show whether evidence is Current, Changed, Unknown, or Unavailable.

5. *As a GM*, when the agent proposes a corpus write in a future tool-parity slice.  
   → Preview diff only; nothing commits until explicit GM approval.

---

## Path index (read these, not chat)

### Design & UX

| Path | Role |
|------|------|
| `Docs/Design/UX-STORIES-agent-interaction-hermes.md` | Full user stories and post-P3 story status |
| `Docs/Design/ANCHOR-plan-surface-agent-interaction.md` | Surface ladder, R10/R11, provider invariants |
| `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md` | `SourceArtifact -> SourceAnchor -> SourceUnit` contract |
| `Docs/Plans/HANDOFF-ontology-taxonomy-plan-surface-consumer-alignment.md` | Graph-aligned consumer boundary |
| `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md` | Derived-semantics ladder; no production retrieval changes |
| `Docs/Design/ANCHOR-dungeonBuddy-graph-retrieval.md` | Graph retrieval direction and evidence constraints |
| `.hermes.md` | Hermes policy: corpus canon, memory rules, plugin install |

### Frontend — Agent Interaction

| Path | Role |
|------|------|
| `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` | Main `/plan` bar + pane shell, ask flow, thread controls, source reader, freshness actions |
| `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts` | Thread, turn, metadata, evidence snapshot, and localStorage helpers |
| `apps/live-control-ui/src/planSurface/components/RetrievalFreshnessPanel.tsx` | P3 retrieval-freshness trust panel |
| `apps/live-control-ui/src/planSurface/components/CorpusChangeSignalPanel.tsx` | P3.1 corpus freshness/change signal panel |
| `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx` | Dogfood trace panel behind user toggle |
| `apps/live-control-ui/src/planSurface/components/ContextSufficiencyPanel.tsx` | Retrieved/admitted evidence display |
| `apps/live-control-ui/src/planSurface/components/contextSufficiencyLadder.ts` | Ladder + admitted items for UI |
| `apps/live-control-ui/src/planSurface/planSurface.css` | Agent Interaction shell, bar, pane, trace/citation/freshness styling |
| `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx` | Mounts Agent Interaction on `/plan` |
| `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | UI coverage for Agent Interaction behavior |
| `apps/live-control-ui/src/api/types.ts` | `LiveQueryResponse`, thread types, retrieval/citation freshness types |
| `apps/live-control-ui/src/api/liveApi.ts` | `postLiveQuery`, citation-source client, citation-freshness client |

### Backend — query loop, source reader, freshness

| Path | Role |
|------|------|
| `apps/live_control_server/services/live_agent_loop.py` | `process_live_query`, Hermes CLI path, preflight retrieval, `retrieval_freshness`, `agent_trace` |
| `apps/live_control_server/services/citation_source_reader.py` | Read-only validated source lookup for in-pane citation reader |
| `apps/live_control_server/services/citation_freshness.py` | Metadata-only citation freshness checker and source-line hash comparison |
| `apps/live_control_server/routes/live.py` | `POST /api/live/query`, `/api/live/citation-source`, `/api/live/citation-freshness` |
| `src/live_play/manifest_context_query.py` | Manifest retrieval, session scoping, admission |
| `src/live_play/source_bundle.py` | `IngestionSourceBundle` and source-vocabulary adapter |

### Hermes plugin & runtime

| Path | Role |
|------|------|
| `integrations/hermes/plugins/dungeonbuddy/__init__.py` | `dungeon_context_lookup`, manifest tools, legacy lexical fallback |
| `integrations/hermes/plugins/dungeonbuddy/skills/dungeonbuddy-corpus-qa/SKILL.md` | Agent skill and cite-or-abstain policy direction |
| `scripts/hermes_spike_install_plugin.sh` | Symlink plugin into `$HERMES_HOME` |
| `.hermes-runtime/` (local, gitignored) | Scoped Hermes home, config, sessions, logs |

### Graph / ontology surfaces to know but not consume directly

| Path | Role |
|------|------|
| `src/graph_memory/**` | Graph-memory implementation surface owned by ontology/taxonomy workstream |
| `evals/graph_memory_layer/**` | Diagnostic graph-memory eval/report artifacts |
| `tests/test_graph_memory_*.py` | Graph-memory tests; not Agent Interaction acceptance gates |

---

## Runtime quick reference

```bash
# Hermes plugin (once)
export HERMES_HOME="$PWD/.hermes-runtime"
export DUNGEONBUDDY_REPO="$PWD"
export DUNGEONBUDDY_CORPUS_ROOT="$PWD/corpus"
bash ./scripts/hermes_spike_install_plugin.sh

# Live-control with Hermes CLI backend
export DUNGEONMIND_LIVE_HERMES_MODE=cli
export DUNGEONMIND_LIVE_HERMES_PROVIDER=custom
export DUNGEONMIND_LIVE_HERMES_MODEL=gpt-5.4-mini
uv run uvicorn apps.live_control_server.main:app --reload --port 8000

# UI
cd apps/live-control-ui && npm run dev   # http://localhost:5173/plan
```

Env vars defined in `live_agent_loop.py`: `DUNGEONMIND_LIVE_HERMES_*`, `HERMES_HOME`.

---

## Invariants (do not regress)

1. **Corpus is canon** — campaign facts via tools/retrieval, not Hermes long-term memory (`.hermes.md`).
2. **Preflight retrieval remains inspectable** — Hermes path returns `context_packet`; zero admitted + confident answer is a bug.
3. **No autonomous writes** — preview → explicit GM confirm; benchmark before loosening.
4. **Pointers in persistence** — thread storage may keep Q/A, citation locators, evidence snapshots, freshness metadata, trace ids, and summaries; not corpus bodies.
5. **Live reads across threads** — factual answers ground on current corpus after ingest/write in any thread.
6. **UI stays in the bar/pane** — citations, source reader, trace, retrieval freshness, and corpus signal remain inside Agent Interaction chrome; do not take over plan canvas.
7. **Session scope** — session-number questions must not admit wrong-session recaps.
8. **Graph boundary** — Agent Interaction consumes source-vocabulary envelopes and metadata; it does not consume graph internals or graph summaries as evidence.

---

## Build sequence from here

| Phase | Status / next action |
|-------|----------------------|
| **P0** | Landed; local conversation/thread core exists. |
| **P1 / P1.1** | Landed; citation trust surface and source-reader hardening exist. |
| **P2.0 / P2.1** | Landed; named threads and long-thread guardrails exist. |
| **P3.0 / P3.1** | Landed; retrieval freshness and corpus change signals exist. |
| **P4 / R10** | **Next likely code slice:** lift Agent Interaction state into an app-level `AgentInteractionProvider` while preserving current `/plan` UI. |
| **P5** | Future: full operator tool parity via Hermes, with preview/confirm writes. |
| **P6** | Future: Hermes memory integration for non-canon layers only. |

**Next choices after this docs re-anchor:**

1. R10/P4 `AgentInteractionProvider` lift.
2. Graph-aligned adapter planning for future graph-backed retrieval that emits `SourceUnit` envelopes.
3. Later `/play` migration after provider lift.

Do not start runtime graph retrieval in this workstream.

---

## Verification

Docs-only re-anchor:

```bash
rg -n "Next slice to implement|Not done|P0|P1|P2|P3|P4|R10|retrieval_freshness|citation-freshness|CorpusChangeSignal|SourceArtifact|SourceAnchor|SourceUnit|ontology|taxonomy|graph" Docs/Design Docs/Experiments Docs/Plans

rg -n "AgentInteractionProvider|SourceArtifact|SourceAnchor|SourceUnit|retrieval_freshness|citation-freshness|evidence_snapshots|CorpusChangeSignalPanel" Docs/Design Docs/Experiments Docs/Plans
```

Runtime touched only if code changes:

```bash
uv run pytest tests/test_live_control_server.py -q
cd apps/live-control-ui && npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx
cd apps/live-control-ui && npm test -- --run src/planSurface/components/agentInteractionHistory.test.ts
cd apps/live-control-ui && npm run build
```

---

## Re-anchor procedure

1. Read this anchor.
2. Read the parent plan-surface anchor.
3. Read `CONTRACT-surface-vocabulary-boundary-v0.md` before introducing new proof or retrieval display shapes.
4. Confirm any PR status before saying a phase is landed.
5. For code, prefer R10/P4 provider lift next; keep `/plan` visual UI mostly unchanged.
6. Do not start graph retrieval, graph materialization, LLM extraction, alias merge, corpus writes, or Hermes long-term memory from this anchor.

---

## Related anchors & handoffs

| Document | When |
|----------|------|
| `Docs/Design/UX-STORIES-agent-interaction-hermes.md` | Story catalog and post-P3 story status |
| `Docs/Design/ANCHOR-plan-surface-agent-interaction.md` | R10/R11 ladder, app-level provider architecture |
| `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md` | Source-vocabulary boundary |
| `Docs/Plans/HANDOFF-ontology-taxonomy-plan-surface-consumer-alignment.md` | Graph-aligned consumer boundary |
| `Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md` | Derived-semantics ladder |
| `Docs/Design/ANCHOR-dungeonBuddy-graph-retrieval.md` | Future graph retrieval direction |
