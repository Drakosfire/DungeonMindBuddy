# HANDOFF — Hermes Agent Interaction Bar (self-continuity)

**Status:** Active self-continuity handoff  
**Written:** 2026-06-22  
**Audience:** Fresh in-IDE agent picking up Agent Interaction + Hermes integration  
**Branch:** `cursor/hermes-agent-interaction-bar` (pushed; tip `eac1b8f`)  
**Primary goal:** Continue evolving the Agent Interaction drawer into a inspectable, conversational portal backed by Hermes — with manifest-backed retrieval, rich trace telemetry, and eventually multi-turn memory.

## 0. Re-anchor block

Read this block first; do not reconstruct state from chat history.

| Field | Value |
|-------|-------|
| **Active branch** | `cursor/hermes-agent-interaction-bar` @ `eac1b8f` (`feat(plan): add Hermes trace telemetry`) |
| **Base** | `main` + R11 ingestion source bundle (`cb0c953`) + two Hermes commits on branch |
| **Working tree** | Clean for product code; ignore modified `evals/c2_live_prep/live/_pytest/**/session_22/*` artifacts unless you are debugging pytest live workspace |
| **PR** | Not opened yet — create from branch when ready: `https://github.com/Drakosfire/DungeonMindBuddy/pull/new/cursor/hermes-agent-interaction-bar` |
| **Dogfood stack** | Vite UI `http://localhost:5173` · FastAPI live-control `http://localhost:8000` |
| **Hermes runtime** | Scoped install at `$PWD/.hermes-runtime`; binary on PATH (`~/.local/bin/hermes`) |
| **Hermes mode flag** | `DUNGEONMIND_LIVE_HERMES_MODE=cli` on live-control server enables external Hermes one-shot per query |
| **Last green verification** | Branch commits include passing focused tests (see §7) |

**Current-state hypothesis:** The Agent Interaction bar on `/plan` can ask corpus questions through two backends (`live` = native manifest retrieval ladder only; `hermes` = preflight retrieval + external Hermes CLI synthesis). Telemetry is inspectable (trace, retrieved text, prompt preview, token estimates). Conversation history persists turn **metadata** in `localStorage` but each Hermes turn is still a **fresh one-shot** — no Hermes session continuity yet. The next phase is to lean into Hermes as the backing agent (multi-turn chat, tool loops, memory policy) while keeping manifest retrieval as the evidence source.

**Canonical docs to read after this handoff:**

1. `Docs/Design/ANCHOR-plan-surface-agent-interaction.md` (update stale "uncommitted spike" note when you touch it)
2. `Docs/Plans/HANDOFF-self-continuity-plan-toolbar-ingestion-design.md` (R10 provider / bottom bar direction)
3. `.hermes.md` (Hermes hard rules — memory is not canon)
4. `Docs/Plans/HANDOFF-prep-agent-c2-ingest-s21-plan-s22-cursor-first.md` §9 (Hermes path context)

---

## 1. Mission

Build an **inspectable agent interaction surface** on `/plan` that lets the GM ask campaign questions, see what evidence was retrieved, see what was sent to the agent, and eventually hold a **multi-turn conversation** enriched by corpus text — with Hermes as the orchestration/runtime layer and DungeonMindBuddy manifest retrieval as the evidence layer.

This is **working but not done**. The spike proved the wiring; the product direction is to go deeper on Hermes features (persistent sessions, tool loops, memory boundaries) rather than bolting more logic into live-control's subprocess wrapper.

---

## 2. What works today (evidence-backed)

### UI — Agent Interaction bar (`PlanAgentInteractionBar`)

- Bottom drawer on `/plan` with ask field, backend radio (`live` | `hermes`), ingestion proof via `IngestionSourceBundle`.
- **Live backend:** returns `context_packet`; UI renders context sufficiency ladder + **Retrieved text** (all admitted excerpts, full text, collapsible).
- **Hermes backend:** returns synthesized `answer` + `context_packet` + `agent_trace`; UI shows answer, trace panel, and retrieved text.
- **Trace panel** (`TraceDetailsPanel`): collapsible; shows runtime, provider/model, steps, token estimates, context budget, artifact refs, warnings, **Prompt sent to Hermes** (`prompt_preview`).
- **Turn history:** bounded (`AGENT_TURN_HISTORY_CAP = 20`) metadata in `localStorage` per campaign; reload restores question list but not full response bodies.

### Backend — query routing (`process_live_query`)

