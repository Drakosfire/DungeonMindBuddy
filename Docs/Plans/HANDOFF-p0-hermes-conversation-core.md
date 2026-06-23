# HANDOFF — P0 Hermes Conversation Core

**Created:** 2026-06-22  
**Status:** READY FOR CODE AGENT  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target branch:** `feat/hermes-p0-conversation-core`  
**Suggested PR title:** `feat(hermes): add P0 conversation core`  
**Design PR branch:** `docs/p0-hermes-conversation-core`  
**Parent anchors:**

- `Docs/Design/ANCHOR-agent-interaction-hermes.md`
- `Docs/Design/UX-STORIES-agent-interaction-hermes.md`
- `Docs/Design/ANCHOR-plan-surface-agent-interaction.md`
- `.hermes.md`

---

## 0. Mission

Implement **P0 Hermes Conversation Core** for the `/plan` Agent Interaction surface.

Current `main` has a useful proof:

```txt
/plan Agent Interaction bar/pane
POST /api/live/query
query_backend = live | hermes
Hermes CLI one-shot path
preflight DungeonBuddy retrieval
context_packet returned to UI
agent_trace returned to UI
turn metadata persisted in localStorage
```

P0 moves the proof from “one-shot ask box” toward a real conversation surface:

```txt
DungeonBuddy thread ↔ Hermes session id
full thread persistence
same-thread follow-ups
trace visibility toggle
conversation UI shell
```

The core product goal:

```txt
A GM can prep in one named conversation thread, ask follow-ups without restating context, reload the browser without losing the thread, and still trust that campaign facts come from DungeonBuddy corpus/retrieval rather than Hermes memory.
```

---

## 1. Current Main State

Before coding, verify current `main`, but assume this starting point:

- `/plan` exists as the first intentional configured surface.
- `PlanAgentInteractionBar` is mounted plan-locally.
- `POST /api/live/query` accepts `query_backend` and can route to `hermes`.
- Hermes path currently uses one-shot CLI behavior.
- The backend performs preflight DungeonBuddy retrieval before Hermes synthesis.
- Responses include `context_packet` and `agent_trace`.
- UI displays context sufficiency and trace details.
- localStorage currently keeps turn metadata, not full durable conversation threads.

Read first:

```txt
Docs/Design/ANCHOR-agent-interaction-hermes.md
Docs/Design/UX-STORIES-agent-interaction-hermes.md
Docs/Design/ANCHOR-plan-surface-agent-interaction.md
.hermes.md
apps/live_control_server/services/live_agent_loop.py
apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts
apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
```

---

## 2. Product Target

P0 should satisfy the first conversational stories from `UX-STORIES-agent-interaction-hermes.md`:

```txt
S1.2 — active thread continues when I open Agent Interaction.
S1.5 — follow-up questions in the same thread use conversation history.
S4.1 — full thread history persists across reload.
S3.1/S3.2 — trace is available by user choice, not always dominant.
```

Concrete desk-prep journey:

```txt
1. GM opens /plan.
2. GM opens Agent Interaction.
3. GM asks: “What is the name of the Inn in Mireward Reach and who owns it?”
4. The answer returns with corpus-grounding and trace available.
5. GM follows up: “Does the owner know Lysandra? If so how?”
6. The follow-up remains in the same DungeonBuddy thread and resumes the same Hermes session where possible.
7. GM reloads the browser.
8. The conversation thread returns with Q/A, selected backend/session pointers, citation/proof pointers, and trace pointers.
9. Trace can be toggled on/off without deleting trace data.
```

---

## 3. Key Mental Model

DungeonBuddy owns the product thread.

Hermes owns the agent session.

DungeonBuddy corpus remains canon.

```txt
UI Thread
  - product conversation container
  - title, turns, selected backend, Hermes session id, citations/proof pointers
  - reload persistence
  - not campaign canon

Hermes Session
  - agent-orchestration continuity
  - tool-loop state / prior conversation context
  - not campaign canon

DungeonBuddy Retrieval / Corpus
  - campaign evidence and facts
  - context_packet / source evidence
  - canon authority
```

Do not let these collapse into one store.

---

## 4. Hermes Facts To Verify Before Coding

This handoff intentionally does not assume exact Hermes CLI behavior beyond what is already proven in this repo.

Before implementation, run a local Hermes investigation and record results in the PR body or a short dev note.

Verify:

```txt
1. Can non-interactive question mode be combined with resume/session id?
   Examples to test, do not assume:
   - hermes chat -q "..." --resume <session_id>
   - hermes --resume <session_id> -q "..."
   - hermes chat --continue -q "..."

2. Where does Hermes expose the current/new session id?
   - stdout?
   - session artifact path?
   - SQLite metadata?
   - log file?
   - CLI flag?

3. Can a session title be set non-interactively?
   - slash command in prompt?
   - CLI flag?
   - direct session metadata update?

4. Does HERMES_HOME isolate sessions/logs as expected?

5. Is there a programmatic API preferable to subprocess CLI for this slice?

6. What toolsets are required for DungeonBuddy?
   Expected starting point: dungeonbuddy,memory,file, but verify.

7. Does session resume preserve plugin/tool availability and environment variables?
```

