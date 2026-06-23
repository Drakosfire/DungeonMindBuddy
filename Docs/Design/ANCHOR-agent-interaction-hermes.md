# Anchor — Agent Interaction + Hermes

**Status:** Active anchor  
**Created:** 2026-06-23  
**Scope:** Plan-mode Agent Interaction bar/pane, Hermes-backed conversation, manifest retrieval, multi-thread UX, operator tool parity  
**Parent:** `Docs/Design/ANCHOR-plan-surface-agent-interaction.md` (surface ladder, R10/R11, ingestion vocabulary)

Start here to re-anchor or jumpstart an agent on **conversational Hermes prep** — not chat history.

---

## Executive summary

**What it is:** A bottom **Agent Interaction** surface on `/plan` where the GM preps at the desk (before session) and reviews after (ingestion). **Hermes** is the target default backing agent: multi-turn conversation, full operator tool access, corpus-grounded prose answers with in-pane citations. **Manifest retrieval** (`dungeon_context_lookup`) remains the evidence layer; corpus is canon, not Hermes memory.

**What works today (spike, branch `cursor/hermes-agent-interaction-bar` ~`eac1b8f`):**

- Ask field + backend route (`live` | `hermes`) via `POST /api/live/query`
- Hermes CLI one-shot with **preflight retrieval** (context packet always returned)
- Inspectable trace: retrieved text, prompt preview, token estimates, steps (partial)
- Turn metadata in `localStorage` (not full thread bodies on reload)
- Each Hermes turn = **new** `--oneshot` — no session continuity yet

**Where we're going (UX locked — see stories doc):**

| Track | Target |
|-------|--------|
| Hermes session continuity | Reuse session across turns, not one-shot per message |
| Conversation UI | Named threads, 2–3 parallel arcs/day, full persist on reload |
| Live corpus coherence | Every thread read/write; writes in thread A visible in thread B |
| Citations | Prose + links → full doc **inside Agent Interaction pane** |
| Trace | **User toggle** |
| New thread | **Auto-suggest after N turns** |
| Tools | All operator tools (statblock, NPC, tables, …); writes **preview → GM confirm only** |
| R10 | Bar follows across surfaces; collapsed = **thread title only** |

**Not done:** Multi-turn Hermes sessions, parallel thread switcher, in-pane corpus reader, trace toggle, full thread persistence, tool parity beyond retrieval, R10 provider hoist.

---

## Example user stories (acceptance anchors)

Full catalog: `Docs/Design/UX-STORIES-agent-interaction-hermes.md`

**Journey — Mireward inn prep**

1. *As a GM*, I ask: *"What is the name of the Inn in Mireward Reach and who owns it, what are its prices and what does it offer?"*  
   → Prose answer with **corpus-linked facts**; click link → **full rendered doc in Agent Interaction pane**.

2. *As a GM*, I follow up in the **same thread**: *"Does the owner know Lysandra? If so how?"*  
   → Uses **thread + Hermes session context**; does not blindly re-retrieve inn docs; cites new evidence where needed.

3. *As a GM*, I **reload the browser** → full thread returns (Q/A, links, trace pointers).

4. *As a GM*, I run **ingestion in the same thread**, then ask *"what changed?"* → answer reflects **live canon**.

**Parallel threads + live canon**

5. *As a GM*, I keep **"Inn prep"** and **"S23 ingest"** as two named threads and switch same day → each **resumes scroll/focus**; ingest in one thread → factual ask in the other sees **updated corpus**.

**Trust & control**

6. *As a GM*, I toggle **trace on** during dogfood, **off** when citations feel enough.

7. *As a GM*, when the agent proposes a corpus write → **preview diff only**; nothing commits until I approve.

---

## Path index (read these, not chat)

### Design & UX (start here for product intent)

| Path | Role |
|------|------|
| `Docs/Design/UX-STORIES-agent-interaction-hermes.md` | **Full user stories**, interview decisions, build phases P0–P6 |
| `Docs/Design/ANCHOR-plan-surface-agent-interaction.md` | Surface ladder, R10/R11, provider invariants |
| `Docs/Plans/HANDOFF-self-continuity-hermes-agent-interaction-bar.md` | Engineering handoff: spike learnings, env vars, verification |
| `Docs/Plans/HANDOFF-self-continuity-plan-toolbar-ingestion-design.md` | Bar/pane ownership, ingestion proof, R10 direction |
| `.hermes.md` | Hermes policy: corpus canon, memory rules, plugin install |

### Frontend — Agent Interaction (extend, don't redesign)