| `query_backend` | Behavior |
|-----------------|----------|
| `live` | Native live turn or manifest context lookup; ladder-first UI |
| `hermes` + `DUNGEONMIND_LIVE_HERMES_MODE=cli` | **Preflight** in-process `dungeon_context_lookup` → embed excerpts in prompt → `hermes --oneshot --toolsets dungeonbuddy` |
| `hermes` (no CLI mode) | In-process `handle_dungeon_context_lookup` only (no external agent) |

### Hermes plugin (`integrations/hermes/plugins/dungeonbuddy`)

- Primary tools: `dungeon_context_lookup`, `dungeon_manifest_index`, `dungeon_get_document` (manifest-backed).
- Legacy lexical `dungeon_search` gated behind `DUNGEONBUDDY_HERMES_LEXICAL_FALLBACK=1`.
- Skill registered as `corpus-qa` (not `dungeonbuddy:corpus-qa` — colon breaks plugin load).

### Session scoping fix (landed earlier on branch lineage)

- Manifest retrieval respects session signals; cross-session contamination (e.g. S23 content answering S22 ending questions) was fixed in `manifest_context_query.py` + ladder UI.

---

## 3. Learnings from designing this (capture these)

### 3.1 Preflight retrieval before Hermes is non-negotiable for inspectability

**Observation:** Hermes `--oneshot` returns only final text. Without preflight, the UI showed "Admitted evidence: 0" while still displaying a confident answer — a trust-breaking trace.

**Decision:** Live-control always runs `dungeon_context_lookup` before CLI invocation, returns `context_packet` in the API response, and embeds admitted excerpts in the Hermes prompt.

**Implication for next agent:** Any move to Hermes-native multi-turn chat must **still surface retrieval/admission diagnostics** to the UI. Do not rely on the agent's answer alone as proof of grounding.

### 3.2 Two backends teach different mental models

- **`live`:** "Show me what the retrieval system admits/rejects" — no synthesis, ladder is the product.
- **`hermes`:** "Answer my question, but let me audit retrieval + prompt + trace."

Keep this split until Hermes path can run multi-step tool loops with per-step trace export.

### 3.3 Fresh Hermes one-shot per turn is a deliberate spike, not the end state

Each `hermes --oneshot` invocation is a **new subprocess** with no conversation carry-over. UI history is metadata-only.

**User intent for next phase:** Multi-turn conversation with memory enriched by retrieved text — requires Hermes **session** (`hermes chat` or session-id reuse), not repeated one-shots.

### 3.4 Token estimates matter for the "are we dumping whole docs?" question

Trace now includes:

- `prompt_char_count` / `prompt_token_estimate`
- `admitted_excerpt_char_count` / `admitted_excerpt_token_estimate`
- `total_excerpt_*` across admitted evidence

Use these to falsify whether retrieval is stuffing full recaps vs targeted excerpts. If estimates approach full-doc size, tighten admission — do not hide behind synthesis quality.

### 3.5 Hermes provider config is easy to get wrong

- Upstream Hermes may not have `openai` provider enabled; this spike uses `--provider custom` with `OPENROUTER_BASE_URL=https://api.openai.com/v1`.
- Env vars: `DUNGEONMIND_LIVE_HERMES_PROVIDER`, `DUNGEONMIND_LIVE_HERMES_MODEL`, `DUNGEONMIND_LIVE_HERMES_BASE_URL`.

### 3.6 Hermes memory ≠ campaign canon

`.hermes.md` is explicit: do not store campaign facts in Hermes memory; use DungeonBuddy tools for evidence. Any "conversation memory" feature must distinguish:

- **Thread continuity** (prior turns in this UI session)
- **Retrieval cache / proof pointers** (what evidence was admitted)
- **Hermes ambient memory** (off or strictly non-canon for this product)

### 3.7 UI simplification improved inspectability

Removed redundant panels (admitted summary, suggested reads, weak/debug splits). Single **Retrieved text** section + collapsible **Agent trace** + **Prompt sent to Hermes** is the inspectability surface. Do not re-expand clutter without user ask.

### 3.8 R10 (app-level provider) is still future work

Current implementation lives inside `/plan` (`PlanAgentInteractionBar`), not `AgentInteractionProvider` in `AppChrome`. The architecture docs still call for hoisting. Hermes work can proceed on `/plan` first, but do not bake `/plan`-only assumptions into Hermes session IDs if R10 migration is imminent.

### 3.9 In-process vs CLI boundary

- **In-process:** fast, testable, good for unit tests and plugin development.
- **CLI:** real Hermes tool loop, real provider billing, session artifacts under `$HERMES_HOME/sessions/`, agent.log.

The product direction favors **CLI (or Hermes API if one exists)** for real agent behavior; in-process remains fallback/dev path.

---

## 4. Known gaps and red flags

