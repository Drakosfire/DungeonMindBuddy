# HANDOFF — DEMO: query Session 29 across the existing Elderwyld graph

**Status:** BLOCKED — bounded serial retrieval successor; design only, with no
            implementation, provider, database, or runtime lease.

**Documentation settlement (2026-10-09):** The current-main re-anchor merged as
Buddy #1052 at `22310fab4deb5794d0d3fd3d3ddd956ae3200727` from reviewed
head `1640c92f9385caa0dc76d8e28594a44ec762909e`. Its documentation lease
is closed. The selected-World/Session 29 product gate remains BLOCKED pending
SERVER's exact active database authority and MIND's narrowly authorized native
`eldyrwild` state check. No live Agent turn or operator dogfood is authorized.

**Steward:** DEMO

**Re-anchored source base:** Buddy main
`f9476629ad90c039a2ad7be0de0e6c162161cce3`; DungeonMind remote main
`33ad2983385e8c4e80afb64b07fdb538f9c89901` (2026-10-09). No live
authority was inspected.

**Consumed contracts:** Buddy #833 saved-Plan Ask; #834 full-graph gate; #835
                        local-operator Graph read gate; #836 explicit
                        managed-World-to-native-Graph binding; #853 design-only
                        runtime contract; #938 merged saved-World Plan Ask.

**Topology:** #938 already supplies a durable Graph-backed saved-World Plan Ask on
              the accepted `auto_plan_world` route. This handoff now tracks the
              remaining selected-World/Session 29 answerability and citation gate.
              PRIME assigns any exact implementation or live-witness lease.

**Future implementation PR title:** DEMO: query Session 29 across Elderwyld graph.

## 1. One user-visible capability

The GM asks from the accepted saved Plan conversation about existing native
Elderwyld knowledge in Campaign 1, Campaign 2 / Session 29, and a question
that requires evidence across both campaigns. The Agent returns a grounded
answer with native source citations. Every graph query, expansion, evidence
lookup, and source read for one turn uses one resolved native Graph revision.

The Graph operation is read-only, but a real `/api/live/agent/turn` POST may dispatch
the configured provider and persist a retrieval session, conversation, and receipt;
none is authorized by this blocked handoff. The capability does not initialize
a KnowledgeSpace, admit new sources, ingest a recap, write graph knowledge, create a
Run, or change Plan content. The fresh-World source-admission path remains a distinct
later J3 gate in the roadmap.

## 2. Identity, scope, and turn provenance

- The user-facing request identifies a managed Buddy World and saved Plan. Buddy
  independently resolves the managed World and proves the Plan belongs to it before any
  graph or provider work. The browser and model cannot choose a native Graph ID, Graph
  scope, GM role, binding version, or revision pin.
- Buddy reads the #836 `native_graph_binding` from that managed World. It must be
  present, active, and versioned. Buddy retains the managed World ID, native Graph
  `world_id`, and `binding_version` as separate trusted values for the whole turn. Never
  derive a binding from names, slugs, campaign IDs, graph contents, or equal-looking
  IDs.
- The Buddy Agent-turn boundary resolves the binding. The lower DungeonMind reader
  remains native-Graph-only and receives the bound native Graph `world_id`. Do not make
  the generic MIND reader consult Buddy's World registry.
- The accepted `auto_plan_world` resolver uses the active binding's native World ID,
  takes the first native object lookup or search snapshot as the server-selected
  revision, pins later reads to it, and rechecks the binding before dispatch. The
  binding's `validated_head_revision_id` is activation-time evidence, not that query
  pin. A frozen retry uses its stored Graph revision. The separate generic
  `graph_request` resolver is outside this selected-Plan capability.
- Use native MIND V2 world-wide scope with `campaign_id=None` and GM admissibility.
  Buddy narrative focus may carry `campaign_id=longmont-c2` and
  `session_id=session-29` only in a separate context/ranking field. Neither value may
  become native scope, native `campaign_id`, native focus, or a Graph entity ID. Resolve
  any Session 29 entity ID from the adopted Graph during verification; report its
  absence rather than guessing.
- The local-operator loopback guard from #835 applies to the Agent graph route; MIND GM
  admissibility remains an independent visibility filter, not authentication. This is a
  local-operator capability, not named-user or remote GM access.