Hard rule:

```txt
Do not implement fragile session-id parsing unless covered by tests and documented as temporary.
```

If Hermes cannot reliably resume non-interactive sessions yet, implement P0 with a DungeonBuddy thread model first and keep Hermes one-shot as a fallback, but leave a clear `HermesSessionHandle` seam.

---

## 5. Scope

### Backend scope

Add or extend backend support for:

```txt
AgentInteractionThread
AgentInteractionTurn
Hermes session handle
thread create/read/update/list
thread-scoped query request
thread-scoped query response
trace toggle metadata if persisted server-side
```

Possible backend files:

```txt
apps/live_control_server/services/live_agent_loop.py
apps/live_control_server/routes/live.py
apps/live_control_server/services/agent_interaction_threads.py   # new, if server-side persistence chosen
src/live_play/live_store.py                                      # only if reusing JSON helpers
```

### Frontend scope

Add or extend UI support for:

```txt
active thread state
thread title
full turn list persistence/rehydration
same-thread follow-up rendering
trace visibility toggle
Hermes session id pointer display in advanced/trace mode only
```

Possible frontend files:

```txt
apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts
apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx
```

### Tests

Update/add tests for:

```txt
backend thread creation and query continuity
Hermes resume command construction or fallback behavior
no live events/jobs for context questions
full UI thread restoration after reload
trace toggle hides/shows trace panel
turn persistence does not store raw corpus bodies beyond allowed proof snippets policy
```

---

## 6. Out of Scope

Do not implement in P0:

```txt
app-level AgentInteractionProvider hoist
cross-surface bar
React /play migration
operator tool parity
statblock generation through Hermes
NPC/table tools through Hermes
corpus write approval UI
autonomous writes
graph memory preview UI
graph query executor
in-pane full corpus citation reader, unless needed as a tiny stub
Hermes long-term memory policy
production database persistence
multi-user sync
```

P0 is conversation core only.

---

## 7. Data Boundary Rules

### Allowed in thread persistence

```txt
thread id
title
created/updated timestamps
active backend
Hermes session id / session handle
turn question text
turn answer text
citation locators / source paths / evidence ids
context summary counts
trace id / trace metadata pointer
warnings
collapsed/expanded UI preference if local
```

### Dangerous; avoid or bound carefully

```txt
full context_packet with large admitted excerpts
raw prompt sent to Hermes
absolute filesystem paths
Hermes log/session absolute paths
retrieved corpus document bodies
statblock markdown bodies
normalized recap full text
candidate graph preview payloads
```

### Not allowed as canon

```txt
Hermes memory
UI thread Q/A
agent summaries
uncited answer claims
```

Campaign facts must still come from DungeonBuddy retrieval/corpus tools.

---

## 8. Proposed Type Shape

Names can change, but keep the conceptual contract.

```ts
type AgentInteractionThread = {
  threadId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  campaignId: string;
  session?: number | null;
  surfaceId: "plan" | "play" | "build" | string;
  activeBackend: "hermes" | "live";
  hermesSession?: HermesSessionHandle | null;
  turns: AgentInteractionTurn[];
  uiState?: {
    traceVisible: boolean;
    scrollAnchorTurnId?: string | null;
  };
};
```

```ts
type HermesSessionHandle = {
  sessionId: string;
  title?: string | null;
  runtime: "cli" | "api" | "in_process" | "unknown";
  hermesHome?: string | null; // advanced/debug only; do not display as product copy
  createdAt?: string | null;
  updatedAt?: string | null;
};
```

```ts
type AgentInteractionTurn = {
  turnId: string;
  askedAt: string;
  completedAt?: string | null;
  question: string;
  answer: string;
  backend: "hermes" | "live";
  status: "ok" | "error" | "partial";
  contextSummary?: AgentInteractionContextSummary;
  citations?: LiveQueryCitation[];
  trace?: AgentInteractionTrace | null;
  warnings?: string[];
};
```

If using localStorage only for P0, version the stored object:

```txt
agent-interaction-thread-v1:<campaignId>:<threadId>
agent-interaction-active-thread-v1:<campaignId>:<surfaceId>
```

If using server-side JSON under live session dir, document that it is transitional and not long-term user-level persistence.

---

## 9. Backend Design Options

Choose one; do not mix without a reason.

### Option A — Frontend-first localStorage persistence

Best if the goal is fast P0 UI dogfood.

Pros:

