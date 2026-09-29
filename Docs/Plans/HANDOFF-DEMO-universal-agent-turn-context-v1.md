---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J2 — universal Agent turn context
  - Flow: DEMO
  - Direction: STEWARD → PRIME + ARCHITECTURE → CODE → PRIME
  - Handoff: `Docs/Plans/HANDOFF-DEMO-universal-agent-turn-context-v1.md`
  - PR topology: serial within DEMO Agent; this PR is design/authority only

  ## Review contract
  One Buddy-owned turn contract resolves the current surface, owner scope,
  primary work object, graph lens, and temporal graph focus independently.
  Exact World/campaign authority and focus are server-resolved; absent context
  is explicit; supplied invalid/foreign identity fails closed. Generic no-scope
  turns do not load a session packet. `/api/live/query` remains packet-bound.
  The six-surface matrix and owning-boundary acceptance evidence govern.

# HANDOFF — DEMO: one truthful Agent turn across Buddy surfaces

**Created:** 2026-09-29
**Status:** DESIGN REVIEW — implementation BLOCKED on PRIME/ARCHITECTURE acceptance and route-registration collision recheck
**Conversation/workstream:** LOCAL DEMO ACCEPTED / DEMO J2
**Flow / owner:** DEMO / Buddy Agent interaction
**Direction:** STEWARD → PRIME + ARCHITECTURE → CODE → PRIME
**Design authority base:** Buddy `main@ed1bf1ba0531bf9018f2397863825fa20c781bfe` (PR #789 merge)
**PR topology:** serial within DEMO Agent; this is a design-review PR, no implementation lease is active
**Implementation PR authorization:** none until this design is accepted, the route-registration collision is cleared, and the handoff is re-anchored on current main. Then open exactly one implementation PR; no UI adoption PR is authorized by this handoff.
**PRIME merge coordination:** PRIME owns ecosystem merge coordination; this handoff does not request merge.

Repository operating law is [`AGENTS.md`](../../AGENTS.md). DEMO product state is
owned by [`ROADMAP-demo.md`](../Roadmaps/ROADMAP-demo.md). The completed J2
canvas-composition slice is recorded in
[`HANDOFF-DEMO-J2-world-plan-canvas-composition-v1.md`](HANDOFF-DEMO-J2-world-plan-canvas-composition-v1.md).

## §1 Mission and decision-ready invariant

Establish one reusable Buddy-owned Agent turn boundary that can truthfully
answer from the context available on any navigable DEMO surface without making
surface identity, graph scope, or work-object identity impersonate one another.

**Decision-ready invariant:** every accepted Agent turn is bound to:

1. the exact current surface and its current owner snapshot;
2. either no graph scope, one verified World scope, or one verified campaign
   scope;
3. an optional exact primary work object and its own revision; and
4. an optional exact selected graph object and graph revision.

Those are distinct authorities. A missing document does not erase an available
World; a selected World does not manufacture a Plan, campaign, or session; a
Plan document revision is not a graph revision; and an absent graph scope is
not reported as graph retrieval. Client locators are requests for resolution,
not authority or trusted prose.

The same resolved owner scope and primary work object may retain a conversation
across surface changes. The current surface snapshot is re-resolved on every
turn. Changing the owner scope or primary work object cannot silently reuse a
thread/pointer bound to the old identity.

## §2 Current authority and observed gaps

Exact accepted base: PR #789 merged at
`ed1bf1ba0531bf9018f2397863825fa20c781bfe`; PRIME Cycle 1 accepted exact code
head `7e4fb73d5a553b58bd1350c9c0ded653ef97b2e0` for canvas composition. Its
review explicitly leaves universal Agent on Index, Plan, Play, Build, Ingest,
and Combat as successor work. #789 is a composition PASS, not an Agent or full
J2 acceptance.

Current implementation evidence:

- `POST /api/live/query` requires the loaded packet's `campaign_id` and integer
  `session`, and verifies both against a loaded packet (or a compatibility
  packet for a managed World Plan). It is not a generic turn endpoint. Keep
  this route and its packet binding unchanged as a legacy adapter.
- `AgentSurfaceContextRequest` v1 is identity-only and packet-shaped
  (`surface_id`, `campaign_id`, `document_id`, integer `session_number`,
  pointers). Its resolver/rendering supports Plan and Play; other surfaces are
  rejected/omitted. Do not silently broaden or reinterpret this v1 wire shape.
- `AgentWorldGraphQueryContextRequest` is the graph retrieval lens. It carries
  World, campaign/world mode, optional graph revision pin and selected node.
  World scope is not the work-object context and must remain independently
  reported.
- `AgentContextPacket` currently requires `AgentWorldScope`; that makes the
  no-World/no-campaign ordinary conversation case unrepresentable at this
  boundary. Any optional-scope change must preserve strict retrieval behavior
  when a graph scope is requested.
- Hermes pointer storage keys bindings by `(campaign_id, agent_thread_id)` and
  stores Hermes session IDs as provider continuation. That provider ID is not
  a product scope or user-visible conversation identity. World-only and
  unscoped turns need an explicit structured owner binding without breaking
  legacy campaign pointer reads.
- UI has one app-level `AgentInteractionProvider` and lease-guarded surface
  publication, but current publisher/Ask coverage is uneven. The global chrome
  is not proof that every surface has a useful Ask owner or a truthful
  server-resolved context.

The latest human Plan witness is an explicit product-quality rejection, not
merely a caveat: the user said the canvas “looks awful,” has “no boundary,” and
has “a bunch of default styling.” The exact live witness was
`http://127.0.0.1:5201/plan?world=pr788-exact-head-witness-b-2026-09-28`.
Rendered-source inspection found a 3px slate border on
`.world-owned-plan__canvas` and a 2px parchment border on the nested
`.tiptap-spike-editor`; the user still does not perceive a meaningful canvas
boundary. The editor retains `tiptap-spike-editor md-content` and shared
default Markdown/theme composition. Thus this is not an absent CSS border: the
current dark tray + large blank parchment sheet reads as generic/default rather
than a deliberate writing surface. Do not use selector presence, screenshot
diffs, CSS border width, or the 115 passing composition tests as a substitute
for product-owner visual acceptance. This feedback is not waived by #789's
review or merge and is not bundled into the universal Agent backend contract.
It remains an explicit, unresolved presentation acceptance debt in the
roadmap; any successor styling work needs its own bounded design/implementation
authority.

## §3 Six-surface owner and lens matrix

This matrix distinguishes what the surface owns today from what the shared
Agent contract must resolve. It is not permission to invent a client publisher
for a missing owner.

| Surface | Existing owner evidence | Required server-resolved work snapshot | Graph lens and honest absence |
|---|---|---|---|
| Index | `IndexSurfacePublisher` publishes Command Board with null campaign/document/session; selected managed World is independently available from selected-World authority. | No primary work object. Current route/surface instance only. | If an exact managed World is selected, a World lens may be requested. Otherwise ordinary conversation with `graph.status=not_requested`; never synthesize a campaign from `surface_id`. |
| Plan | Campaign Plan uses the exact workspace document and target session; World-owned Plan has exact managed `world_id`, exact Plan `document_id`, and null product campaign/session. | Resolve the active saved Plan record/revision from its owning registry. Unsaved local draft is `unavailable_or_unsaved`, not a made-up durable document ID. | Use exact selected World or campaign owner and current graph head/revision. World Plan reads use `scope_mode=world`, null campaign, no packet session. |
| Play | `PlaySurfacePublisher` derives campaign/playable identity from the admitted durable Run; current beat/scene context has a dedicated server resolver. | Resolve exact admitted Run, playable artifact/revision, and current Beat-first moment from Run authority. | The Run's actual owning World/campaign only. Missing/invalid Run is distinct from a valid Run with no current moment. |
| Build | `BuildSurfaceContext` observes the active workspace-document session/record, including exact document, campaign and class when admitted. | Resolve exact active Build document and saved revision from workspace-document authority; never trust posted Markdown as server context. | Use the document's verified owner scope. No active document may still allow ordinary chat if scope is otherwise absent. |
| Ingest | `MemoryIngestPage` derives campaign/session from its PlanView context and publishes surface context; exact extraction/source IDs are currently route inputs, not an admitted generic conversation owner. | Resolve the exact selected recap/source/run through the owning ingestion/APP-STATE authority before treating it as current work. | Use the verified campaign/World only. Missing recap context does not imply no campaign; failed scope lookup is unavailable, not absent. |
| Combat | The route exists in product navigation; no equivalent generic Agent owner publication/resolver is established in this baseline. | First identify the exact live encounter/session owner and current encounter revision; until then return an explicit unsupported/unavailable owner context, not guessed combat state. | Do not infer Campaign/World from the route name. A selected World lens can remain independent if verified. |

The implementation contract must expose unsupported/unimplemented owner
resolution as an explicit status per surface. It must not claim six-surface
product availability until each surface has an owning-boundary integration
witness. This backend slice establishes the common turn authority; it does not
add six UI Ask panels or make the current surface owners magically equivalent.

## §4 Proposed bounded wire and result contract

The accepted design may refine field names, but it must preserve these
semantics. The additive endpoint is `POST /api/live/agent/turn`, composed as a
child route under the already-registered `/api/live` router. This avoids a new
`main.py` registration while #763/#765 are open and leaves
`/api/live/query` unchanged as the campaign/session packet-bound legacy route.

```json
{
  "schema": "dmb_agent_turn_request_v1",
  "client_thread_id": "agent-thread-opaque",
  "turn_id": "client-turn-opaque",
  "surface": {"surface_id": "plan", "instance_id": "lease-identity"},
  "owner_scope": {"kind": "world", "world_id": "world-locator"},
  "primary_work": {"kind": "plan", "object_id": "document-locator", "expected_revision": 3},
  "client_work_state": "saved_dirty",
  "graph_request": {
    "mode": "world",
    "world_id": "world-locator",
    "revision_pin": null,
    "focus": {"kind": "session", "session_id": "session-23", "campaign_id": "longmont-c2"}
  },
  "graph_selection": {"node_id": "node:hempholm"},
  "message": "What have we established about this place?"
}
```

`owner_scope` is explicitly one of `null`, `{kind:"world", world_id}`, or
`{kind:"campaign", campaign_id}`. These values are untrusted locators; the
server resolves the selected World or campaign through its existing owner
authority. `graph_request` is a required discriminated choice: `{mode:"none"}`
means no graph retrieval is requested and carries no selected node, while
`{mode:"world",world_id,revision_pin,focus}` or
`{mode:"campaign",campaign_id,revision_pin,focus}` explicitly requests one
graph lens. `focus` is a required client locator for requested graph lenses
and is either
`{kind:"none",session_id:null,campaign_id:null}` or
`{kind:"session",session_id,campaign_id}` with an exact nonblank session ID
and exact focus campaign ID when one applies (otherwise null). It is a temporal
retrieval focus, not an alternate graph scope or authorization. The server
must corroborate it against the resolved surface/work snapshot and reject any
disagreement. The current surface/work resolver supplies the accepted value;
it is never guessed from a URL, session number, World ID, or campaign
surrogate. A managed World Plan with no target
session uses `kind:"none"`. A campaign Plan preserves its exact resolved
session and focus campaign. A World lens on a session-focused surface preserves
that same session focus and exact campaign when applicable. A null revision pin
means resolve the current readable revision; a non-null pin requests that exact
revision. The server resolves a campaign to its owning World. A graph lens may
equal or narrow the verified
owner scope, never widen it: World owner + same World lens is valid; World owner
+ a campaign lens is valid only when that campaign resolves inside the same
World; campaign owner permits only that same campaign lens; a campaign owner
cannot request the broader World lens. With no work owner, a graph lens is
allowed only when the current surface resolver independently proves the exact
selected World/campaign; otherwise reject it. World selection with
`graph_request.mode="none"` remains ordinary no-retrieval conversation. A
non-null `graph_selection` or session focus paired with `mode:"none"` is
contradictory and fails validation; the server must not ignore it or silently
upgrade the request to retrieval.

`primary_work` is null only when no durable work object is selected, or a
bounded `{kind, object_id, expected_revision}` locator for a saved object.
`client_work_state` is a separate presentation hint with values
`none|saved_clean|saved_dirty|new_unsaved`; it is not a resolved status or
authority. Thus null work + `none` means no selected work, while null work +
`new_unsaved` means the client reports a local unsaved draft. The response
echoes that distinction as `client_work_state_reported` (never `resolved`) and
never claims to have read draft content. `saved_dirty` is only a browser hint:
the server resolves the exact saved object locator against its current
committed authority, uses the actual latest committed revision, and reports
`changed_since_expected` with expected-versus-used revision values when that
revision differs from `expected_revision`. No local editor prose or unsubmitted
diff is sent or treated as context.
Contradictory selection/hint pairs fail validation rather than being guessed.

The request carries bounded identity and the typed UI-state hint only; no
client `ambientSummary`, quoted work prose, source excerpts, workspace paths,
fake session numbers, or caller-asserted resolved statuses.

Every non-null submitted identity is re-resolved at the server-owned boundary
on every turn. A malformed, foreign, or removed identity is rejected with a
typed 4xx and no downgrade to null. A genuinely absent optional identity is
allowed and reported absent. `expected_revision` is a freshness expectation,
not a historical content pin: if the same authorized work object still exists
at a newer committed revision, the read-only turn may proceed against that
current revision and must return `changed_since_expected`, the exact revision
actually used, and the matching owner snapshot. It must never label that
answer as using the older revision. Exact graph `revision_pin` is different: if
that revision cannot be read, reject the requested graph turn and do not call
the answer model; if it is readable but non-head, report its actual revision
and `is_head=false`.

Within a valid authorized lens, an exact selected node that is not returned by
the graph query is `selection_found=false` (a valid not-found/empty result),
not a foreign-identity error; the server must not reveal whether that node
exists in another scope. A valid empty graph or `selection_found=false` may
still call the answer model with an explicit empty retrieval result for an
ordinary answer, but the response must say no graph evidence was found and
must not claim graph grounding or fabricate citations. Invalid/foreign scope,
unavailable graph service, or an unreadable requested revision remains
fail-closed and makes no answer-model call.

The result separates:

```text
surface: current surface_id + resolution status + owner snapshot generation
scope: absent | resolved | rejected | unavailable; kind + canonical owner ID
primary_work: absent | resolved | changed_since_expected | foreign | removed | unavailable
client_work_state_reported: none | saved_clean | saved_dirty | new_unsaved
graph: not_requested | ready | empty | unavailable | rejected; requested lens,
       canonical World/campaign, requested pin, requested/resolved temporal
       focus, actual revision, observed head, is_head,
       selection_found: null | false | true, optional exact selected node
conversation: client thread ID + turn ID + provider-continuity outcome
answer: text/status/warnings; no implied graph grounding when graph not used
```

Statuses must not collapse: no scope is different from an invalid foreign
scope; absent work is different from a client-reported unsaved draft; empty
graph is different from graph-service outage; a non-head graph revision is
different from the current head. A requested graph that cannot be
authoritatively resolved follows the existing fail-closed retrieval policy and
does not call the answer model. A turn with `graph_request.mode="none"` may use
ordinary conversation without graph tools and must not claim retrieval or
citations. Surface owner/scope, primary work, and graph request remain separate
fields; selection of a graph node does not itself request a graph read.

`selection_found` is `null` when no graph selection was requested, `true` only
when the exact requested node is present in the authorized result, and `false`
when a valid authorized query does not return it. It never reveals
cross-scope existence.

The response carries the exact graph revision/head state and the independent
primary-work revision used for that turn. It also echoes `client_work_state`
as `client_work_state_reported`; it does not convert that browser hint into a
server-verified status. Graph and document revisions must never be compared as
if they share an identity space. A UI request-generation token may suppress
stale late responses; it is not server authorization.

## §5 Conversation binding and compatibility

- Buddy product conversation history is currently client-owned, not a
  server-authoritative thread store. `AgentInteractionProvider` holds it and
  `agentInteractionHistory.ts` persists `AgentInteractionThread` turns and
  indexes in browser `localStorage`: thread records use
  `agent-interaction-thread-v2:<campaign>:<threadId>`, active-thread keys use
  `agent-interaction-active-thread-v2:<campaign>:<surface>:<document?>`, and
  indexes use `agent-interaction-thread-index-v2:<campaign>:<surface>:<document?>`.
  These browser records survive reload on that browser profile, but are not a
  cross-device or server-authenticated history authority.
- A client `client_thread_id` is therefore an opaque UI/history locator, not a
  credential and not a canonical server-owned product thread. The UI must use
  a separate local history when owner scope or primary work object changes;
  same verified scope/work may preserve a client conversation across surface
  changes. The server never accepts client `conversation_history` as authority
  on this new endpoint.
- `HermesSessionPointerStore` in
  `apps/live_control_server/services/hermes_session_store.py` persists only
  provider continuation bindings to `hermes_thread_pointers.json` under the
  configured `session_dir()` base from `apps/live_control_server/config.py`.
  For the generic no-scope route this directory is only the pointer-storage
  location: do not call `load_session()` or read a packet/session as a
  prerequisite. It is not Buddy message history. The generic route reuses this
  same file/store but adds a versioned structured binding
  namespace over canonical owner scope, primary work identity (or none), and
  client thread ID. Reuse is allowed only for an exact structured-key and
  stored-identity match; a changed scope/work key starts fresh provider
  continuity and cannot fetch another key's Hermes session.
- Legacy behavior is deliberately not migrated implicitly. Existing
  `/api/live/query` keeps its current `(campaign_id, agent_thread_id)` lookup,
  validation, recovery, and update behavior unchanged. The new generic route
  never reads, rewrites, deletes, or auto-adopts a legacy campaign-only pointer,
  because it cannot prove that pointer's primary-work binding. It starts a
  fresh structured provider continuation instead. Existing legacy UI threads
  remain available through the old route; an adopter must create a clean new
  client thread at cutover rather than display old history as if Hermes had
  continued it.
- The server resolves surface/owner/work/graph context anew on every request
  and returns a per-turn `resolved_context` snapshot in that response. Buddy
  currently has no durable server-side transcript/snapshot store: the new
  backend must not claim otherwise. In the later six-surface UI-adoption
  handoff, each result summary (canonical owner/work IDs, actual revisions,
  graph request/result status and surface resolution status; no source prose)
  is persisted with the turn in the existing `AgentInteractionTurn` browser
  history at `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts`
  and typed in `apps/live-control-ui/src/api/types.ts`. `worldGraphContext`
  source payloads remain stripped from local persistence as today. The UI
  handoff must disclose that this history is browser-local; creating a new
  server transcript store requires a separate design/lease.
- The new path uses the existing injected `AgentRuntime` seam. Deterministic
  fake-runtime tests are the owning proof; no paid live-provider smoke is a
  merge gate.
- This is read-only conversation/retrieval. No graph writes, Plan edit
  proposals, action execution, or review/apply workflow is authorized here.

## §6 Activation gate and future implementation write lease

This design PR creates no implementation lease. Before activation, re-check
current `main`, all open PRs, the active DEMO roadmap, and route ownership.

**Open-PR collision inventory observed 2026-09-29 (recheck at activation):**

| PR | State/topology | Relevant current paths | Effect on this design |
|---|---|---|---|
| #763 Rules query | Open draft, paused; targets `main` | `apps/live_control_server/main.py`, `routes/rules_query.py`, related model/service/tests, `pyproject.toml`, `uv.lock` | Do not edit shared registration or dependency files concurrently. |
| #764 Rules Lawyer ToolHost | Open; stacked on #763 | Plan projection/catalog and Rules UI/test files; no server route registration | No runtime path overlap if the new route stays backend-only. |
| #765 Rules Lawyer synthesis | Open; stacked on #764 | `apps/live_control_server/main.py`, new Rules route/model/service/tests | Second active claimant on central router registration; #763 is not the only collision. |
| #781 Interaction Map | Open, targets `main` | Build Agent semantic-action UI and tests | No backend router or history path overlap. |
| #760 / #761 UI convergence/STOP | Open design PRs stacked in UI docs | UI handoffs/roadmap documents | No backend path overlap. |
| #790 this design | Open design PR, targets `main` | DEMO handoff, roadmap, prior J2 handoff and mirror only | No implementation lease. |

The implementation uses the bounded existing-router seam instead of competing
for `main.py`: create an Agent router with path `/agent/turn`, include it as a
child of the already-registered `/api/live` router in
`apps/live_control_server/routes/live.py`, and expose
`POST /api/live/agent/turn`. Preserve `/api/live/query` behavior and do not
modify `main.py`. Current open PRs #763 and #765 both edit `main.py`; the
complete inventory above must still be refreshed before activation, and the
full application route table must prove no path collision. This avoids an
indefinite wait on paused #763 while preserving the existing app registration
boundary. If review shows `routes/live.py` or the exact route path is newly
leased/claimed, stop and coordinate rather than switching back to `main.py`
unilaterally.

Proposed future implementation paths, subject to PRIME/ARCHITECTURE review and
activation-time collision check:

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/routes/agent.py` | Additive generic turn endpoint; keep packet-bound live route intact |
| Modify | `apps/live_control_server/routes/live.py` | Include the new Agent subrouter under the already-registered `/api/live` router; do not modify `main.py` |
| Create | `apps/live_control_server/models/agent_turn.py` | Strict typed generic request/result and owner/scope statuses |
| Create | `apps/live_control_server/services/agent_turn_service.py` | Resolve surface/work/scope separately, assemble one turn, preserve fail-closed retrieval |
| Modify | `apps/live_control_server/services/agent_runtime.py` | Represent optional graph retrieval scope without fabricating a required one |
| Modify | `apps/live_control_server/services/agent_context_assembler.py` | Assemble surface snapshot, work object and graph lens as separate context channels |
| Modify | `apps/live_control_server/services/agent_world_graph_query_context.py` | Reuse graph lens, preserve exact World/campaign mode and revision evidence |
| Modify | `apps/live_control_server/services/agent_surface_context.py` | Preserve legacy v1 adapter; add no silent surface rewrite |
| Modify | `apps/live_control_server/services/hermes_session_store.py` | Structured scope/thread provider binding with legacy campaign compatibility |
| Modify | `apps/live_control_server/services/hermes_graph_query.py` | Dispatch shared runtime with optional graph capability and explicit result status |
| Create | `tests/test_agent_turn_service.py` | Fake-runtime service matrix, independent revisions and strict absence/failure cases |
| Create | `tests/test_agent_turn_route.py` | API owning-boundary proof including 4xx scope/thread conflicts and no-fallback behavior |
| Modify | `tests/test_live_query_hermes_graph.py` | Preserve existing packet-bound `/api/live/query` compatibility controls |
| Modify | `tests/test_hermes_session_store.py` | Structured owner binding and legacy campaign pointer continuity |
| Modify (later UI adoption only) | `apps/live-control-ui/src/api/types.ts` | Type per-turn resolved-context summary and client-reported unsaved state |
| Modify (later UI adoption only) | `apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts` | Persist safe resolved-context summary with existing browser-local Agent turns; keep full source payload stripped |
| Modify | `Docs/Roadmaps/ROADMAP-demo.md` | Record accepted contract, exact implementation/review evidence, and remaining six UI-owner witnesses |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md` | Keep byte-identical to the sole roadmap authority |
| Modify | `Docs/Plans/HANDOFF-DEMO-J2-world-plan-canvas-composition-v1.md` | Backward-looking completion record for #789 while retaining the user's unaccepted visual judgment |

The future implementation may add only focused owning tests under the named
test directories. New production owner authorities, additional persistent
thread stores, new graph schemas, provider contracts, dependencies, or any UI
route/publisher are stop/rebrief conditions.

## §7 Explicitly out of scope

- Editing the six surface UIs or adding Ask plugins/panels; this is a backend
  contract and resolver slice, followed by a separately activated adoption
  handoff.
- Changing the `/api/live/query` packet/session contract or its C1/C2 behavior.
- Treating `surface_id`, `campaign_id`, `document_id`, `session_number`, a URL,
  a provider pointer, or free-form context text as authorization.
- New WorldKeeper/DungeonMind APIs or graph schemas; work-object CRUD; graph
  writes; extraction changes; retrieval ranking changes; auto-publication.
- Plan edit proposal/application, generic tool/action execution, Combat
  mechanics, or a redesign of the Plan canvas. The human visual rejection of
  the current Plan presentation remains separately open.
- Claims of universal six-surface readiness from backend route tests alone.

## §8 Required owning-boundary evidence

The future implementation's focused contract suite must prove:

1. Request parsing rejects unknown fields, malformed identities, unknown
   `client_work_state` values and oversized messages; `null` is explicit and
   distinguishable from malformed. `graph_request.mode="none"` is an explicit
   no-retrieval request, not a missing or malformed lens; non-null selection
   or session focus paired with it is rejected, never ignored/upgraded.
2. Exact Index turn with no scope returns a normal no-graph conversation result
   and does not invoke a graph tool or claim graph grounding. It succeeds with
   packet loading unavailable: the configured `session_dir()` is used only for
   structured provider-pointer persistence, and no session packet is loaded.
3. Exact managed World Plan with null product campaign and no target session
   resolves the World graph at an observed revision; Plan document ID/revision
   is resolved independently. A browser-reported `new_unsaved` Plan remains a
   client hint only: no draft body or synthetic document ID reaches the server.
   Its graph focus is `kind:"none"`, not a guessed session. Campaign Plan
   preserves the exact resolved session ID and focus campaign. World-mode
   retrieval from a session-focused surface preserves that same exact focus
   when applicable; tests reject guessed session numbers and campaign
   surrogates.
4. World lens maps to explicit `scope_mode=world`, null campaign, and exact
   World. Campaign lens maps to exact nonblank campaign. There is no fallback
   or `surface_id`-derived campaign.
5. Foreign/removed World, campaign, Plan, Build document or Run yields typed
   failure; it never degrades to absent context. A valid existing work object
   at a newer revision resolves against that actual revision and reports
   `changed_since_expected`. A selected graph node not found within a valid
   authorized graph lens reports `selection_found=false`, not foreign identity.
6. Unsaved local Plan draft is explicitly reported as a client hint and never
   serialized as a server document ID or treated as resolved work. No primary
   object is a distinct valid absence. The hint never authorizes reading draft
   contents.
7. Graph not requested, valid empty, selection not found, graph unavailable,
   invalid/foreign scope, and unavailable exact revision have distinct
   outcomes. Valid empty/not-found may invoke the model with explicit empty
   graph context and no grounding claim; invalid or unavailable requested
   retrieval prevents an answer call. Genuine no-scope chat remains allowed.
8. Graph revision/head and work-object revision are both present where
   resolved and are not conflated. A changed expected work revision visibly
   returns expected-versus-used revisions; an exact graph pin is honored or
   rejected, never silently replaced.
9. Same structured owner + same primary object may reuse the provider
   continuation across a surface change. Changing either changes the
   structured pointer key and starts fresh continuity; it cannot read a
   pointer stored for the prior key. The later UI-adoption suite also proves
   that local history selects/creates a separate client thread when scope or
   primary work changes. Buddy transcript/history stays client-owned in the
   existing browser store and is not represented as server-owned.
10. Hermes pointer identity cannot cross owner scopes/work objects or establish
    product identity. Legacy `/api/live/query` retains its exact campaign key;
    the generic route starts a new structured binding without reading or
    rewriting campaign-only legacy bindings. Tests prove both paths.
11. Existing `/api/live/query` campaign packet tests stay green and continue to
    enforce loaded campaign/session equality.
12. Tests inject a deterministic AgentRuntime. No credentials, model calls,
    provider cost or live DB writes are required.
13. The full application route table includes exactly one
    `POST /api/live/agent/turn` registration through the `/api/live` router,
    while `/api/live/query` remains registered once with its unchanged method,
    path and packet-bound behavior.

After design acceptance, delivery proceeds in this order: (1) implement and
verify the backend turn baseline; (2) a separately activated shared Agent
UI/adapters handoff adopts the contract on Index, Plan, Play, Build, Ingest,
and Combat; then (3) end-to-end witnesses exercise those real owner-to-backend
paths. The six surface integrations are mandatory owning evidence; backend
tests alone do not claim universal product availability. The World-reference
lens is a later consumer of this same graph request/resolution authority, not a
prerequisite that displaces universal Agent adoption or creates a competing
lens. Each adopter proves that its actual owner publishes or resolves an exact
identity, that Ask works where claimed, and that absence, unsaved state,
changed revision and unavailable authority are shown truthfully.

## §9 Required commands and handback

The implementation handoff must pin exact current base, PR order, and tests at
activation. Minimum owning evidence:

```bash
pytest -q tests/test_agent_turn_service.py tests/test_agent_turn_route.py \
  tests/test_live_query_hermes_graph.py tests/test_hermes_session_store.py
ruff check apps/live_control_server/routes/agent.py \
  apps/live_control_server/models/agent_turn.py \
  apps/live_control_server/services/agent_turn_service.py
git diff --check
```

Also run current server import/type validation and a full application route
table witness for `POST /api/live/agent/turn`, proving one registration and no
path collision. At activation, recheck route ownership in open PRs #763 and
#765 and any newer open PR. Do not wait on #763 solely because it is paused if
the nested-router seam remains available and unclaimed. Record inherited
unrelated baseline failures rather than silently expanding this lease.

The design-review handback must resolve:

- whether the typed request/result and three independent identities are
  sufficient and exact;
- whether optional no-graph conversation can use the current AgentRuntime
  without introducing a parallel conversation engine;
- the Hermes pointer compatibility/read-upgrade strategy;
- whether one backend resolver can be universal while six product owners
  remain independent;
- whether the proposed nested-router path lease remains minimal after the
  current #763/#765 route-ownership recheck; and
- acceptance of the explicit backend → six-surface shared UI/adapters →
  end-to-end sequence, with World-reference lens work later on this same
  resolved graph authority.

No production implementation begins until PRIME and ARCHITECTURE accept those
decisions, the route-registration collision is cleared by the bounded seam or
explicit coordination, and this handoff is re-anchored as ACTIVE on current
main. The first implementation is the backend turn baseline; universal
six-surface UI adoption and end-to-end proof follow as separately activated
serial DEMO work. The World-reference lens is later and must consume this same
resolved scope/graph authority, not create a second lens.
