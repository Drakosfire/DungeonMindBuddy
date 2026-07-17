---
pr_body_template: |
  ## Outcome

  A GM can use the existing Plan Agent Interaction pane to ask one Hermes question and receive a correctly labeled graph-grounded, qualified, abstained, or failed answer with revision-pinned source-anchor citations, safe graph-tool trace, and reload-safe local turn metadata—without path-based evidence access or conversational-continuity claims.

  ## Scope and verification

  - Predecessor base: `827e34adc93705c1b44a97ab3d3c00afdaf7340e` — merge of GitHub PR #354
  - Implementation base: `<docs-only commit that lands this handoff; record exact SHA before dispatch>`
  - Changed paths: report the actual §4 paths only
  - Verification: report every §7 command and manual scenario with exact result and provenance
  - Baseline failures and waivers: compare the owning suites on implementation base and head; write `none` when none exist
  - Deferred successors: same-thread Hermes continuity, persisted Hermes session identity, product-path demolition, backend-toggle removal, and all write-capable tools
---

# HANDOFF — PR355: Plan Hermes graph evidence presentation and reload-safe turn persistence

**Created:** 2026-07-14  
**Status:** ACTIVE — dispatch exactly one implementation capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr355-plan-hermes-graph-evidence-presentation.md`  
**Predecessor base:** `827e34adc93705c1b44a97ab3d3c00afdaf7340e` — merge of GitHub PR #354  
**Reviewed PR354 head:** `97f4a09ba22260198b542ea852946c562568fd37`  
**Implementation base:** the docs-only commit that lands this handoff on `main`; record the immutable SHA before dispatch  
**Suggested branch:** `agent/pr010b4c-plan-hermes-graph-evidence`  
**Suggested PR title:** `feat(plan): present and persist Hermes graph evidence`

> **Dispatch rule**
>
> Commit this complete handoff before dispatch. Use that docs-only commit as the implementation base. It must descend from the accepted PR354 merge commit and contain no production-code changes.
>
> Consume PR354 as a stable predecessor. Do not reopen graph-agent hosting, IPC, retry, grounding classification, tool-event recovery, or graph-context resolution design except for the narrowly permitted citation projection in §4.
>
> Opening PR355 is the final repository action for this dispatch. Stop after opening it. Do not begin PR010B Rung 5.

---

## §0 Capability decomposition decision

PR354 made one server-side Hermes graph turn real, typed, fail-closed, and reachable through `POST /api/live/query`. It deliberately left the result unusable as a complete Plan interaction: `citations=[]`, graph tool events are untyped in the browser, the path-only source reader cannot open an opaque graph anchor, safe graph trace is discarded during local persistence, and the current request serializer still sends fields PR354 rejects.

PR355 is one cross-layer product capability: faithfully present and preserve one already-completed PR354 turn.

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Project accepted PR354 source-anchor IDs into an explicit graph-citation response variant | No — required evidence contract for the selected capability | Yes | Indirectly | Yes | Yes | Include |
| Serialize Hermes requests without legacy manifest or unsupported session fields | No — required to reach the merged backend from Plan | Yes | No | Yes | Yes | Include |
| Present PR354 grounding states as grounded, qualified, evidence-gap, or execution-error UX | No — required interpretation of the selected capability | Yes | Yes | Yes | Yes | Include |
| Open graph evidence through the existing revision-pinned opaque source-anchor route | No — required evidence interaction | Yes | Yes | Yes | Yes | Include |
| Render bounded graph-tool events in the existing trace drawer | No — required inspectability | Yes | Yes | Yes | Yes | Include |
| Persist answer, grounding, graph citations, and sanitized graph trace in the existing local thread record | No — required reload behavior for the same completed turn | Yes | Yes | Yes | Yes | Include |
| Keep Hermes usable when the legacy source-bundle diagnostics request fails | No — removes a legacy UI precondition from the same graph-only interaction | No new public contract | Yes | Yes | Yes | Include |
| Prove one positive graph-evidence journey and one graph-gap journey in the existing Plan surface | No — acceptance proof for the selected capability | No | Yes | Yes | Yes | Include as verification |
| Send prior turns into Hermes and resolve “it” or other same-thread shorthand | Yes | Yes | Yes | Yes | Yes | Successor — PR010B Rung 5 |
| Persist or resume a Hermes session pointer across reload or process restart | Yes | Yes | Yes | Yes | Yes | Successor — PR010B Rung 6 |
| Remove legacy Hermes retrieval, CLI one-shot, Live fallback, or the backend selector | Yes | Yes | Yes | Yes | Yes | Successor — PR010B Rung 7 |
| Make Hermes the default or only Plan backend | Yes | Yes | Yes | Yes | Yes | Successor — PR010B Rung 7 after dogfood acceptance |
| Add server-side thread storage or cross-device synchronization | Yes | Yes | Yes | Yes | Yes | Successor — not this slice |
| Add drafts, writes, preview/confirm, or governed operator tools | Yes | Yes | Yes | Yes | Yes | Successor — PR011 |
| Redesign Agent Interaction or add a separate graph-evidence surface | Yes | Yes | Yes | Yes | Yes | Reject |

**Selected capability**

```text
The existing Plan Agent Interaction pane faithfully presents and locally preserves one merged PR354 Hermes graph turn, including its grounding state, opaque revision-pinned evidence citations, bounded graph-tool trace, and explicit failure state.
```

**Why the included rows share one invariant**

The backend citation projection, request serializer, answer presentation, source-anchor reader, trace rendering, persistence sanitizer, and dogfood proof all establish the same trust property: the evidence a GM sees and can reopen is exactly the evidence PR354 admitted for that turn, at that turn’s authoritative graph scope and revision.

**Named successors**

1. **PR010B Rung 5 — same-thread object continuity:** bounded prior-turn history and explicit conversational identity sufficient to resolve pronouns while performing fresh graph reads.
2. **PR010B Rung 6 — Hermes session-pointer continuity:** durable thread-to-session binding and reload/process-restart resume without treating chat as campaign canon.
3. **PR010B Rung 7 — acceptance and demolition:** remove obsolete Hermes product retrieval, CLI one-shot behavior, Live synthesis fallback, and the steady-state backend selector after accepted dogfood.
4. **PR011 — Agent Context + governed tools:** typed read/draft/preview/confirm capabilities and proposal-bound writes.

---

## §1 Mission

```text
A GM can use the existing Plan Agent Interaction pane to ask one Hermes question and receive a correctly labeled graph-grounded, qualified, abstained, or failed answer with revision-pinned source-anchor citations, safe graph-tool trace, and reload-safe local turn metadata—without path-based evidence access or conversational-continuity claims.
```

**Invariant**

```text
Every graph-grounding label, persisted citation, source read, and graph-tool detail shown for a Plan Hermes turn must be a bounded projection of the merged PR354 product envelope at the exact server-resolved world, campaign, focus, admissibility, and revision; model prose, trace presence, display labels, local paths, stale session handles, and legacy retrieval metadata can never create, upgrade, rebind, or rescue evidence.
```

**Mission falsification test**

```text
This is not one slice if implementation must send prior turns, establish or resume a Hermes session, change PR354 grounding/recovery semantics, add a new graph retrieval operation, introduce server-side thread persistence, remove the backend selector, demolish legacy code, redesign the Agent Interaction surface, or add any write-capable tool.
```

---

## §2 Context, authority, and boundaries

| Field | Required content |
| --- | --- |
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; `Docs/Design/ANCHOR-agent-interaction-hermes.md`; `Docs/Design/UX-STORIES-agent-interaction-hermes.md` |
| Repository rules | `AGENTS.md`; `.cursor/rules/external-agent-pr-loop.mdc`; `.cursor/skills/external-agent-pr-loop/SKILL.md`; canonical HANDOFF template |
| Predecessor base | `827e34adc93705c1b44a97ab3d3c00afdaf7340e` — merge of GitHub PR #354 |
| Implementation base | Docs-only commit that lands this handoff on `main`; record immutable SHA before dispatch |
| Predecessor contract | PR354 `dmb_live_query_response_v1`, `dmb_hermes_graph_grounding_v1`, typed fail-closed error behavior, safe projected `agent_trace.tool_events`, `hermes_session=None`, and exact no-fallback behavior; PR010A source-anchor read request/result contract and existing route |
| Exact input consumed | Existing Plan `postLiveQuery(...)` result for `query_backend="hermes"`, plus explicit citation clicks against the existing PR010A source-anchor read route |
| Named successor | PR010B Rung 5 — same-thread object continuity |
| What remains false | No prior turn reaches Hermes; no pronoun resolution is claimed; no Hermes session is persisted or resumed; no server-side thread store exists; Hermes is not the default backend; legacy product code and selector remain; no writes exist |
| Explicit non-goals | Host/IPC changes, new routes, new retrieval operations, graph-schema changes, graph writes, arbitrary source browsing, path conversion, raw tool-result persistence, app-wide provider hoist, Play integration, broad UI redesign, source-bundle migration, or cleanup outside the named paths |

### Accepted predecessor state

PR354 is merged. Treat these behaviors as stable predecessor guarantees:

1. The server resolves authoritative graph scope and revision.
2. One Hermes graph-agent host execution occurs per accepted request.
3. Grounding classification is server-owned and has exactly four states: `grounded`, `partial`, `abstained`, `error`.
4. Evidence-bearing completions fail closed on authoritative scope, canonical outcome, and source-anchor presence.
5. Ordered tool errors are typed; a later evidence-bearing completion can explicitly recover an earlier error, while a later unrecovered error fails the turn.
6. Contradictory-scope and malformed events fail safely and leak no event data.
7. The product response includes a safe trace shell and bounded projected tool events.
8. `citations` is intentionally empty.
9. `hermes_session` is intentionally `null`; trace session identity is observability only.
10. No legacy manifest, corpus, lexical, arbitrary-path, CLI-one-shot, or Live-synthesis fallback contributes to a Hermes answer.

PR355 must not duplicate or reinterpret this state machine in the browser. The browser consumes `grounding.state`; it does not reclassify raw tool events.

### Current consumer gaps that constrain this slice

The current Plan consumer is not yet compatible with the merged product contract:

- `postLiveQuery` always sends `manifest_path` and `hermes_session_id`, including for Hermes, although PR354 rejects non-null values.
- `LiveQueryResponse` does not type the additive `grounding` block.
- `LiveQueryCitation` requires a repository path and cannot represent an opaque graph anchor.
- the source reader always calls `/api/live/citation-source` with a path;
- `hasGrounding()` checks only legacy context packets or citations and labels a typed Hermes abstention/error as an “Ungrounded draft”;
- `TraceDetailsPanel` ignores `agent_trace.tool_events`;
- `safeTraceForPersistence()` drops graph tool events;
- local turn persistence has no grounding field;
- `response.hermes_session ?? currentThread.hermesSession` can retain a stale pre-PR354 session handle;
- opening the Agent Interaction pane gates the question UI on a legacy source-bundle diagnostics load;
- path-oriented citation freshness must not be applied to opaque graph-anchor citations.

### Read authoritative inputs in this order

1. `AGENTS.md`
2. `.cursor/rules/external-agent-pr-loop.mdc`
3. `.cursor/skills/external-agent-pr-loop/SKILL.md`
4. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
5. `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
6. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
7. `Docs/Design/ANCHOR-agent-interaction-hermes.md`
8. `Docs/Design/UX-STORIES-agent-interaction-hermes.md`
9. `Docs/Plans/HANDOFF-pr354-hermes-single-turn-backend-cutover.md`
10. `apps/live_control_server/services/hermes_graph_query.py`
11. `src/graph_memory/retrieval/models.py`
12. `apps/live_control_server/routes/world_graph_retrieval.py`
13. `apps/live-control-ui/src/api/types.ts`
14. `apps/live-control-ui/src/api/liveApi.ts`
15. `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`
16. `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx`
17. `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx`
18. `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
19. owning backend and frontend tests named in §4
20. this checked-in handoff

### Authority precedence

```text
1. Current repository architecture and accepted decisions
2. Current Campaign Supergraph roadmap and PR tracker after this handoff is checked in
3. This checked-in handoff
4. Merged PR354 and PR010A public contracts
5. Current repository implementation and owning tests
6. Project Sources, historical handoffs, proposals, and chat summaries
```

If `main` moves beyond the recorded implementation base, another branch changes a §4 production path, or the predecessor response/source-anchor shapes differ materially from §6, stop and report whether the handoff must be re-anchored.

---

## §3 Observable-path inventory

| Observable path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
| --- | --- | --- | ---: | --- |
| Select **Hermes tools** and submit a question | Client always sends the legacy planning manifest and may send a stored Hermes session ID; PR354 rejects them | Hermes request omits both fields entirely, includes graph context and UI thread ID, and sends no prior turns | Yes | `liveApi.ts` serializer + Plan integration test |
| Browser graph projection is still loading | Submit is currently disabled globally | Hermes submit remains disabled until a usable request scope can be formed; existing Live behavior need not be redesigned | Yes | Plan component |
| Browser graph projection fails but the server can resolve scope | UI says the query will continue “unpinned,” which is no longer accurate | Explain that the server will resolve the authoritative revision; do not claim an unpinned Hermes execution | Yes | Plan component copy/test |
| Legacy source-bundle diagnostics load fails | Question form is hidden because the entire content area is gated on `bundle` | Agent Interaction question, threads, answers, graph citations, and trace remain usable; only legacy diagnostics show an error/unavailable state | Yes | Plan component |
| PR354 returns `grounding.state="grounded"` with graph citations | UI cannot type grounding or citations | Show a **Graph-grounded answer** label and concise supporting-evidence affordance | Yes | Backend response + Plan presentation |
| PR354 returns `grounding.state="partial"` with graph citations | Generic status/ungrounded logic | Show a **Qualified graph answer** label and the server warning; preserve usable citations | Yes | Plan presentation |
| PR354 returns `grounding.state="abstained"` | Stable abstention text is mislabeled as an ungrounded draft | Show **Graph evidence gap** and coverage diagnostics/warnings; no citation cards and no generic draft warning | Yes | Plan presentation |
| PR354 returns `grounding.state="error"` or graph unavailable | Stable error text is treated as an ordinary answer | Show **Hermes graph error** with typed diagnostic; no citations, no path reader, no fallback | Yes | Plan presentation |
| Backend constructs graph citations | `citations=[]` | Emit one opaque citation per unique source anchor accepted for the final grounded/partial result, preserving first-seen order and exact dispatched scope/revision | Yes | `hermes_graph_query.py` |
| Error then later evidence-bearing completion | PR354 classifies as recovered success | Emit citations only from accepted evidence-bearing completions; preserve PR354 recovery semantics | Yes | Backend response tests |
| Evidence-bearing completion then later unrecovered error | PR354 classifies as error | Emit no citations and preserve the typed error | Yes | Backend response tests |
| Scope-mismatched or malformed event mixed with valid data | PR354 fails the product envelope closed | Emit no citations and leak no foreign/malformed identifier | Yes | Backend response serialization tests |
| Model prose contains anchor-like text | Could tempt a consumer to parse prose | Never create a citation from answer text, messages, or trace strings | Yes | Backend tests |
| Click a graph citation | UI calls path-based `/api/live/citation-source` | Call existing `POST /api/live/world-graph/retrieval/source-anchor/read` with exact opaque anchor and exact pinned scope/revision | Yes | API client + Plan component |
| Source-anchor read returns content at exact scope | No graph reader | Display bounded content and metadata without inventing or exposing a repository path | Yes | Plan source reader |
| Source-anchor read returns `partial` or `truncated` | No graph reader | Display available content with a qualification/truncation warning | Yes | Plan source reader |
| Source-anchor read returns `empty`, `denied`, or `unavailable` | No graph reader | Display a stable no-content state; never fall back to current head or path reader | Yes | Plan source reader |
| Source-anchor read response contradicts citation ID or scope/revision | No graph reader | Reject the response as a contract error and render no content | Yes | Client validation + tests |
| Retry source-anchor click | Existing button can be clicked again | Retry the same exact pinned request only; no revision rebinding | Yes | Plan component |
| Trace Off | Graph tool events exist but are ignored | Answer remains answer-first; no graph trace details render | Yes | Plan component |
| Trace On | Existing panel renders only legacy shell fields | Existing trace drawer additionally shows bounded tool name/state/duration/outcome, graph scope/revision, matched node IDs, relationship IDs, source-anchor IDs, and diagnostic codes | Yes | Trace component |
| Malformed trace payload in client | `tool_events` is `unknown[]` | Sanitize/ignore malformed entries; do not crash or render arbitrary objects | Yes | Types/helper/component tests |
| Save a grounded/partial turn | Graph grounding and tool events are not persisted | Persist bounded grounding, opaque citations, and sanitized trace under existing local thread storage | Yes | `agentInteractionHistory.ts` |
| Save abstained/error turn | Generic answer/status persists | Persist typed grounding state and diagnostics needed to render the same state after reload; persist no graph citations | Yes | Storage |
| Persist source read content | Source preview is component state today | Continue to persist no source body, hash, or read response | Yes | Storage/no-leak tests |
| Persist graph trace | `safeTraceForPersistence` drops tool events | Persist only the explicit safe graph-tool whitelist and bounded ID lists; never prompt, message, source content, path, raw args, or arbitrary event fields | Yes | Storage sanitizer |
| Reload Plan | Saved turn reconstructs an incomplete `LiveQueryResponse` without grounding | Reconstruct and display the same answer state, graph citations, grounding summary, and safe trace without re-running Hermes or source reads | Yes | Plan + storage integration |
| Click a saved citation after reload | No graph citation survives | Re-read the exact persisted anchor at its original revision/scope | Yes | Plan integration |
| Submit another Hermes turn after reload | Stored stale session may be forwarded | New turn is independent; serializer sends no Hermes session and no prior turns | Yes | API/provider/storage tests |
| Consume a PR354 response while thread contains a stale Hermes handle | Nullish fallback preserves stale handle | Clear the stored handle for `mode="hermes_graph_agent"`; trace session ID remains observability-only | Yes | Provider/component tests |
| Legacy Live answer with path citation | Existing behavior works | Continue rendering/opening path citation through the existing path route and freshness flow | Yes | Regression tests |
| Path citation freshness on graph citation | Graph citation lacks a path | Do not build path evidence snapshots or show path-oriented corpus freshness controls for graph citations | Yes | Storage + Plan tests |
| Manual positive dogfood | Backend exists but complete Plan journey is unproven | Real Plan request shows answer, citation click, trace, exact revision, reload-safe turn | Yes | Existing surface/manual proof |
| Manual graph-gap dogfood | Backend abstention exists but UI journey is unproven | Real graph gap shows honest evidence-gap state and no hidden fallback or source card | Yes | Existing surface/manual proof |

No row authorizes same-thread pronoun resolution, Hermes session persistence, default-backend changes, demolition, or writes.

---

## §4 Files in scope — allowlist

Every changed path must appear below. The handoff itself is committed before dispatch and belongs to the implementation base, not the implementation diff.

### Authority synchronization

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Mark PR354 done, define PR355 precisely, and keep Rung 5–7 separate |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Reconcile the critical path and dogfood ladder to the same accepted sequence |

### Backend response projection

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Modify | `apps/live_control_server/services/hermes_graph_query.py` | Add the opaque graph-citation product projection from already accepted PR354 evidence; do not change host dispatch or grounding/recovery semantics |
| Modify | `tests/test_live_query_hermes_graph.py` | Prove citation identity, ordering, state gating, recovery ordering, no-leak behavior, and unchanged PR354 failure classifications |

### Frontend API, state, presentation, and persistence

| Action | Path | Purpose: how this establishes or proves §1 |
| --- | --- | --- |
| Modify | `apps/live-control-ui/src/api/types.ts` | Add exact grounding, graph-citation, graph-tool-event, and source-anchor-read wire types while retaining legacy variants |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Serialize Hermes queries without forbidden legacy/session fields and add the existing opaque source-anchor read client |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | Own request-shape and endpoint/body proof at the serializer boundary |
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` | Clear stale Hermes handles for PR354 responses and preserve bounded turn data without inventing continuity |
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx` | Prove stale-handle clearing and independent subsequent turns |
| Modify | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts` | Persist grounding, graph citations, and whitelisted bounded graph trace; exclude graph citations from path snapshots |
| Modify | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts` | Prove reload round trip, compatibility, bounds, and serialized no-leak guarantees |
| Modify | `apps/live-control-ui/src/planSurface/components/prepMemoryQa.ts` | Map typed Hermes grounding states to accurate answer-first presentation without disturbing legacy Live logic |
| Modify | `apps/live-control-ui/src/planSurface/components/prepMemoryQa.test.ts` | Prove grounded/partial/abstained/error and malformed-contract presentation |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` | Extend the existing pane for graph citations, exact anchor reads, source-bundle-independent asking, reload reconstruction, and graph-specific diagnostics |
| Modify | `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.tsx` | Render bounded typed graph-tool trace inside the existing drawer |
| Modify | `apps/live-control-ui/src/planSurface/components/TraceDetailsPanel.test.tsx` | Prove useful trace rendering, malformed-entry safety, and redaction |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | Prove complete Plan request/presentation/click/reload/error and legacy sibling journeys |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | Style only the added states and existing-pane evidence/trace content |