- Return a compact receipt with the managed World ID, native Graph `world_id`,
  binding version, native scope/admissibility, Plan revision basis, pinned
  revision, and exact evidence/source references. The accepted Plan Ask sends
  committed Plan content and bounded selected Graph context to the configured
  provider; disclose that use before dispatch. A citation may claim source text
  was opened only when a validated bounded source read occurred. Do not place
  the full Graph or Plan Markdown, hidden prompts, or provider reasoning in
  receipts, history, or logs.
- A later head `R2` does not invalidate a correctly pinned `R1` read: it may finish
  against `R1` and truthfully report that `R1` is no longer head. If any subread loses
  the `R1` pin, repeat the full retrieval at a newly resolved head or fail closed. Never
  mix heads.

## 3. Source findings and evidence limits

The historical source audit at Buddy code head `672d18b` described the generic
`graph_request` path. It does not describe the selected saved-Plan Ask path merged
in #938. At the current Buddy base:

- routes/agent.py::`_graph_resolver` verifies `graph_request.world_id` against the
  independently resolved managed owner or saved Plan. It calls `get_world_container`
  only as an existence check, discards the returned record, then passes that same
  managed ID into `build_existing_graph_context`.
- services/agent_turn_service.py::`build_existing_graph_context` places its `world_id`
  argument into `AgentWorldGraphQueryContextRequest` unchanged.
  services/agent_world_graph_query_context.py::`build_projection_request` copies it
  unchanged into `WorldGraphProjectionRequest`.
- services/world_graph_projection.py::`_project_world_graph_direct` calls
  `direct_services_from_config(request.world_id)`. The direct MIND reader treats that
  argument as the native Graph `world_id`. No managed-to-native translation occurs on
  this path.
- `routes/agent.py::_plan_context_resolver` independently verifies the managed
  World and saved Plan, reads the active versioned `native_graph_binding`, and passes
  `binding.native_world_id` to native direct services. It uses world-wide GM scope,
  pins the native revision through search and source-index reads, and checks that
  the binding has not changed before dispatch.
- `tests/test_agent_turn_route.py::test_policy_resolver_reads_real_pinned_native_graph_with_distinct_managed_id`
  exercises distinct managed/native IDs on an in-memory Graph with seeded source
  artifacts. The same test covers citation/source-read receipt and history replay
  without another Graph read. It does not exercise the historical S22–29 corpus.

These are source and synthetic-route findings, not proof of the current selected
native database/head, C1/C2 or S22–29 source coverage, Thrin identity, or live
Session 29 answerability. MIND's STOP checkpoint/export for
`dogfood-current-corpus-replay-v1` concerns that separate replay World and cannot
establish completeness of native `eldyrwild`. The historical S22 Mireward
addressability report records a missing `source_artifacts` row and
`stored_provenance_invalid` for the published object at its pinned revision; it
does not prove that every S22 object is uncitable or describe the current head.
The previously reported sealed-bundle counts are static package evidence. The
prior native observation at `rev:680c246047d67f9fe0293ee90526f670` is
historical and is not a current live witness. No live Graph read was performed
for this handoff.

## 4. Required acceptance evidence

At activation, pin an exact Buddy/MIND base, exclusive path allowlist,
runtime/database/output ownership, verification commands, and one serial PR topology.
Candidate Buddy boundaries to recheck are `routes/agent.py`,
`services/agent_turn_service.py`, `services/agent_world_graph_query_context.py`,
`services/world_graph_projection.py`, the #836 binding resolver, the Plan Agent
consumer, and their owning tests. RAKE's focused audit covered
`routes/agent.py:214-358`, `services/agent_turn_service.py:563-607`,
`services/agent_world_graph_query_context.py:379-398,581-584`,
`services/world_graph_projection.py:74-94,125-136`,
`integrations/dungeonmind/world_graph_reads.py:853-868,1431-1455`, and
`services/world_graph_binding.py:99-163,184-256`. Candidate Buddy tests to recheck
include `tests/test_agent_turn_route.py`, `tests/test_world_graph_binding.py`,
`tests/test_agent_turn_service.py`, and `tests/test_agent_graph_auth.py`.
MIND owner-boundary evidence should recheck
`tests/unit/test_world_graph_retrieval_service.py`,
`tests/unit/test_world_graph_read_context.py`, and
`tests/unit/test_world_graph_read_observability.py` at its current pinned ref.
These paths are investigation hints, not a current write lease. No MIND
implementation change is requested.

