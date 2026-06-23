# Roadmap — Plan Surface Agent Interaction

**Status:** Active roadmap  
**Created:** 2026-06-22  
**Updated:** 2026-06-22  
**Branch under design:** `cursor/cloud-agent-1782137144843-h0ddf`  
**Related anchor:** `Docs/Design/ANCHOR-plan-surface-agent-interaction.md`  
**Related graph UX:** `Docs/Design/GRAPH-MEMORY-RECAP-PREVIEW-UX-HANDOFF.md`

---

## 1. Roadmap Thesis

The current branch proves that `/plan` can host a meaningful Agent Interaction layer: it can load source-vocabulary proof, ask manifest-backed questions, route through a native live backend or Hermes, display context sufficiency, and expose trace telemetry.

That proof is valuable, but it is too wide to land as a single PR.

Roadmap thesis:

```txt
Land the vocabulary first.
Land the inspectable backend second.
Land the /plan UI consumer third.
Hoist to app-level provider only after the plan-scoped proof is stable.
Prepare graph-memory preview UX as a trust surface, but do not implement it until backend contracts exist.
```

This prevents four common failures:

```txt
1. UI depending on raw ingestion internals.
2. Hermes becoming a black-box answer generator.
3. The plan-scoped proof hardening into the final app-wide architecture.
4. Candidate graph extraction being presented as canon or generic graph-database UI.
```

---

## 2. Current Branch Inventory

The current branch is ahead of `main` and includes multiple conceptual slices.

### Design / continuity

```txt
Docs/Design/ANCHOR-plan-surface-agent-interaction.md
Docs/Design/ROADMAP-plan-surface-agent-interaction.md
Docs/Design/GRAPH-MEMORY-RECAP-PREVIEW-UX-HANDOFF.md
Docs/Plans/HANDOFF-self-continuity-hermes-agent-interaction-bar.md
```

### Source vocabulary / ingestion proof

```txt
src/live_play/source_bundle.py
apps/live_control_server/routes/live.py  (/api/live/source-bundle)
tests/test_source_bundle.py
Docs/data/ingested-corpus-library/*
evals/c2_live_prep/benchmarks/*manifest*
```

### Agent backend / Hermes

```txt
apps/live_control_server/services/live_agent_loop.py
integrations/hermes/plugins/dungeonbuddy/__init__.py
src/live_play/manifest_context_query.py
apps/live_control_server/routes/live.py  (/api/live/query query_backend)
tests/test_live_control_server.py
tests/test_hermes_dungeonbuddy_plugin.py
tests/test_manifest_context_query.py
```

### `/plan` UI consumer

```txt
apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx
apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx
apps/live-control-ui/src/planSurface/components/ContextSufficiencyPanel.tsx
apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts
apps/live-control-ui/src/planSurface/components/contextSufficiencyLadder.ts
apps/live-control-ui/src/planSurface/planSurface.css
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/test/fixtures.ts
apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx
apps/live-control-ui/src/planSurface/components/contextSufficiencyLadder.test.ts
```

### Graph memory preview design

```txt
Docs/Design/GRAPH-MEMORY-RECAP-PREVIEW-UX-HANDOFF.md
```

This is design-only. It should not pull graph-preview routes, React components, graph visualization libraries, approval endpoints, or query executors into the current Agent Interaction implementation slices.

### Must not land accidentally

```txt
evals/c2_live_prep/live/_pytest/**
```

These are pytest live workspace artifacts. They should be removed from PR branches unless the PR is explicitly about fixture output changes.

---

## 3. Target Product Shape

The target product is not “a query box in `/plan`.”

The target is an inspectable Agent Interaction layer that can eventually follow the GM across surfaces.

```txt
AppChrome
  AgentInteractionProvider
    bottom Agent Interaction Bar
    expandable Agent Interaction Pane
    projection-aware context
    bounded turn summaries
    proof pointers
  Surface routes
    /plan
    /live-play
    future surfaces
```

The current branch is a plan-scoped proof of that target:

```txt
PlanSurfaceShell
  PlanAgentInteractionBar
    source bundle proof
    live/hermes backend picker
    question form
    context sufficiency review
    trace details
    bounded turn history
```