### Path-count expectation

Expected implementation diff: **18 paths**.

If a required change cannot be completed within this allowlist, stop and report the missing owning boundary. Do not add a “small adjacent” file silently.

---

## §5 Explicitly out of scope — denylist

The following paths and capabilities are inspection-only unless this handoff is formally re-anchored:

### Runtime and graph contracts

- `apps/live_control_server/services/hermes_graph_agent_host.py`
- `apps/live_control_server/services/hermes_graph_agent_contract.py`
- `apps/live_control_server/services/hermes_graph_agent.py`
- `apps/live_control_server/services/live_agent_loop.py`
- `apps/live_control_server/routes/live.py`
- `apps/live_control_server/main.py`
- `apps/live_control_server/routes/world_graph_retrieval.py`
- `apps/live_control_server/services/world_graph_retrieval.py`
- `src/graph_memory/retrieval/**`
- `src/graph_memory/kernel/**`
- `src/graph_memory/hermes_graph_plugin.py`
- `integrations/hermes/**`
- `.hermes.md`

### Legacy product paths

Do not modify or repurpose:

- legacy manifest/corpus/lexical retrieval;
- arbitrary-path citation routes or readers;
- CLI-one-shot runtime;
- Live synthesis behavior;
- existing path-citation semantics;
- provider/model selection;
- source-bundle generation or ingestion semantics.