The owning-boundary evidence must prove:

1. **Distinct-ID positive path:** preserve the already tested synthetic
   managed-ID-A to native-ID-B binding and pinned-revision behavior on the
   `auto_plan_world` route. For any real witness, first prove the exact selected
   managed World, committed Session 29 Plan, active binding, native DB, and head;
   do not assume the native ID or current head from historical documents.
2. **Fail-closed binding path:** missing, inactive, wrong, or stale binding fails before
   a MIND reader or provider call. A binding change during turn setup cannot silently
   retarget a turn.
3. **Answerability and citations:** after SERVER identifies the exact authority
   and MIND completes a narrowly authorized read-only source/provenance check,
   use a separately leased witness against the actual non-empty native
   `eldyrwild` Graph. Use verified facts already present in the current graph for
   one C1 question, one C2 Session 29 question, and one cross-campaign multi-hop
   question. Prove each claim from native evidence/source references at `R1`. Do not
   invent a Session 29 Graph node or assume recap admission.
4. **Pinned-head concurrency:** in a separate disposable native fixture, resolve `R1`,
   advance only that fixture to `R2` while retrieval is in progress, and prove every
   subread completes at `R1` with truthful head reporting or performs a full retry at
   `R2`. Mixed revisions fail.
5. **Restart freshness:** in that fixture, advance `R1` to `R2`, restart Buddy,
   re-resolve binding and head, and prove a new query uses `R2`. Never advance the real
   `eldyrwild` Graph for fixture tests.
6. **Disclosure and result:** the accepted Plan UI shows the configured provider
   destination and that bounded Graph excerpts may be sent before dispatch; after the
   turn it shows the exact evidence references and excerpts actually sent. No full Graph
   or Plan payload is placed in receipts, stored conversation history, traces, or logs.
7. **Auth and scope:** exercise the #835 local-operator guard on the exact Agent graph
   route; reject denied/non-loopback requests and non-GM native admissibility. Other
   unguarded internal Graph/evidence routes found in the #835 audit remain outside this
   implementation lease and must not be called by this capability or represented as
   secured by #835.

The live `eldyrwild` Graph reads would be read-only, but the Agent turn is not
operationally read-only: it may dispatch a provider and persist APP-STATE state.
The fixture may publish only to its isolated
disposable native authority. A live managed-World binding action, if needed, requires
PRIME to confirm the exact target World and runtime owner under the #836 handoff. No
KnowledgeSpace creation, persistent demo DB target change, console/SQL repair, shared
service start, or real Graph mutation is authorized by this BLOCKED design.

## 5. Blockers and activation

This handoff remains BLOCKED. The exact path is not ready for implementation until:

1. SERVER identifies the exact native database/head and selected managed World;
   PRIME confirms the committed Session 29 Plan and any real binding witness.
2. MIND completes a narrowly authorized read-only check of native C1/C2 and
   S22–29 source coverage and Thrin identity at that authority. Its separate
   `dogfood-current-corpus-replay-v1` STOP checkpoint/export is not this proof.
3. DEMO and PRIME refresh current refs, open PRs, worktrees, and runtime leases.
   #826 remains a paused, independent empty KnowledgeSpace path, not a predecessor.
4. PRIME pins the exact provider-dispatch, APP-STATE persistence, runtime,
   database, output, and path lease before any live Agent-turn witness or code
   change. The #835 local-operator route guard remains the applicable auth gate.

Until these gates are satisfied, no Graph query, provider call, database connection,
server start, registry mutation, or UI implementation is authorized by this handoff.
PRIME owns implementation activation, exact-head review, and merge coordination. A
handoff message saying “done” is not acceptance; DEMO must inspect the returned diff and
run the original witness.

This documentation slice does not close Session 28 recap admission, fresh-World
source admission, any J1–J6 gate, visual acceptance, hosted readiness, or
operator dogfood acceptance.