| Path | Role |
|------|------|
| `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` | Main bar + pane shell, ask, backend select, turn history |
| `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx` | Agent trace (→ add user toggle) |
| `apps/live-control-ui/src/planSurface/components/ContextSufficiencyPanel.tsx` | Retrieved text / evidence display |
| `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts` | Turn metadata persistence (→ full thread bodies) |
| `apps/live-control-ui/src/planSurface/components/contextSufficiencyLadder.ts` | Ladder + admitted items for UI |
| `apps/live-control-ui/src/planSurface/planSurface.css` | `.plan-agent-shell`, `.plan-agent-bar`, `.plan-agent-pane` |
| `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx` | Mounts Agent Interaction on `/plan` |
| `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | UI tests for ask/trace/backends |
| `apps/live-control-ui/src/api/types.ts` | `AgentInteractionTrace`, `LiveQueryResponse`, thread types |
| `apps/live-control-ui/src/api/liveApi.ts` | `postLiveQuery`, `query_backend` |

### Backend — query loop & trace

| Path | Role |
|------|------|
| `apps/live_control_server/services/live_agent_loop.py` | **`process_live_query`**, Hermes CLI path, preflight, `agent_trace` |
| `apps/live_control_server/routes/live.py` | `POST /api/live/query`, `query_backend` validation |
| `src/live_play/manifest_context_query.py` | Manifest retrieval, session scoping, admission |
| `src/live_play/source_bundle.py` | `IngestionSourceBundle` (ingestion proof in bar) |

### Hermes plugin & runtime

| Path | Role |
|------|------|
| `integrations/hermes/plugins/dungeonbuddy/__init__.py` | `dungeon_context_lookup`, manifest tools, legacy lexical fallback |
| `integrations/hermes/plugins/dungeonbuddy/skills/dungeonbuddy-corpus-qa/SKILL.md` | Agent skill (→ cite-or-abstain hardening) |
| `scripts/hermes_spike_install_plugin.sh` | Symlink plugin into `$HERMES_HOME` |
| `.hermes-runtime/` (local, gitignored) | Scoped Hermes home, config, sessions, logs |

### Tests & smoke

| Path | Role |
|------|------|
| `tests/test_live_control_server.py` | Hermes CLI routing, trace, context packet assertions |
| `tests/test_hermes_dungeonbuddy_plugin.py` | Plugin tools without Hermes binary |
| `tests/test_live_query_manifest_context.py` | Retrieval/session scoping |
| `evals/hermes_spike/questions.jsonl` | Manual Hermes eval questions |

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
2. **Preflight retrieval** — Hermes path returns `context_packet` + embeds excerpts in prompt; zero admitted + confident answer = bug.
3. **No autonomous writes** — preview → explicit GM confirm; benchmark before any loosening.
4. **Pointers in persistence** — thread storage: Q/A, citation locators, trace ids; not a second corpus store (R10 rule).
5. **Live reads across threads** — factual answers ground on **current** corpus after ingest/write in any thread.
6. **UI stays in the bar/pane** — citations and corpus reader inside Agent Interaction chrome; do not take over plan canvas.
7. **Session scope** — session-number questions must not admit wrong-session recaps (regression-sensitive).

---

## Build sequence (from UX doc)

| Phase | Focus |
|-------|--------|
| **P0** | Hermes session id reuse, full thread persist, conversation UI shell, trace toggle |
| **P1** | In-pane citation reader, cite-or-abstain skill |
| **P2** | Named parallel threads, quick switch + resume, N-turn auto-suggest |
| **P3** | Agent decides re-retrieve vs thread context; corpus change signals |
| **P4** | R10 `AgentInteractionProvider`, cross-surface bar |
| **P5** | Full operator tool parity via Hermes |
| **P6** | Hermes memory integration (non-canon layers only) |

**Next slice to implement:** P0 — see `UX-STORIES-agent-interaction-hermes.md` § Interview status.

---

## Verification (minimum)

```bash
uv run pytest tests/test_live_control_server.py tests/test_hermes_dungeonbuddy_plugin.py -q
cd apps/live-control-ui && npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx
cd apps/live-control-ui && npm run build
```

**Behavioral smoke:** `/plan` → Agent Interaction → Hermes backend → ask Session-scoped question → trace shows admitted evidence > 0, `prompt_preview` present.

---

## Re-anchor procedure

1. Read this anchor (executive summary + invariants).
2. Run `git status --short --branch` — confirm branch (Hermes work: `cursor/hermes-agent-interaction-bar` or descendant).
3. Skim `Docs/Design/UX-STORIES-agent-interaction-hermes.md` for story IDs relevant to your slice.
4. Read only the **path index** files your slice touches.
5. Re-run verification commands above before claiming done.
6. For surface-wide context (R10, ingestion vocabulary), read parent `ANCHOR-plan-surface-agent-interaction.md`.

**Stale-note discipline:** Re-verify branch tip, "what works today," and any pending PR claims before quoting them in a new handoff.

---

## Related anchors & handoffs

| Document | When |
|----------|------|
| `Docs/Design/UX-STORIES-agent-interaction-hermes.md` | Full stories, Round 1–3 decisions |
| `Docs/Plans/HANDOFF-self-continuity-hermes-agent-interaction-bar.md` | Spike engineering detail, plugin warnings |
| `Docs/Design/ANCHOR-plan-surface-agent-interaction.md` | R10/R11 ladder, surface architecture |
| `Docs/Plans/HANDOFF-prep-agent-c2-ingest-s21-plan-s22-cursor-first.md` §9 | Hermes vs dogfood retrieval history |