Legacy behavior may remain for its current named consumers. PR355 only prevents the graph citation branch from using it.

### Deferred product capabilities

Do not implement:

- prior-turn request history;
- pronoun or shorthand continuity;
- thread-to-Hermes session identity;
- reload/process-restart session resume;
- server-side or cross-device thread persistence;
- automatic head refresh or historical-revision browsing;
- backend default changes or selector removal;
- legacy code demolition;
- Play/live-table integration;
- new chat, citation, trace, or dogfood surfaces;
- graph writes, drafts, preview/confirm, or PR011 capabilities;
- agent-generated prep persistence.

### Forbidden shortcuts

- Do not derive citations from `final_response`, `messages`, prompt text, display labels, or arbitrary trace strings.
- Do not parse an anchor ID into a filesystem path.
- Do not call `/api/live/citation-source` for a graph citation.
- Do not rebind a saved citation to current graph head.
- Do not treat `agent_trace.tool_events` as the browser’s grounding classifier.
- Do not persist a source-anchor read body.
- Do not preserve a stale Hermes session by nullish fallback for a PR354 response.
- Do not add compatibility fallback when a graph citation is malformed or unreadable.
- Do not hide a typed abstention/error behind the generic “Ungrounded draft” warning.
- Do not use a mocked diagnostic page as manual dogfood proof.

