# HANDOFF — Post-P3 Agent Interaction Graph-Aligned Re-anchor

**Status:** ACTIVE / CURRENT  
**Created:** 2026-06-26  
**Branch:** `docs/agent-interaction-post-p3-graph-aligned-reanchor`  
**Workstream:** Agent Interaction / Plan Surface / Source Vocabulary / Ontology-Taxonomy Alignment  
**Mode:** Docs-first re-anchor, then prepare R10/P4 provider lift. Do not start runtime graph retrieval.

---

## Mission

Re-anchor the Agent Interaction and Plan Surface docs after the local `/plan` Agent Interaction ladder through P3.1. Fresh agents should no longer treat P0 as the next slice.

The next likely code slice is:

```text
R10.0 / P4.0 — App-level AgentInteractionProvider lift, preserving current /plan UI
```

---

## Verified PR state

PR #185 — `feat(hermes): show corpus change signals on stored turns` — is merged.

Therefore permanent docs should state:

```text
P3.1 — landed
```

not pending / merge-ready.

---

## Landed local `/plan` ladder

| Phase | Status | Established behavior |
|-------|--------|----------------------|
| P0 — Hermes Conversation Core | Landed | `AgentInteractionThread` / `AgentInteractionTurn`, same-thread follow-up plumbing, localStorage persistence, trace toggle, Hermes session-handle seam / CLI fallback warning. |
| P1 — Citation Trust Surface | Landed | Answer-first UI, citation cards, Open source action, in-pane current source reader, citation-source frontend/backend client. |
| P1.1 — Citation Source Reader Hardening | Landed | `/api/live/citation-source` OpenAPI coverage, file extension allowlist, unsupported/missing/truncation tests, read-only source lookup contract. |
| P2.0 — Named Thread Switcher | Landed | Thread index, named local prep threads, new / rename / switch / delete, per-thread active turn/backend/trace preference, source-reader reset on thread switch. |
| P2.1 — Thread Quality Guardrails | Landed | Long-thread suggestion after threshold, explicit Start new thread / Keep going, per-thread dismissal persistence, helper-level thread index tests, reload/remount coverage. |
| P3.0 — Retrieval Freshness Decision | Landed | `retrieval_freshness` response object; Fresh retrieval / Blended / Thread context / Insufficient grounding panel; lightweight persistence on turns; backend decision builder; tests proving no source/prompt leakage. |
| P3.1 — Corpus Change Signals | Landed | Metadata-only `/api/live/citation-freshness`, backend source-line evidence snapshots, client locator fallback snapshots labeled `locator-v1`, explicit Check current source state action, Corpus signal Current / Changed / Unknown / Unavailable, turn-level metadata persistence without source bodies. |

---

## Canonical docs to read now

```text
Docs/Design/ANCHOR-agent-interaction-hermes.md
Docs/Design/ANCHOR-plan-surface-agent-interaction.md
Docs/Design/UX-STORIES-agent-interaction-hermes.md
Docs/Experiments/PLAN-SURFACE-LADDER-TRACKING.md
Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md
Docs/Plans/HANDOFF-ontology-taxonomy-plan-surface-consumer-alignment.md
Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md
Docs/Design/ANCHOR-dungeonBuddy-graph-retrieval.md
```

---

## Runtime/code paths to know

Frontend:

```text
apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts
apps/live-control-ui/src/planSurface/components/RetrievalFreshnessPanel.tsx
apps/live-control-ui/src/planSurface/components/CorpusChangeSignalPanel.tsx
apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/planSurface/planSurface.css
```

Backend:

```text
apps/live_control_server/services/live_agent_loop.py
apps/live_control_server/services/citation_source_reader.py
apps/live_control_server/services/citation_freshness.py
apps/live_control_server/routes/live.py
tests/test_live_control_server.py
src/live_play/source_bundle.py
```

Hermes/plugin:

```text
.hermes.md
integrations/hermes/plugins/dungeonbuddy/__init__.py
integrations/hermes/plugins/dungeonbuddy/skills/dungeonbuddy-corpus-qa/SKILL.md
scripts/hermes_spike_install_plugin.sh
```

Graph/ontology likely code surfaces:

```text
src/graph_memory/**
evals/graph_memory_layer/**
tests/test_graph_memory_*.py
Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md
Docs/Design/ANCHOR-dungeonBuddy-graph-retrieval.md
```

---

## Graph / ontology alignment rules

1. `/plan` is a consumer, not graph infrastructure.
2. AgentInteractionProvider should eventually live above routes/surfaces in AppChrome.
3. Agent Interaction stores pointers, summaries, thread metadata, citation locators, evidence snapshots, and tool-run proof pointers.
4. Agent Interaction must not store corpus bodies, normalized recap text, graph internals, raw prompts, or unbounded source excerpts.
5. SourceVocabulary contract remains:

   ```text
   SourceArtifact -> SourceAnchor -> SourceUnit
   ```

6. Ontology/taxonomy branch owns derived semantics, controlled vocabulary, graph IR, validation, reports, deterministic materialization, and later shadow retrieval.
7. Graph outputs should eventually enrich or produce the same `SourceUnit` envelope.
8. Graph summaries are navigational display material, not source evidence.
9. Corpus markdown/on-disk canonical artifacts remain source of truth until explicit write APIs promote changes.
10. No production retrieval behavior should depend on graph output until shadow-mode evidence and promotion gates exist.

---

## Recommended next code slice

Do not start this until docs are truthful and merged or explicitly waived.

```text
R10.0 / P4.0 — App-level AgentInteractionProvider lift, preserving current /plan UI
```

Scope:

```text
- Create app-level provider state above /plan.
- Move thread/pane/projection state ownership behind provider hooks.
- Keep current /plan visual UI mostly unchanged.
- Let /plan publish ambient context into provider.
- Store pointers and summaries only.
- Do not build graph retrieval.
- Do not migrate Play yet.
- Do not add operator tool parity yet.
```

Suggested future branch:

```text
feat/agent-interaction-provider-lift
```

Suggested PR title:

```text
feat(agent): lift Agent Interaction state into provider
```

---

## Explicit non-goals for the next code PR

Do not implement:

```text
runtime graph retrieval
graph materializer
LLM extraction
alias resolution
identity merge
relationship inference
Play migration
operator tool parity
Hermes long-term memory
corpus writes
prompt changes
canonical corpus mutation
```

---

## Verification

Docs-only re-anchor:

```bash
rg -n "Next slice to implement|Not done|P0|P1|P2|P3|P4|R10|retrieval_freshness|citation-freshness|CorpusChangeSignal|SourceArtifact|SourceAnchor|SourceUnit|ontology|taxonomy|graph" Docs/Design Docs/Experiments Docs/Plans

rg -n "AgentInteractionProvider|SourceArtifact|SourceAnchor|SourceUnit|retrieval_freshness|citation-freshness|evidence_snapshots|CorpusChangeSignalPanel" Docs/Design Docs/Experiments Docs/Plans
```

Runtime checks are only required if runtime files change.