```txt
minimal backend work
fast iteration
matches current metadata persistence pattern
```

Cons:

```txt
not cross-browser
not user-level
harder to share with backend or Hermes session lifecycle
```

Requirements if chosen:

```txt
backend still accepts thread_id / hermes_session_id in query request
backend returns updated hermes_session handle when available
UI persists full thread locally
tests prove rehydrate
```

### Option B — Live-control server JSON persistence

Best if backend needs to own Hermes session handles.

Pros:

```txt
server owns session id mapping
more testable query continuity
persistence survives browser localStorage clearing
```

Cons:

```txt
still tied to live session dir unless carefully scoped
not final user-level storage
```

Requirements if chosen:

```txt
new service for thread store
route endpoints for list/read/create/update
atomic JSON writes via existing helpers
no corpus bodies in thread store
```

### Recommendation

Prefer **Option B if Hermes session id reuse is reliable**, because session mapping is backend-runtime concern.

Prefer **Option A if Hermes session id reuse is not reliable yet**, but preserve the backend request/response seam.

Do not block P0 on perfect long-term storage.

---

## 10. API Contract Direction

Current endpoint:

```txt
POST /api/live/query
```

Extend request with optional thread/session fields:

```ts
type LiveQueryRequest = {
  campaign_id: string;
  session: number;
  mode: "live";
  text: string;
  query_backend?: "live" | "hermes";
  manifest_path?: string | null;

  // P0 additions
  agent_thread_id?: string | null;
  hermes_session_id?: string | null;
  trace_requested?: boolean | null;
};
```

Extend response with thread/session fields:

```ts
type LiveQueryResponse = {
  answer: string;
  context_packet?: LiveContextPacket | null;
  agent_trace?: AgentInteractionTrace | null;

  // P0 additions
  agent_thread_id?: string | null;
  turn_id?: string | null;
  hermes_session?: HermesSessionHandle | null;
};
```

If server owns persistence, add thread routes:

```txt
GET    /api/live/agent-interaction/threads
POST   /api/live/agent-interaction/threads
GET    /api/live/agent-interaction/threads/{thread_id}
PATCH  /api/live/agent-interaction/threads/{thread_id}
```

Keep routes thin. Put logic in a service module.

---

## 11. Hermes Invocation Contract

Current Hermes CLI mode is controlled by environment variables in `live_agent_loop.py`.

P0 should add a single function boundary for session-aware Hermes invocation, even if internals remain subprocess-based.

Suggested backend seam:

```py
@dataclass(frozen=True)
class HermesConversationRequest:
    prompt: str
    thread_id: str | None
    hermes_session_id: str | None
    trace_requested: bool
    toolsets: tuple[str, ...]

@dataclass(frozen=True)
class HermesConversationResult:
    answer: str
    hermes_session_id: str | None
    trace: dict[str, Any]
    warnings: list[str]
```

Suggested function:

```py
def run_hermes_conversation(request: HermesConversationRequest) -> HermesConversationResult:
    ...
```

Do not let CLI argument construction sprawl through `process_live_query`.

---

## 12. UI Behavior

### Default pane

When opened:

```txt
show active thread
show thread title
show turn list
show ask box
show trace toggle
```

For P0, the thread switcher can be minimal:

```txt
active thread only
New thread button optional
thread title generated from first question or editable simple input
```

Do not build the full 2–3 parallel thread switcher unless it is cheap and covered by tests. That is P2.

### Collapsed bar

Target steady-state copy:

```txt
Agent Interaction · <thread title>
```

No snippets. No noisy counts. No trace text.

### Trace toggle

Trace exists for dogfood, but should not dominate normal prep.

```txt
Trace: Off | On
```

When off:

```txt
hide TraceDetailsPanel
keep citations/evidence summary visible if present
```

When on:

```txt
show TraceDetailsPanel per selected/latest turn
```

Persist trace toggle per surface/campaign or thread.

---

## 13. Acceptance Criteria

P0 is complete when:

```txt
- A GM can ask a Hermes-backed question in /plan.
- The UI creates or uses an active Agent Interaction thread.
- The follow-up question sends thread/session identifiers to the backend.
- Backend attempts to resume the same Hermes session when supported.
- If resume is unsupported, fallback is explicit in trace/warnings and thread model still works.
- Full thread Q/A survives browser reload.
- Trace visibility is user-toggleable.
- Trace hidden does not delete trace/proof data.
- Corpus retrieval preflight still runs for Hermes factual questions.
- context_packet still returns to the UI.
- No context question writes live events/jobs.
- No autonomous corpus writes exist.
- No raw corpus bodies or large context packets are stored in localStorage/thread persistence.
- Tests cover persistence, follow-up, trace toggle, and backend session handle behavior.
```

---

## 14. Test Plan

### Backend tests

Add/extend:

```txt
tests/test_live_control_server.py
tests/test_hermes_dungeonbuddy_plugin.py
```

Required cases:

```txt
1. Hermes query returns agent_thread_id / turn_id / hermes_session when available.
2. Second Hermes query with same thread/session attempts resume path.
3. CLI command construction includes resume/session flag only when verified supported.
4. Missing/unsupported Hermes session resume returns warning but still answers through fallback.
5. Context questions do not write event_log/job_queue.
6. Preflight context lookup still returns context_packet.
```

Use monkeypatch/fake subprocess. Do not require real Hermes binary in CI.

### Frontend tests

Extend:

```txt
apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx
```

Required cases:

```txt
1. User asks first question; thread appears with generated title and turn.
2. User asks follow-up; prior thread id/session id are sent.
3. Reload/re-render restores full Q/A turn history.
4. Collapsed bar shows thread title only.
5. Trace toggle hides/shows trace details.
6. localStorage payload does not include context_packet or large text_excerpt body fields.
```

If new helper tests are useful:

```txt
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts
```

---

## 15. Verification Commands

Run before requesting review:

```bash
uv run pytest tests/test_live_control_server.py tests/test_hermes_dungeonbuddy_plugin.py -q
cd apps/live-control-ui && npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx
cd apps/live-control-ui && npm run build
```

If touching manifest retrieval:

```bash
uv run pytest tests/test_manifest_context_query.py -q
```

---

## 16. Manual Smoke

With local Hermes installed/configured:

```bash
export HERMES_HOME="$PWD/.hermes-runtime"
export DUNGEONBUDDY_REPO="$PWD"
export DUNGEONBUDDY_CORPUS_ROOT="$PWD/corpus"
export DUNGEONMIND_LIVE_HERMES_MODE=cli
export DUNGEONMIND_LIVE_HERMES_PROVIDER=custom
export DUNGEONMIND_LIVE_HERMES_MODEL=gpt-5.4-mini
uv run uvicorn apps.live_control_server.main:app --reload --port 8000
```

Then:

```txt
1. Open /plan.
2. Open Agent Interaction.
3. Ask Hermes: “What is the name of the Inn in Mireward Reach and who owns it?”
4. Confirm answer returns and trace can be opened.
5. Ask follow-up: “Does the owner know Lysandra?”
6. Confirm same DungeonBuddy thread is used.
7. Confirm Hermes session resume is used or fallback warning appears.
8. Reload browser.
9. Confirm full Q/A thread returns.
10. Toggle trace off/on.
```

---

## 17. Review Focus

Reviewer should check:

```txt
- Did the implementation preserve corpus-as-canon?
- Is Hermes session continuity real, tested, or explicitly marked fallback?
- Does thread persistence avoid becoming a second corpus?
- Does the UI feel like a conversation thread rather than a one-shot form?
- Is trace available but not forced into normal view?
- Are write boundaries untouched?
- Are graph memory and Play migration kept out of P0?
```

---

## 18. Suggested PR Body

```md
## Summary

Implements P0 Hermes Conversation Core for the `/plan` Agent Interaction pane.

This adds a DungeonBuddy Agent Interaction thread model, full thread persistence across reload, same-thread follow-up plumbing, Hermes session handle support where available, and a user-controlled trace visibility toggle. Corpus/retrieval remains the factual authority; Hermes session memory is orchestration context only.

## Scope

- Agent Interaction thread model
- Full thread turn persistence
- Hermes session handle plumbing / resume attempt
- Follow-up query continuity
- Trace visibility toggle
- Tests for persistence, follow-up, trace toggle, and backend session handling

## Out of scope

- App-level AgentInteractionProvider hoist
- React `/play` migration
- Operator tool parity
- Autonomous writes
- Graph memory preview UI
- Corpus write approval flow
- Hermes long-term memory policy

## Verification

- [ ] `uv run pytest tests/test_live_control_server.py tests/test_hermes_dungeonbuddy_plugin.py -q`
- [ ] `cd apps/live-control-ui && npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx`
- [ ] `cd apps/live-control-ui && npm run build`

## Manual smoke

- [ ] Ask first Hermes-backed question in `/plan`.
- [ ] Ask follow-up in same thread.
- [ ] Reload and confirm full thread returns.
- [ ] Toggle trace off/on.
- [ ] Confirm preflight retrieval/context packet remains present.
```

---

## 19. Final Instruction To Code Agent

Do not try to solve “all Hermes integration.”

This PR is successful if the GM can have one persistent, same-thread Hermes-backed prep conversation in `/plan`, with trace available on demand, while DungeonBuddy corpus remains the source of truth.

If Hermes session resume is uncertain, build the DungeonBuddy thread model and a clean `HermesSessionHandle` seam first. Do not fake continuity by silently stuffing all prior turns into a prompt without naming that behavior in trace/warnings.