---

## §6 Contract specification

### §6A — PR354 remains the classification authority

The frontend consumes the server’s `grounding` block. It may validate internal consistency, but it must not promote or downgrade a turn by inspecting raw graph tool events.

Canonical wire shape consumed:

```json
{
  "schema": "dmb_hermes_graph_grounding_v1",
  "state": "grounded | partial | abstained | error",
  "world_id": "eldyrwild",
  "campaign_id": "longmont-c2",
  "focus": { "kind": "session", "session_id": "session-21" },
  "admissibility": "gm",
  "revision_id": "<immutable revision or null for unavailable>",
  "successful_tool_count": 1,
  "source_anchor_count": 1,
  "diagnostic_codes": [],
  "warnings": []
}
```

Add an exact TypeScript type for this schema and an optional `grounding` field to `LiveQueryResponse`.

The frontend may fail closed when a malformed response contradicts itself:

- `grounded` or `partial` with no valid same-scope graph citation is **not** displayed as graph-grounded;
- `abstained` or `error` never displays graph citation cards even if a malformed payload includes them;
- a citation whose scope/revision differs from `grounding` is dropped and produces a visible contract warning;
- these checks do not replace or re-run PR354’s event classifier.

### §6B — Opaque graph citation response variant

Add a discriminated graph citation variant without breaking existing path citations.

```ts
interface LegacyPathCitation {
  kind?: "legacy_path";
  evidence_id: string;
  path: string;
  line_start: number | null;
  line_end: number | null;
  source_role: string;
  authority: string;
}

interface WorldGraphAnchorCitation {
  schema: "dmb_world_graph_anchor_citation_v1";
  kind: "world_graph_anchor";
  anchor_id: string;
  world_id: string;
  campaign_id: string;
  focus: { kind: "none" | "session"; session_id: string | null };
  admissibility: string;
  revision_id: string;
}

type LiveQueryCitation = LegacyPathCitation | WorldGraphAnchorCitation;
```

Do not add fake legacy fields to the graph variant. In particular, a graph citation has no `path`, line range, source role, authority label, or source body until the anchor is explicitly read.

Backend construction rules:

1. Construct graph citations only when final grounding state is `grounded` or `partial`.
2. Use only source-anchor IDs from the same evidence-bearing events that PR354 accepted for final grounding.
3. Copy world, campaign, focus, admissibility, and revision from the dispatched authoritative scope—not from model output and not from client input after resolution.
4. Preserve first-seen anchor order.
5. Deduplicate by exact `anchor_id` only.
6. `len(citations)` must equal the unique accepted anchor count represented by `grounding.source_anchor_count`.
7. Return `citations=[]` for `abstained`, `error`, graph unavailable, projection failure, scope mismatch, malformed event, or unrecovered tool error.
8. Do not perform a source-anchor read while building the answer response.
9. Do not include source content, file paths, raw tool arguments, messages, or unbounded graph payloads.
10. Do not change PR354 state classification or ordered recovery semantics.

Ordered-event regression cases are mandatory because this file now owns both classification consumption and citation projection:

| Event sequence | PR354 final state | Citation result |
| --- | --- | --- |
| error only | error | `[]` |
| error → empty completion | error | `[]` |
| error → evidence-bearing completion | grounded/partial according to evidence | anchors from accepted later evidence only |
| evidence-bearing completion → error | error | `[]` |
| scope mismatch → valid evidence | error | `[]`; foreign IDs absent from serialization |
| malformed event mixed with valid evidence | error | `[]`; malformed IDs/collections absent |