| Gap | Severity | Notes |
|-----|----------|-------|
| No Hermes session continuity | High | Each turn = new `--oneshot`; no `--session` reuse wired |
| Hermes tool steps often show as 1 step | Medium | One-shot may not expose intermediate tool calls to live-control; check `$HERMES_HOME/logs/agent.log` |
| Token usage often "not reported" | Medium | `_collect_hermes_home_artifacts` is best-effort parse of session files |
| Turn history drops response bodies on reload | Medium | Only `AgentInteractionTurnMeta` persisted; re-fetch or store pointers |
| R10 not started | Medium | Bar still plan-scoped |
| Hermes may answer beyond admitted evidence | High | Preflight helps but synthesis can hallucinate; need cite-or-abstain discipline in skill/prompt |
| Full document admission not ruled out | Medium | Watch excerpt token estimates vs source doc sizes |
| Anchor doc stale | Low | `ANCHOR-plan-surface-agent-interaction.md` still mentions uncommitted spike |

---

## 5. How to run (operator)

### One-time Hermes setup

```bash
cd /media/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
export HERMES_HOME="$PWD/.hermes-runtime"
export DUNGEONBUDDY_REPO="$PWD"
export DUNGEONBUDDY_CORPUS_ROOT="$PWD/corpus"
bash ./scripts/hermes_spike_install_plugin.sh
hermes plugins enable dungeonbuddy
# Enable custom OpenAI-compatible provider in $HERMES_HOME/config.yaml if needed
```

### Live-control server with Hermes CLI backend

```bash
cd /media/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy
export HERMES_HOME="$PWD/.hermes-runtime"
export DUNGEONBUDDY_REPO="$PWD"
export DUNGEONBUDDY_CORPUS_ROOT="$PWD/corpus"
export DUNGEONMIND_LIVE_HERMES_MODE=cli
export DUNGEONMIND_LIVE_HERMES_PROVIDER=custom
export DUNGEONMIND_LIVE_HERMES_MODEL=gpt-5.4-mini
export DUNGEONMIND_LIVE_HERMES_BASE_URL=https://api.openai.com/v1
uv run uvicorn apps.live_control_server.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/live-control-ui && npm run dev
# Open http://localhost:5173/plan → Agent Interaction → select Hermes backend
```

### Watch Hermes directly (optional)

```bash
hermes chat --toolsets dungeonbuddy --provider custom --model gpt-5.4-mini
# Prefer: hermes memory off  (see .hermes.md)
```

---

## 6. Files in scope for next slices

**Backend**

- `apps/live_control_server/services/live_agent_loop.py` — Hermes CLI path, preflight, `agent_trace`, prompt assembly
- `apps/live_control_server/routes/live.py` — `query_backend` on `POST /api/live/query`
- `integrations/hermes/plugins/dungeonbuddy/__init__.py` — tools, manifest lookup
- `integrations/hermes/plugins/dungeonbuddy/skills/dungeonbuddy-corpus-qa/SKILL.md` — agent instructions
- `src/live_play/manifest_context_query.py` — retrieval/admission (session scoping, ending beats)

**Frontend**

