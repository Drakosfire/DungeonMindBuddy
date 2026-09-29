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
  primary work object, and optional graph lens independently. Exact World or
  campaign authority is server-resolved; absent context is explicit; supplied
  invalid/foreign identity fails closed. `/api/live/query` remains packet-bound.
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
semantics. The proposed endpoint is `POST /api/agent/turn`; it is additive and
does not weaken `/api/live/query`.

```json
{
  "schema": "dmb_agent_turn_request_v1",
  "thread_id": "buddy-thread-opaque",
  "turn_id": "client-turn-opaque",
  "surface": {"surface_id": "plan", "instance_id": "lease-identity"},
  "owner_scope": {"kind": "world", "world_id": "verified-by-server"},
  "primary_work": {"kind": "plan", "object_id": "document-id", "expected_revision": 3},
  "graph_selection": {"node_id": "node:hempholm", "revision_pin": null},
  "message": "What have we established about this place?"
}
```

`owner_scope` is explicitly one of `null`, `{kind:"world", world_id}`, or
`{kind:"campaign", campaign_id}`. `primary_work` and `graph_selection` are
optional and independent. The request carries bounded identity only; no client
`ambientSummary`, quoted work prose, source excerpts, workspace paths, fake
session numbers, or caller-asserted resolved statuses.

Every non-null submitted identity is re-resolved at the server-owned boundary
on every turn. A missing/foreign/malformed supplied identity is rejected with
a typed 4xx and no downgrade to null. A genuinely absent optional identity is
allowed and reported absent. The server may return a resolved current owner
snapshot distinct from the caller's `expected_revision`; a changed revision
must be visible and cannot be represented as the requested stale version.

The result separates:

```text
surface: current surface_id + resolution status + owner snapshot generation
scope: absent | resolved | rejected | unavailable; kind + canonical owner ID
primary_work: absent | resolved | unsaved | stale | foreign | unavailable
graph: not_requested | ready | empty | unavailable; World, scope_mode,
       graph revision, observed head, is_head, optional exact selected node
conversation: Buddy thread ID + turn ID + server binding outcome
answer: text/status/warnings; no implied graph grounding when graph not used
```

Statuses must not collapse: no scope is different from an invalid foreign
scope; no primary object is different from an unsaved local draft; empty graph
is different from graph-service outage; a non-head graph revision is different
from the current head. A requested graph that cannot be authoritatively
resolved follows the existing fail-closed retrieval policy and does not call
the answer model. A turn with no requested/available scope may use ordinary
conversation without graph tools and must not claim retrieval or citations.

The response carries the exact graph revision/head state and the independent
primary-work revision used for that turn. Graph and document revisions must
never be compared as if they share an identity space. A UI request-generation
token may suppress stale late responses; it is not server authorization.

## §5 Conversation binding and compatibility

- Stable Buddy `thread_id` is not a Hermes `hermes_session_id` and not a graph
  session ID. It is bound server-side to structured owner scope plus the
  primary work-object identity when present. Surface is per-turn context, not
  an owner ID.
- Surface changes within the same verified owner scope and same primary work
  object may retain the Buddy conversation. Changing scope or primary object
  rejects the old binding or requires a new thread; it never reuses a provider
  pointer by campaign string coincidence.
- A provider continuation pointer is internal, bound to the Buddy thread and
  structured owner key, and can never establish World/campaign authority.
- Existing campaign-scoped `/api/live/query` requests and pointer files remain
  compatible. The implementation must explicitly define read/upgrade behavior
  for legacy campaign keys; no lossy rewrite or deletion of existing pointer
  state is allowed.
- The new path uses the existing injected `AgentRuntime` seam. Deterministic
  fake-runtime tests are the owning proof; no paid live-provider smoke is a
  merge gate.
- This is read-only conversation/retrieval. No graph writes, Plan edit
  proposals, action execution, or review/apply workflow is authorized here.

## §6 Activation gate and future implementation write lease

This design PR creates no implementation lease. Before activation, re-check
current `main`, all open PRs, the active DEMO roadmap, and route ownership.

**Known collision gate:** open PR #763 is a paused Rules route candidate. It is
not permission to share route registration files concurrently. The future
implementation handoff must re-check whether #763 still owns
`apps/live_control_server/main.py`, `routes/live.py`, or related router
registration. If any required production path overlaps, wait for #763 to settle
or rebrief/split the route seam before activating. Do not quietly append a
second router to a contested central file.

Proposed future implementation paths, subject to PRIME/ARCHITECTURE review and
activation-time collision check:

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/routes/agent.py` | Additive generic turn endpoint; keep packet-bound live route intact |
| Modify | `apps/live_control_server/main.py` | Register the new route only after the #763 collision is cleared |
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

1. Request parsing rejects unknown fields, malformed identities and oversized
   messages; `null` is explicit and distinguishable from malformed.
2. Exact Index turn with no scope returns a normal no-graph conversation result
   and does not invoke a graph tool or claim graph grounding.
3. Exact managed World Plan with null product campaign and no target session
   resolves the World graph at an observed revision; Plan document ID/revision
   is resolved independently.
4. World lens maps to explicit `scope_mode=world`, null campaign, and exact
   World. Campaign lens maps to exact nonblank campaign. There is no fallback
   or `surface_id`-derived campaign.
5. Foreign/stale World, campaign, Plan, Build document, Run, or selected-node
   identity yields typed failure; it never degrades to absent context.
6. Unsaved local Plan draft is explicitly unsaved and never serialized as a
   server document ID. No primary object is a distinct valid absence.
7. Graph empty, graph unavailable, and graph not requested produce distinct
   response states. A requested unavailable/invalid graph prevents an
   authoritative answer call; genuinely unscoped chat remains allowed.
8. Graph revision/head and work-object revision are both present where
   resolved and are not conflated. A stale expected work revision is visible.
9. Same structured owner + same primary object may continue the Buddy thread
   across a surface change; changing either rejects/rebinds explicitly.
10. Hermes pointer identity cannot cross owner scopes or establish product
    identity; existing campaign pointer bindings remain readable and stable.
11. Existing `/api/live/query` campaign packet tests stay green and continue to
    enforce loaded campaign/session equality.
12. Tests inject a deterministic AgentRuntime. No credentials, model calls,
    provider cost or live DB writes are required.

Six-surface integrations remain separate owning evidence after the backend
contract: each surface must prove its actual current owner publishes or resolves
an exact identity, that Ask works where it is claimed, and that absence,
unsaved state, stale state and unavailable authority are shown truthfully.

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

Also run current server import/type validation and any route-registry check
required by `#763` after it settles. Record inherited unrelated baseline
failures rather than silently expanding this lease.

The design-review handback must resolve:

- whether the typed request/result and three independent identities are
  sufficient and exact;
- whether optional no-graph conversation can use the current AgentRuntime
  without introducing a parallel conversation engine;
- the Hermes pointer compatibility/read-upgrade strategy;
- whether one backend resolver can be universal while six product owners
  remain independent;
- whether the proposed path lease is minimal after #763 settles; and
- the explicit follow-up order for six UI surface adopters and the separate
  World-reference lens.

No production implementation begins until PRIME and ARCHITECTURE accept those
decisions, the collision is cleared, and this handoff is re-anchored as ACTIVE
on current main. The next step is the reusable World-reference lens; it must
consume this same resolved scope/graph authority, not create a second lens.