### §6C — Hermes request serializer

`postLiveQuery` must branch at the serializer boundary.

For `queryBackend === "hermes"`, the JSON body contains:

```json
{
  "campaign_id": "longmont-c2",
  "session": 22,
  "mode": "live",
  "query_backend": "hermes",
  "text": "<question>",
  "agent_thread_id": "<local UI thread ID or null>",
  "trace_requested": true,
  "world_graph_context": {
    "schema": "dmb_agent_world_graph_query_context_request_v1",
    "world_id": "eldyrwild",
    "campaign_id": "longmont-c2",
    "focus": { "kind": "session", "session_id": "session-21" },
    "admissibility": "gm",
    "revision_pin": "<browser projection revision or null>"
  }
}
```

It must **omit**, not merely set to null:

- `manifest_path`
- `hermes_session_id`
- prior turns/messages/history
- capability policy
- graph root/path
- source path

For `queryBackend === "live"`, preserve the existing request body and manifest/session behavior exactly. This is a serializer-boundary guarantee and must be tested in `liveApi.test.ts`, not only through a mocked component callback.

### §6D — Source-anchor read wire contract

Add a client for the existing route only:

```text
POST /api/live/world-graph/retrieval/source-anchor/read
```

Exact request uses the PR010A camelCase wire contract:

```json
{
  "schema": "dmb_world_graph_source_anchor_read_request_v1",
  "worldId": "eldyrwild",
  "campaignId": "longmont-c2",
  "focus": { "kind": "session", "sessionId": "session-21" },
  "admissibility": "gm",
  "revisionPin": "<citation revision>",
  "anchorId": "source-anchor:v1:...",
  "maxChars": 4000
}
```

The request is built only from a validated `WorldGraphAnchorCitation`. The browser may not substitute current projection state, current graph head, current session selection, or a path.

Add exact camelCase response types for `dmb_world_graph_source_anchor_read_v1`, including:

- `outcome`;
- `snapshot` with world/campaign/revision/head/focus/admissibility;
- `anchorId`;
- `evidenceRefId`;
- `sourceArtifactId`;
- `sourceDomain`;
- `locatorKind`;
- `mediaType`;
- `content`;
- `contentSha256`;
- `lineStart` / `lineEnd`;
- `truncated`;
- `diagnostics`.

Before rendering content, validate:

1. `response.anchorId === citation.anchor_id`;
2. response snapshot exists for any content-bearing result;
3. snapshot world/campaign/focus/admissibility/revision exactly match the citation;
4. outcome is canonical;
5. content is a string before rendering.

A contradiction is a client-visible contract error. Render no content and do not call another route.

### §6E — Answer-first presentation matrix

| Server grounding state | Required heading | Answer prose | Citation affordance | Warning/error behavior |
| --- | --- | --- | --- | --- |
| `grounded` | `Graph-grounded answer` | Show | Show validated graph citations | No generic ungrounded warning |
| `partial` | `Qualified graph answer` | Show | Show validated graph citations | Show server qualification/warnings |
| `abstained` | `Graph evidence gap` | Show stable abstention | None | Show bounded diagnostics/coverage signal; no draft warning |
| `error` | `Hermes graph error` | Show stable error | None | Show typed error code/warnings; no draft warning |
| missing/malformed grounding on `mode="hermes_graph_agent"` | `Hermes grounding contract error` | May show answer only as untrusted diagnostic prose | None | Explicit contract warning; never label grounded |
| legacy Live response | Existing `Grounded answer` / `Ungrounded draft` behavior | Preserve | Preserve path citations | Preserve existing behavior |

The answer remains the primary content. Evidence details and trace remain collapsed or secondary. Do not make anchor IDs, revision IDs, or graph metadata the main answer.

### §6F — Graph evidence cards and source reader

Use the existing “Supporting sources” area and source-preview region. Do not create another drawer or page.

Before click, a graph citation card may show only:

- a concise label such as `Graph evidence 1`;
- a shortened or collapsible anchor ID;
- the pinned revision in secondary metadata;
- an `Open evidence` action.

Do not invent a source title, file path, line range, authority, or source-domain label before the read result supplies it.

After a successful read, show:

- bounded content;
- source domain/artifact ID when returned;
- line range when returned;
- revision/head status from the response snapshot;
- truncation or partial warning;
- diagnostics when useful.

Never display or request an arbitrary filesystem path for a graph citation.

Graph citation source states:

| State | Required behavior |
| --- | --- |
| idle | No source body displayed |
| loading | Show bounded loading state |
| `enough` | Show content after exact identity/scope validation |
| `partial` / `truncated` | Show content plus qualification |
| `empty` | Show no-content state |
| `denied` | Show access-denied state; no fallback |
| `unavailable` | Show unavailable state; no fallback |
| HTTP/contract error | Show error; render no stale or contradictory content |

Switching turns or citations clears the ephemeral source-read response. Reload does not persist or automatically re-read source content.

### §6G — Safe typed graph trace

Replace `tool_events?: unknown[]` with a typed optional graph-tool event shape matching PR354’s safe projection:

```ts
interface HermesGraphToolTraceEvent {
  tool_name: string;
  state: "start" | "completion" | "error" | string;
  duration_ms: number | null;
  world_id: string | null;
  campaign_id: string | null;
  focus: { kind: string | null; session_id: string | null } | null;
  admissibility: string | null;
  revision_pin: string | null;
  bounded_ids: Record<string, unknown>;
  retrieval_schema: string | null;
  outcome: string | null;
  matched_node_ids: string[];
  relationship_ids: string[];
  source_anchor_ids: string[];
  diagnostic_codes: string[];
}
```

Rendering rules:

- graph trace remains inside the existing `TraceDetailsPanel`;
- show the Hermes execution/session ID as **observability only**, never as restored continuity;
- show world/campaign/revision/focus/admissibility from the grounding block or exact safe event fields;
- show tool name, state, duration, retrieval outcome, IDs, and diagnostic codes;
- malformed entries are ignored or rendered as one bounded contract warning, never stringified wholesale;
- do not render `bounded_ids` values unless they pass a narrow primitive/list sanitizer; omission is acceptable;
- for `mode="hermes_graph_agent"`, never render `prompt_preview`, raw command text, raw arguments, messages, source bodies, or paths even if a malformed response supplies them;
- preserve existing legacy trace rendering for non-Hermes responses.

Trace is observability, not citation authority. A source-anchor ID visible only in trace does not become clickable evidence unless the backend also issued a matching graph citation.

### §6H — Local persistence and reload

Keep the existing local-storage keys and thread schema forward-compatible. Do not create a second store or server persistence layer.

Add optional persisted turn fields as needed:

```ts
interface AgentInteractionTurn {
  // existing fields
  grounding?: HermesGraphGrounding | null;
  citations?: LiveQueryCitation[];
  trace?: AgentInteractionTrace | null;
}
```

Persistence rules:

1. Persist answer, status, grounding, validated citation metadata, and sanitized trace.
2. Persist no source-anchor read response, source body, content hash, or preview state.
3. Persist no `worldGraphContext` detail beyond the existing safe summary.
4. Persist no prompt preview, Hermes messages, raw tool args, arbitrary event objects, absolute path, or graph root.
5. Persist no Hermes session for PR354 mode.
6. `buildEvidenceSnapshots()` accepts only legacy path citations; graph citations produce no path freshness snapshot.
7. Existing legacy records without `kind`, `grounding`, or `tool_events` remain readable.
8. Unknown/malformed persisted graph events or citations are ignored fail-closed during load/render.
9. Reload reconstructs the same presentation state without invoking `/api/live/query` or source-anchor read.
10. Clicking a persisted graph citation after reload sends the same anchor/scope/revision as before reload.

Sanitize and bound persisted graph trace independently of server typing. Minimum caps:

```text
maximum persisted graph tool events: 24
maximum IDs per event field: 32
maximum diagnostic codes per event: 32
maximum warnings: 16
maximum string length for any persisted graph trace scalar: 512 characters
```

Smaller defensible caps are acceptable. Larger or unbounded persistence is not.

The persisted event whitelist is:

- `tool_name`
- `state`
- `duration_ms`
- `world_id`
- `campaign_id`
- `focus`
- `admissibility`
- `revision_pin`
- `retrieval_schema`
- `outcome`
- `matched_node_ids`
- `relationship_ids`
- `source_anchor_ids`
- `diagnostic_codes`

`bounded_ids` need not be persisted.

### §6I — Hermes session and thread boundary

PR355 does not create continuity.

- `agent_thread_id` remains a browser-owned thread/turn organizer.
- `agent_trace.hermes_session_id` remains observability-only.
- `response.hermes_session` remains `null`.
- consuming a `mode="hermes_graph_agent"` response clears any stale `thread.hermesSession` value rather than retaining it through `??` fallback;
- every later Hermes request omits `hermes_session_id` regardless of stale local data;
- no prior turns/messages are sent;
- reload restores completed turn display only.

Tests must explicitly prove that two visible turns in one local thread are still two independent PR354 turns.

### §6J — Legacy source-bundle and Live compatibility

The legacy source bundle may continue loading for diagnostics, but it cannot gate the graph interaction.

Required component structure:

- thread controls, question form, answers, graph citations, and trace render independently of `bundle` success;
- bundle loading/error affects only the legacy memory-coverage diagnostics section;
- no change to source-bundle API semantics;
- existing Live backend path citations and source/freshness readers remain functional;
- graph citations never enter the path freshness pipeline.

### §6K — Authority synchronization

Update tracker and roadmap to this explicit sequence:

```text
DONE    PR010B Rung 1 — strict graph-only read-tool dispatcher (#350)
DONE    PR010B Rung 2 — model-visible catalog and adapter (#351)
DONE    PR010B Rung 3 — embedded Hermes graph-agent turn (#352)
DONE    PR010B Rung 4A — persistent process-isolated host (#353)
DONE    PR010B Rung 4B — single-turn backend product cutover (#354)
DOING   PR010B Rung 4C / PR355 — Plan graph evidence presentation and reload-safe turn persistence
NEXT    PR010B Rung 5 — same-thread object continuity
LATER   PR010B Rung 6 — Hermes session-pointer continuity
LATER   PR010B Rung 7 — product acceptance, demolition, and backend-toggle removal
```

Documentation must define “reload-safe turn persistence” narrowly: saved answer/citation/trace display only. It must not describe or imply Hermes session resume.

### §6L — Demolition statement

```text
Retained temporarily:
- legacy manifest/corpus/lexical Hermes code;
- path-based citation reader for existing Live/path citations;
- CLI-one-shot development/product remnants;
- Live synthesis path;
- Live/Hermes backend selector.

Reason:
PR355 presents and preserves the accepted graph result but does not yet prove same-thread continuity or steady-state replacement acceptance.

Remaining consumers:
- explicitly selected Live backend;
- legacy path-citation turns and stored history;
- existing tests/developer paths.

Required deletion PR:
PR010B Rung 7, after Rung 5/6 acceptance and dogfood.
```

---

## §7 Verification plan

The worker must run every automated command below from the recorded implementation base and again at head where a baseline comparison is requested. Report exact counts and provenance. Do not rely on PR-description claims.

### V1 — Backend citation projection and PR354 state-machine regression

```bash
uv run pytest tests/test_live_query_hermes_graph.py -q
```

Must own:

- exact graph citation shape;
- first-seen ordering and deduplication;
- authoritative scope/revision copying;
- grounded and partial citations;
- no citations for abstained/error/unavailable;
- error→evidence recovery;
- evidence→error failure;
- scope mismatch and malformed-event no-leak behavior;
- no model-prose citation extraction;
- no source-anchor read during answer construction.

### V2 — Backend sibling and source-anchor-route regression

```bash
uv run pytest tests/test_hermes_graph_agent.py tests/test_hermes_graph_agent_host.py tests/test_agent_world_graph_query_context.py tests/test_live_control_server.py tests/test_world_graph_retrieval_routes.py -q
```

Must prove PR355 did not change host, Rung 3, graph context, route behavior, or PR010A source-anchor semantics.

### V3 — Python static verification

```bash
uv run ruff check apps/live_control_server/services/hermes_graph_query.py tests/test_live_query_hermes_graph.py
```

### V4 — Frontend serializer, provider, presentation-helper, and persistence ownership

```bash
cd apps/live-control-ui && npm test -- src/api/liveApi.test.ts src/agentInteraction/AgentInteractionProvider.test.tsx src/planSurface/components/agentInteractionHistory.test.ts src/planSurface/components/prepMemoryQa.test.ts
```

Must own:

- exact Hermes request omissions;
- unchanged Live request shape;
- exact source-anchor route and camelCase body;
- stale session clearing;
- independent subsequent turns;
- grounding-state presentation;
- persistence caps, round trip, compatibility, and no-leak serialization;
- no path snapshots for graph citations.

### V5 — Existing Plan consumer, trace, click, reload, and sibling UI paths

```bash
cd apps/live-control-ui && npm test -- src/planSurface/components/TraceDetailsPanel.test.tsx src/planSurface/PlanSurfaceShell.test.tsx
```

Must own:

- source-bundle failure does not block Hermes interaction;
- grounded/partial/abstained/error rendering;
- graph citation click uses the opaque route and exact pinned request;
- no legacy path route for graph citations;
- contradictory anchor-read response renders no content;
- bounded graph trace and malformed-entry safety;
- reload renders saved grounding/citations/trace without network execution;
- saved citation click after reload uses original revision;
- legacy Live/path citation behavior remains unchanged.