That proof should land before the app-level provider hoist, but the PR titles and docs must be honest that it is still plan-scoped.

Graph memory preview is adjacent to this target. It will eventually feed Agent Interaction with graph/entity/evidence chips and graph query result cards, but the first graph UX milestone is:

```txt
Recap-derived candidate graph preview
→ GM trust evaluation
→ approve / defer / reject proposed writes
```

Do not treat graph preview as generic graph database UI or as a hidden dependency of the immediate Agent Interaction bar PRs.

---

## 4. Landing Sequence

## PR A — Source Bundle Adapter

**Suggested branch:** `feat/plan-source-bundle-adapter`  
**Suggested title:** `feat(plan): add ingestion source bundle adapter`

### Goal

Land the read-only source-vocabulary adapter that maps ingested corpus library artifacts into the shared surface vocabulary:

```txt
SourceArtifact -> SourceAnchor -> SourceUnit
```

### Scope

Include:

```txt
src/live_play/source_bundle.py
/api/live/source-bundle route
tests/test_source_bundle.py
minimal api/types if needed by tests or UI follow-up
required ingested corpus library fixture updates only if deterministic and necessary
```

### Product contract

The adapter must answer:

```txt
What source artifacts exist?
Where are their anchors?
What source units can UI consume?
What role/authority/lifecycle/evidence status does each unit carry?
What is the coverage summary?
```

### Hard boundaries

Do not embed:

```txt
corpus document bodies
normalized recap text
breadcrumbed recap text
session memory JSONL body lines
full manifest entry bodies
```

Do not add:

```txt
Hermes integration
query backend switching
Agent Interaction UI
provider hoist
graph inference
alias resolution
relationship extraction
corpus mutation
```

### Acceptance criteria

```txt
- /api/live/source-bundle returns dmb_ingestion_source_bundle_v1.
- SourceArtifact / SourceAnchor / SourceUnit are populated for longmont-c2.
- Locators are opaque or repo/corpus-relative; no absolute paths in UI contract.
- Diagnostics include read_only_adapter and corpus_bodies_not_embedded.
- Tests prove no body/text payload is embedded in units.
- No pytest workspace artifacts are included.
```

### Verification

```bash
uv run pytest tests/test_source_bundle.py tests/test_ingested_corpus_library.py -q
```

---

## PR B — Hermes Live Query Backend + Trace

**Suggested branch:** `feat/plan-hermes-live-query-trace`  
**Suggested title:** `feat(plan): add Hermes live-query backend trace`

### Goal

Add inspectable Hermes routing to `/api/live/query` without making Hermes the evidence authority.

### Scope

Include:

```txt
apps/live_control_server/services/live_agent_loop.py
apps/live_control_server/routes/live.py query_backend support
integrations/hermes/plugins/dungeonbuddy/__init__.py
src/live_play/manifest_context_query.py only for query/admission fixes needed by Hermes path
tests/test_live_control_server.py
tests/test_hermes_dungeonbuddy_plugin.py
tests/test_manifest_context_query.py if touched
```

### Product contract

The backend must support two mental models:

```txt
live backend   = native live/context lookup; retrieval/admission is the product
hermes backend = preflight retrieval + Hermes synthesis + inspectable trace
```

### Required backend behavior

For Hermes mode:

```txt
1. Run DungeonBuddy context lookup first.
2. Return the same context_packet to the UI.
3. Embed admitted evidence in the Hermes prompt only after preflight.
4. Return agent_trace with runtime, backend, provider/model, step summary, context summary, prompt size, usage if available, warnings, and artifact refs.
5. Write no live events/jobs for context questions.
```

### Hard boundaries

Do not:

```txt
store Hermes memory as canon
write corpus files
write live events/jobs for context questions
hide retrieval diagnostics behind synthesis
replace manifest retrieval with lexical search
make lexical fallback default
```

### Known design risks to address or explicitly defer

```txt
- Passing full prompt through argv may expose retrieved text to process inspection and can hit OS argument limits.
- Raw Hermes session/log absolute paths should not be browser-facing product data.
- Current Hermes path is one-shot, not session-continuous.
```