- `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`
- `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx`
- `apps/live-control-ui/src/planSurface/components/ContextSufficiencyPanel.tsx`
- `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
- `apps/live-control-ui/src/planSurface/components/contextSufficiencyLadder.ts`
- `apps/live-control-ui/src/api/types.ts`

**Tests**

- `tests/test_live_control_server.py` — Hermes CLI routing + trace assertions
- `tests/test_hermes_dungeonbuddy_plugin.py`
- `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx`

**Design / policy**

- `Docs/Design/ANCHOR-plan-surface-agent-interaction.md`
- `.hermes.md`

---

## 7. Files explicitly out of scope unless user approves

- `src/prompts/corpus_session_planner.py` — planner prompts; separate lane
- `evals/*/gold/*.json` — do not deflate gold to match Hermes output
- Corpus content edits under `corpus/`
- R10 full `AgentInteractionProvider` hoist (large refactor — coordinate with user)
- Replacing manifest retrieval with Hermes v0 lexical search
- Committing pytest live workspace artifacts under `evals/c2_live_prep/live/_pytest/`

---

## 8. Verification commands (§7 for external-agent style)

Run before claiming done on any slice:

```bash
# Backend Hermes + live query
uv run pytest tests/test_live_control_server.py tests/test_hermes_dungeonbuddy_plugin.py -q

# Frontend plan surface
cd apps/live-control-ui && npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx

# Build
cd apps/live-control-ui && npm run build
```

**Behavioral gates for Hermes slices:**

1. Hermes path returns non-empty `context_packet.admitted_evidence` for a known-good session question (e.g. ending beat query with correct session scope).
2. `agent_trace.prompt_preview` contains the user question and retrieved excerpt block.
3. `agent_trace.context_summary.admitted_excerpt_token_estimate` is present and non-zero when evidence admitted.
4. UI shows **Retrieved text** and **Agent trace** without requiring raw answer text for `live` backend.
5. For Hermes backend, answer renders AND trace is collapsible.

---

## 9. Recommended next steps (prioritized)

User direction: **lean harder on Hermes** as backing agent; add **memory/conversation** enriched with retrieved text.

### Slice A — Hermes session continuity (highest leverage)

**Goal:** Reuse a Hermes session across UI turns instead of `--oneshot` every time.

**Design questions to resolve with user:**

- Session id: server-issued per campaign? per UI thread? stored where?
- Invocation: switch from `--oneshot` to `hermes chat` with stdin/session flag, or Hermes API if documented?
- What from preflight still runs each turn? (Likely: fresh retrieval per question, inject as turn context — not stale session memory as canon.)

**Falsification:** Turn 2 references Turn 1 question without re-asking; trace shows same Hermes session artifact path under `$HERMES_HOME/sessions/`.

### Slice B — Richer step/tool trace from Hermes

**Goal:** Surface intermediate tool calls (lookup, get_document) in `agent_trace.steps`, not only final step count = 1.

**Approach:** Parse Hermes session JSON/log after run; or keep process attached longer; or use Hermes native trace export if available.

### Slice C — Conversation UI

**Goal:** Thread view in Agent Interaction bar: prior Q/A visible, select turn to inspect trace/retrieved text, not just metadata chips.

**Constraint:** Persist pointers + trace ids, not corpus bodies (`ANCHOR` pointers-only rule).

### Slice D — Memory policy (explicit, user-visible)

**Goal:** Document and implement which memory layers exist:

| Layer | Allowed content | Storage |
|-------|-----------------|---------|
| UI turn history | questions, trace ids, answer summaries | localStorage |
| Retrieval proof | admitted evidence ids/paths, token counts | API response + optional server cache |
| Hermes session | orchestration state | `$HERMES_HOME/sessions/` |
| Hermes long-term memory | **off** for campaign facts | `.hermes.md` |

Add UI toggle/indicator: "Hermes memory: off" for operator confidence.

### Slice E — Skill/prompt hardening

Update `dungeonbuddy-corpus-qa` skill: cite evidence ids, abstain when preflight admits zero excerpts, prefer tool calls over preamble when excerpts insufficient.

### Slice F — R10 provider hoist (parallel track)

When user wants app-wide bar: extract `PlanAgentInteractionBar` state into `AgentInteractionProvider` per `HANDOFF-self-continuity-plan-toolbar-ingestion-design.md`.

---

## 10. Rubric when we judge (carry forward)

- **Inspectability:** Every synthesized answer must ship with retrievable evidence metadata (`context_packet` + token estimates). Zero admitted + confident answer = fail.
- **Session scope:** Session-number questions must not admit wrong-session recaps (regression test or manual dogfood on S22 vs S23).
- **No corpus in client persistence:** localStorage holds metadata only.
- **Hermes memory ≠ canon:** Any memory feature must cite `.hermes.md`; campaign facts come from tools/retrieval.
- **Cost signal:** Report `agent_trace` elapsed_ms and token fields when comparing retrieval vs full-doc baselines.
- **Tests at boundary:** Backend guarantees proven by `test_live_control_server.py`; UI by `PlanSurfaceShell.test.tsx`.

---

## 11. Recommended first move for fresh agent

1. Re-anchor: checkout `cursor/hermes-agent-interaction-bar`, run §7 verification commands, confirm green.
2. Read `.hermes.md` and skim `_process_hermes_cli_query` in `live_agent_loop.py`.
3. Dogfood one question on `/plan` with Hermes backend; expand trace + retrieved text; note session id behavior under `.hermes-runtime/sessions/`.
4. Discuss with user: **Slice A (session continuity)** vs **Slice C (conversation UI)** first — both are needed; session wiring likely precedes good multi-turn UX.
5. Write a tight implementation handoff with allowlist before coding the next slice.

Do not start by re-architecting retrieval — manifest path is working; the gap is Hermes orchestration and conversation shape.

---

## 12. Branch commit map

| Commit | Summary |
|--------|---------|
| `cb0c953` (main) | R11 ingestion source bundle adapter |
| `6172166` | Route Agent Interaction through Hermes (backend toggle, plugin wiring, in-process path) |
| `eac1b8f` | Hermes trace telemetry (CLI preflight, trace UI, retrieved text consolidation, prompt preview, turn history metadata) |