### V6 — Complete frontend regression and build

```bash
cd apps/live-control-ui && npm test && npm run build
```

### V7 — Diff hygiene

```bash
git diff --check
```

Also report:

```bash
git diff --name-only <implementation-base>...HEAD
git diff --stat <implementation-base>...HEAD
```

These two reporting commands are not substitutes for the §4 allowlist check.

### Automated serialized no-leak assertions

At both backend-response and local-storage boundaries, serialize the complete object and assert distinctive forbidden strings are absent. At minimum inject and search for:

```text
/foreign/absolute/path.md
FOREIGN_WORLD_ID
FOREIGN_CAMPAIGN_ID
FOREIGN_REVISION_ID
FOREIGN_SOURCE_ANCHOR_ID
RAW_PROMPT_SECRET
RAW_TOOL_ARGUMENT_SECRET
RAW_SOURCE_BODY_SECRET
RAW_HERMES_MESSAGE_SECRET
```

Assertions on only `grounding.state` or only visible DOM text are insufficient.

### Manual live dogfood — acceptance gate

Use the existing Plan surface and real provider/runtime. Do not build a diagnostic page.

#### Positive journey

1. Start the current live-control server and UI using repository-supported dogfood commands.
2. Open the existing Plan surface for the published Eldyrwild Campaign 2 graph.
3. Open **Ask prep memory**.
4. Select **Hermes tools**.
5. Ask exactly:

   ```text
   What do we know about Tripod Null-Calf at the North Gate?
   ```

6. Verify:
   - request body contains no `manifest_path` or `hermes_session_id`;
   - response mode is `hermes_graph_agent`;
   - answer is labeled graph-grounded or qualified according to the returned state;
   - at least one opaque graph citation is present;
   - citation scope/revision matches grounding;
   - opening evidence calls only the existing source-anchor read route;
   - returned content is bounded and identity-validated;
   - Trace On shows real graph tool activity, revision, object/edge/anchor IDs, and outcomes;
   - no prompt, raw args, source body, arbitrary path, or Hermes messages appear in trace/local storage.
7. Reload the page.
8. Verify the saved turn, grounding label, citation metadata, and safe trace still render without automatically re-running Hermes or reading the source.
9. Open the saved citation and verify the request uses the original pinned revision.
10. Submit a new simple Hermes question and verify no session ID or prior turns are sent. Do not claim pronoun continuity.

#### Coverage-gap journey

Ask a factual question known to exist in repository Markdown but absent from the admitted World Graph/anchors.

Verify:

- the UI shows **Graph evidence gap** or the typed error state returned;
- no graph citation card appears;
- no path citation appears;
- no `/api/live/citation-source`, manifest, corpus, lexical, CLI, or Live-synthesis fallback runs;
- the stable abstention/error remains after reload.

#### Dogfood provenance

The PR handback must state one of:

```text
Manual dogfood: PASS — run by <actor>, <environment>, <date/time>, evidence summarized in PR body.
```

or

```text
Manual dogfood: BLOCKED — real provider/runtime credentials unavailable to implementation agent. Automated proof complete; operator/reviewer must run the acceptance gate before merge.
```

A blocked worker may open the PR, but the PR may not be accepted as complete until the operator/reviewer records the real run. Mocked tests do not satisfy this gate.

### Baseline comparison

Run V1, V2, V4, V5, and V6 on the implementation base and head when practical. If an implementation-base command cannot include a newly added test case, run the pre-existing owning suite on base and clearly separate the new head-only test file/count.

Report:

| Revision | Backend owning suites | Frontend owning suites | Frontend full suite/build | Provenance |
| --- | --- | --- | --- | --- |
| Implementation base | exact result | exact result | exact result | local/CI |
| Head | exact result | exact result | exact result | local/CI |

Never convert a pre-existing failure into a waiver silently.

---

## §8 Required handback

The implementation agent’s PR body must include all of the following:

1. PR354 predecessor merge SHA: `827e34adc93705c1b44a97ab3d3c00afdaf7340e`.
2. Docs-only implementation-base SHA.
3. Final head SHA.
4. Actual changed paths and diff stat.
5. Exact response citation schema implemented.
6. Exact Hermes request body keys after serialization.
7. Exact source-anchor read endpoint and request body shape.
8. Grounding-to-presentation mapping.
9. Persistence caps and whitelist.
10. Statement that source read content is not persisted.
11. Statement that graph citations never use the path reader or path freshness pipeline.
12. Statement that stale Hermes handles are cleared and no session/prior turns are sent.
13. Ordered-event citation regression results.
14. Complete serialized no-leak results.
15. Every V1–V7 command with exact result and provenance.
16. Base/head comparison.
17. Manual positive dogfood result and evidence.
18. Manual graph-gap dogfood result and evidence.
19. CI/workflow status checks attached to final head; write `none exposed` if none exist.
20. Baseline failures and waivers; write `none` when none exist.
21. Paths outside §4; write `none` or include a stop report.
22. Stop conditions encountered and resolution; write `none` when none exist.
23. Deviations from §6; write `none` when none exist.
24. Confirmation that PR010B Rung 5 has not begun.
25. Confirmation that Hermes session-pointer continuity remains false.
26. Confirmation that the backend selector and legacy code remain for Rung 7.
27. Confirmation that no server-side persistence or write tool was added.
28. Confirmation that the authoritative handoff was implemented without compression, omission, or silent reinterpretation.

Opening the pull request must be the final repository action on the implementation branch.

---

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true.