Recommended mitigation for this PR:

```txt
- Cap prompt size hard.
- Redact command summaries.
- Prefer HERMES_HOME-relative artifact refs or opaque ids.
- Document one-shot as a known limitation.
```

### Acceptance criteria

```txt
- POST /api/live/query accepts query_backend = live | hermes.
- Hermes in-process fallback remains testable.
- CLI mode is gated behind DUNGEONMIND_LIVE_HERMES_MODE=cli.
- Preflight context lookup happens before CLI invocation.
- Response includes context_packet and agent_trace.
- Context questions do not mutate live event/job stores.
- Tests cover missing Hermes executable, CLI success, and no live mutations.
```

### Verification

```bash
uv run pytest tests/test_live_control_server.py tests/test_hermes_dungeonbuddy_plugin.py tests/test_manifest_context_query.py -q
```

---

## PR C — Plan-Scoped Agent Interaction Bar Proof

**Suggested branch:** `feat/plan-agent-interaction-bar-proof`  
**Suggested title:** `feat(plan): add plan-scoped Agent Interaction bar proof`

### Goal

Land the plan-scoped UI proof that lets the GM open a bottom Agent Interaction bar/pane, inspect source-bundle coverage, ask corpus questions, review context sufficiency, inspect Hermes/live traces, and maintain bounded turn summaries.

### Scope

Include:

```txt
PlanAgentInteractionBar.tsx
ContextSufficiencyPanel.tsx
TraceDetailsPanel.tsx
agentInteractionHistory.ts
contextSufficiencyLadder.ts
PlanSurfaceShell.tsx mount point
planSurface.css additions
liveApi.ts / types.ts UI contract additions
fixtures.ts updates
PlanSurfaceShell.test.tsx
contextSufficiencyLadder.test.ts
```

### Product contract

The UI must make three things inspectable:

```txt
1. What source coverage is available?
2. What evidence did the query admit or reject?
3. What did the agent/backend do with that evidence?
```

### Required UI behavior

```txt
- Bottom Agent Interaction bar appears on /plan.
- Opening the pane loads /api/live/source-bundle.
- The pane shows ingestion/source coverage without exposing raw bodies.
- The question form supports live and hermes backends.
- Answers with context_packet show context sufficiency before raw synthesis.
- Hermes CLI answers show trace details and answer.
- Turn history is bounded.
- localStorage does not store context_packet or retrieved text excerpts.
```

### Copy guidance

Prefer calm product language:

```txt
Agent Interaction
Ask ingested corpus
Context packet review
Retrieved text
Agent trace
Prompt sent to Hermes
Source coverage
```

Avoid overstating capabilities:

```txt
Do not claim multi-turn Hermes session continuity yet.
Do not call the plan-scoped pane the final app-wide AgentInteractionProvider.
Do not claim metadata-only persistence if answer summaries are persisted.
```

Preferred wording for history:

```txt
bounded turn summaries; retrieved evidence bodies are not persisted
```

### Hard boundaries

Do not:

```txt
hoist app-level provider yet
replace the right-side Tools drawer
remove existing projection paths
store retrieved evidence bodies in localStorage
create a second projection registry
turn Agent Interaction into corpus write UI
add graph preview UI yet
```

### Acceptance criteria

```txt
- /plan renders existing nav/tool/edit/canvas regions plus bottom Agent Interaction bar.
- Opening Agent Interaction does not break current Tools drawer behavior.
- Tests cover live backend, hermes backend, CLI trace, weak context verdict, broad routes, bounded history, no persisted context_packet/text_excerpt.
- Build passes.
```

### Verification

```bash
cd apps/live-control-ui
npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx src/planSurface/components/contextSufficiencyLadder.test.ts
npm run build
```

---

## PR D — Docs and Self-Continuity Cleanup

**Suggested branch:** `docs/plan-agent-interaction-continuity`  
**Suggested title:** `docs(plan): capture agent interaction continuity`

### Goal

After PRs A–C settle, update docs to accurately describe what landed and what remains future work.

### Scope