- [ ] Exactly one capability is delivered: the existing Plan pane faithfully presents and locally preserves one PR354 Hermes graph turn — proved by V1, V4, V5, and manual dogfood.
- [ ] PR354 remains the sole grounding classifier; the browser does not infer grounding from trace events — proved by V4/V5 and code review.
- [ ] Backend graph citations are derived only from accepted evidence-bearing events at the authoritative dispatched scope/revision — proved by V1.
- [ ] Citation ordering, deduplication, and count match the accepted source-anchor set — proved by V1.
- [ ] Error→evidence recovery can produce later accepted citations, while evidence→error, mismatch, and malformed sequences produce no citations — proved by V1.
- [ ] Model prose, messages, prompts, trace strings, and display labels cannot create citations — proved by V1 and serialized no-leak assertions.
- [ ] Hermes request serialization omits `manifest_path`, `hermes_session_id`, and prior turns while Live serialization remains unchanged — proved at the owning serializer boundary by V4.
- [ ] Graph citations use the exact opaque source-anchor route and camelCase request contract — proved by V4 and V5.
- [ ] Graph citation reads are identity-, scope-, and revision-validated before content renders — proved by V4/V5.
- [ ] Empty, denied, unavailable, HTTP-error, and contradictory anchor reads fail closed without path or head fallback — proved by V5.
- [ ] Grounded, partial, abstained, error, and malformed-contract states receive accurate answer-first presentation and no misleading generic draft label — proved by V4/V5.
- [ ] Graph trace is useful and bounded while prompts, source bodies, paths, raw arguments, messages, and arbitrary objects remain absent — proved by V5 and no-leak assertions.
- [ ] Local persistence round-trips grounding, graph citations, and sanitized trace with explicit caps — proved by V4.
- [ ] Source-anchor content and path-oriented evidence snapshots are not persisted for graph citations — proved by V4 and serialized no-leak assertions.
- [ ] Reload restores completed-turn presentation without re-running Hermes or source reads; saved citation clicks retain the original revision — proved by V5.
- [ ] A PR354 response clears stale Hermes session handles, and later requests remain independent — proved by V4/V5.
- [ ] Legacy source-bundle failure does not block the graph interaction — proved by V5.
- [ ] Existing Live/path citation and freshness behavior remains functional — proved by V4/V5/V6.
- [ ] Host, Rung 3, graph-context, and source-anchor route contracts remain unchanged — proved by V2 and diff review.
- [ ] Real positive and coverage-gap dogfood journeys pass in the existing Plan surface — proved by the manual acceptance gate.
- [ ] Tracker and roadmap mark #354 done, PR355 active, and Rung 5–7 separate — proved by documentation inspection.
- [ ] No unexpected path changed — proved by §4 allowlist comparison and V7 reporting.
- [ ] Baseline failures and verification provenance are reported truthfully.
- [ ] No new route, graph operation, server thread store, UI surface, session continuity, demolition, default-backend change, or write tool was added — proved by diff review.
- [ ] The complete authoritative handoff survived dispatch without omitted constraints.

---

## §10 Reviewer protocol

Review the complete product envelope and unchanged consumers, not only the new helpers.

1. Fetch current PR head and compare it with the implementation base before reading claims.
2. Confirm PR354 merge `827e34a…` is the actual predecessor.
3. Compare changed paths with §4; reject silent adjacent scope.
4. Trace the Hermes request from Plan form through `postLiveQuery`; inspect the serialized body, not only mock arguments.
5. Trace one grounded response from backend classification through citation projection, TypeScript decoding, answer presentation, persistence, reload reconstruction, and source-anchor click.
6. Verify all three event-validity questions remain separate:
   - does an event contradict dispatched scope?
   - does it completely prove grounding?
   - can it be safely serialized/persisted?
7. Follow every defensive branch through classification, citation aggregation, response serialization, browser parsing, DOM rendering, and local-storage serialization.
8. Re-test ordered event sequences: error only, error→empty, error→evidence, evidence→error, mismatch→valid, malformed mixed with valid.
9. Serialize complete error/mismatch/malformed responses and persisted turns; search for distinctive foreign or unsafe identifiers.
10. Verify graph citations are backend-issued product fields, not reconstructed from trace.
11. Verify exact citation scope/revision is used on click and survives reload.
12. Verify contradictory anchor-read responses render no content.
13. Verify source-bundle failure no longer hides the graph interaction.
14. Verify legacy Live/path behavior remains intact.
15. Verify `hermes_session_id`, prior turns, and `manifest_path` are absent from Hermes requests even when stale local state exists.
16. Verify no raw prompt, source body, path, raw args, Hermes messages, or arbitrary event properties reach DOM or local storage.
17. Re-run V1–V7 independently using `scripts/review_external_pr.py verify 355 --handoff Docs/Plans/HANDOFF-pr355-plan-hermes-graph-evidence-presentation.md --parse-counts` once the PR exists.
18. Check current mergeability, workflow runs, and combined status checks on the final head.
19. Compare PR body changed paths/test counts with the actual final PR.
20. Confirm the manual real-runtime positive and graph-gap evidence exists before approval.
21. Confirm Rung 5/6/7 and PR011 remain false.

A backend-only interpretation is invalid: this PR’s contract is the completed response as consumed, rendered, clicked, serialized, and reloaded by the unchanged surrounding Plan product.

---

## §11 Re-review protocol

Begin every re-review from a finding ledger.

| Prior finding | Claimed fix | Owning files/tests | Verified? | New consequence? |
| --- | --- | --- | ---: | --- |
| `<finding>` | `<claimed resolution>` | `<paths/tests>` | Yes / No | `<none or consequence>` |

For each re-review:

1. Fetch the current head; never assume it matches the last reviewed SHA.
2. Compare only the new commits to the last reviewed head first.
3. Verify each claimed fix at its owning boundary.
4. Re-run the complete request → response → presentation → persistence → reload → citation-read path.
5. Re-run the ordered event matrix and source-read negative matrix.
6. Re-run full serialized no-leak checks.
7. Confirm prior fixes remain intact.
8. Check current mergeability, status checks, workflow runs, changed paths, and PR-description accuracy.
9. Add new findings to the ledger.
10. Do not approve or merge merely because focused tests pass; the real dogfood gate and sibling Live path still matter.

---

## Stop conditions

Stop and report instead of widening scope if implementation discovers:

- PR354’s final response no longer exposes enough exact scope/revision/source-anchor information to construct the citation variant;
- citation construction requires reading source anchors server-side or changing Rung 3/host contracts;
- the existing PR010A source-anchor route cannot read an emitted PR354 anchor at the pinned revision;
- a graph citation can only be made usable by inventing a path or using the legacy path reader;
- the browser must reclassify tool events to decide grounding;
- safe reload requires persisting source content, raw tool results, prompts, messages, or session state;
- same-thread history or a Hermes session is required for the first-turn positive journey;
- server-side thread storage is required;
- the existing Agent Interaction pane cannot support the interaction without a new independently useful surface;
- a required change falls outside §4;
- a head-only failure appears in an owning suite;
- the real source-anchor response contradicts the documented camelCase contract;
- the positive dogfood question cannot be answered from the current published graph/anchors;
- the graph-gap journey reaches any legacy fallback;
- a write-capable tool or PR011 contract becomes necessary;
- any handoff constraint cannot be implemented without reinterpretation.

Use this report:

```text
Stop condition:
Why the current mission cannot absorb it:
New public/durable contract discovered:
Affected observable paths:
Affected ownership layers:
Required path outside scope:
Proposed successor slice:
Tracker or authority update needed:
Operator decision required:
```

The worker must not resolve a stop condition by silently broadening the mission.

---

## Final dispatch checklist

Before dispatching the implementation agent:

- [ ] This handoff is committed on `main`.
- [ ] The implementation-base SHA is recorded above.
- [ ] The base descends from PR354 merge `827e34adc93705c1b44a97ab3d3c00afdaf7340e`.
- [ ] No production path changed in the handoff commit.
- [ ] §4 contains every expected changed path.
- [ ] V1–V7 are executable from the recorded base.
- [ ] The operator understands that manual real-runtime dogfood is a merge gate.
- [ ] PR010B Rung 5 remains a separate handoff.

```text
DISPATCH PR355.
STOP AFTER OPENING THE PR.
DO NOT BEGIN PR010B RUNG 5.