```txt
ANCHOR-plan-surface-agent-interaction.md
ROADMAP-plan-surface-agent-interaction.md
HANDOFF-self-continuity-hermes-agent-interaction-bar.md
PLAN-SURFACE-LADDER-TRACKING.md, if rung statuses changed
```

### Acceptance criteria

```txt
- Anchor points to landed commits/PRs.
- Roadmap reflects which slices have merged.
- Handoff no longer describes stale branch state.
- R10 provider hoist remains future unless actually implemented.
```

---

## PR E — App-Level AgentInteractionProvider Hoist

**Suggested branch:** `feat/agent-interaction-provider-hoist`  
**Suggested title:** `feat(plan): hoist Agent Interaction provider above surfaces`

### Goal

Move from plan-scoped proof to durable app-level architecture.

### Prerequisite

Do not start this until PR C is landed and dogfooded.

### Target shape

```txt
AppChrome
  AgentInteractionProvider
    AgentInteractionBar
    AgentInteractionPane
  Route surface
    publishes ambient context
    publishes projection availability
```

### Scope

```txt
AgentInteractionProvider
useAgentInteractionContext or equivalent
surface context publishing from /plan
bounded localStorage rehydrate
transient context dropping
single shared projection container usage
```

### Out of scope

```txt
Hermes multi-turn sessions
full memory policy implementation
new source resolvers
graph preview UI
generic tool orchestration
corpus writes
```

### Acceptance criteria

```txt
- Provider sits above /plan.
- /plan publishes campaign/session/surface context into provider.
- Existing plan-scoped behavior still works.
- Persistence is bounded and pointer/summary-only.
- No retrieved evidence bodies are persisted.
- Projection path is not duplicated.
```

---

## PR F — Hermes Session Continuity Spike

**Suggested branch:** `spike/hermes-session-continuity`  
**Suggested title:** `spike(plan): test Hermes session continuity for Agent Interaction`

### Goal

Explore multi-turn Hermes session continuity without confusing Hermes memory with campaign canon.

### Prerequisite

App-level provider or plan-scoped turn history must be stable enough to compare one-shot vs session mode.

### Questions to answer

```txt
Can Hermes maintain a session id across turns?
Can the UI show per-turn retrieval proof even when Hermes has thread continuity?
Can the system prevent Hermes memory from becoming campaign truth?
Can prior turn context be represented as UI thread continuity, not canon?
```

### Hard boundaries

```txt
No campaign facts in Hermes memory.
No corpus mutation.
No hidden promotion from conversation to canon.
No use of Hermes answer without retrievable evidence for factual campaign claims.
```

---

## PR G — Graph Memory Recap Preview UX Design

**Suggested branch:** `docs/graph-memory-recap-preview-ux`  
**Suggested title:** `docs(graph-memory): design recap memory preview UX`

### Goal

Capture the frontend/product design for a recap-derived graph preview before implementation.

This is a graph-memory trust-surface design slice, not an Agent Interaction code slice.

### Scope

```txt
Docs/Design/GRAPH-MEMORY-RECAP-PREVIEW-UX-HANDOFF.md
optional wireframe notes
cross-links from Agent Interaction anchor/roadmap
```

### Product contract

The preview must help the GM answer:

```txt
Did the system understand my recap?
What did it extract?
What is uncertain?
Where did each claim come from?
What should be approved, deferred, rejected, or ignored?
```

### Required design concepts

```txt
Candidate graph preview
Timeline / beat view
Graph view
Selected node / edge detail
Evidence drawer
Proposed write diff
Ignored / deferred material
State-chip vocabulary
Source deeplinks
Future Agent Interaction graph/entity/evidence chips
```

### Hard boundaries

Do not implement:

```txt
React components
graph visualization library
API calls
live-control routes
graph query executor
graph write approval mechanics
Agent Interaction changes
```

### Acceptance criteria

```txt
- Design frames graph preview as proposed memory diff, not truth.
- Candidate vs canon visual separation is explicit.
- Evidence/source-ref behavior is one-click inspectable.
- Timeline/beat view is considered primary or at least first-class.
- Generic graph database viewer is explicitly rejected.
- Future backend contracts are listed but not implemented.
```

---

## 5. Recommended Immediate Next Move

Given the current broad branch, do this first:

```txt
1. Remove evals/c2_live_prep/live/_pytest/** changes.
2. Open PR A for Source Bundle Adapter.
3. Keep Hermes and UI changes on the working branch until PR A lands.
4. Keep graph preview UX as docs/design only unless explicitly authorized.
```

Rationale:

```txt
The source bundle is the contract everything else should consume.
If that adapter is clean, Hermes and UI can depend on a stable vocabulary.
If UI lands first, it may accidentally encode ingestion-library internals.
If graph preview UI lands too early, it may overfit diagnostic payloads instead of meaningful candidate graph contracts.
```

---

## 6. Dogfood Plan

After PR C lands, run one short dogfood pass on `/plan`:

```txt
1. Start live-control server.
2. Open /plan.
3. Open Agent Interaction.
4. Confirm source coverage for active session.
5. Ask through live backend: “What happened at the end of session 22?”
6. Confirm context packet review admits strong campaign text or clearly marks weak context.
7. Ask through Hermes backend with CLI mode enabled.
8. Confirm trace shows preflight lookup, prompt size, context summary, and answer.
9. Reload the page.
10. Confirm bounded history returns without retrieved evidence bodies.
```

Capture:

```txt
What feels like product?
What feels like debug clutter?
What should move behind details?
What copy overpromises?
What does the GM need in the bottom bar vs pane?
```

Do not immediately implement fixes unless they are safety or data-boundary bugs.

After graph-memory backend produces meaningful candidate graph previews, run a separate graph preview dogfood:

```txt
1. Open Recap Memory Preview.
2. Confirm preview-only warning is visible.
3. Inspect timeline/beat view first.
4. Select a node and edge.
5. Open evidence for each.
6. Confirm source material opens with relevant span/context.
7. Confirm candidate/canon/diagnostic distinctions are obvious.
8. Approve/defer/reject only in simulated or explicitly reviewed mode.
```

---

## 7. Future Product Questions

These questions should guide later slices:

```txt
Does Agent Interaction follow the GM across /plan and Live Play?
How does it know the active surface context?
How does it avoid storing source bodies?
How does Hermes session continuity differ from campaign canon?
How do projection tools and agent tools share the same target model?
Can an agent suggest a projection without opening it automatically?
When does an agent action require explicit confirmation?
How are source reads displayed without flooding the pane?
How will graph/entity/evidence chips appear in Agent Interaction answers?
How does a graph preview avoid looking like truth before approval?
Is timeline/beat view more useful than graph canvas for first comprehension?
What backend source-ref contract is required for source highlighting?
```

---

## 8. Non-Goals For This Roadmap

This roadmap does not authorize:

```txt
unreviewed corpus writes
Hermes memory as canon
candidate graph extraction as canon
production graph inference in Agent Interaction
identity merging
alias resolution
relationship extraction inside /plan UI
app-wide provider before plan-scoped dogfood
a second projection stack
localStorage evidence-body persistence
localStorage graph-preview payload persistence
pytest workspace artifact commits
generic graph database viewer UI
```

---

## 9. Review Checklist For Each PR

Use this checklist before requesting review:

```txt
Is this PR one conceptual slice?
Are generated pytest workspace artifacts absent?
Does the PR title match the actual scope?
Does the PR keep evidence/canon boundaries explicit?
Does localStorage avoid source bodies and context packets?
Does localStorage avoid candidate graph preview payloads?
Does Hermes remain inspectable, not black-box?
Does UI copy avoid overclaiming multi-turn/session memory?
Are absolute paths hidden, relativized, or explicitly dev-only?
Are graph candidates visually distinct from canon?
Are tests proving no live/corpus mutation when the slice is read-only?
```

---

## 10. Slice Naming Convention

Use these scope labels in PR bodies:

```txt
Scope: source-vocabulary adapter
Scope: backend agent runtime
Scope: plan-scoped UI proof
Scope: docs/continuity
Scope: provider hoist
Scope: Hermes session continuity spike
Scope: graph-memory preview UX design
```

This keeps future agents from treating all Agent Interaction and graph-memory work as one blob.
