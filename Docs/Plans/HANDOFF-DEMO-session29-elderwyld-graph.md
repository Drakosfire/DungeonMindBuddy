# HANDOFF — DEMO: query Session 29 across the existing Elderwyld graph

**Status:** BLOCKED — bounded serial retrieval successor; design only, with no
            implementation, provider, database, or runtime lease.

**Steward:** DEMO

**Design base:** Buddy main `e6a4e7d3c00b1587e5f8821f2d50319eafd2adc1` (2026-10-02).

**Consumed contracts:** Buddy #833 saved-Plan Ask; #834 full-graph gate; #835
                        local-operator Graph read gate; #836 explicit
                        managed-World-to-native-Graph binding; #853 design-only
                        runtime contract; DungeonMind main
                        `619329c2c8586572ffd04558a79b3555c2ca3764`.

**Topology:** serial — AGENT-INTERACTION production conversation runtime, DEMO Plan
              conversation cutover, then this J3 retrieval capability. PRIME assigns the
              runtime owner and each exact implementation lease. This handoff is a
              separate successor to the merged design-only #853 contract; do not fold
              Graph retrieval into the runtime implementation lease.

**Future implementation PR title:** DEMO: query Session 29 across Elderwyld graph.

## 1. One user-visible capability

After the production World conversation runtime and Plan consumer cutover are accepted,
the GM asks from the saved Plan conversation about existing native Elderwyld knowledge
in Campaign 1, Campaign 2 / Session 29, and a question that requires evidence across
both campaigns. The Agent returns a grounded answer with native source citations. Every
graph query, expansion, evidence lookup, and source read for one turn uses one resolved
native Graph head.

This is a read-only query of the already populated MIND V2 Graph. It does not initialize
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
- Resolve the current native Graph head once at turn start, after resolving the active
  binding. The binding's `validated_head_revision_id` records activation-time evidence;
  it is not the current query pin. Buddy supplies the current native head as the
  server-selected revision pin for every graph-backed subread. Ignore or reject any
  request-supplied revision pin. If the binding version changes before provider
  dispatch, or the native authority cannot prove the pinned head, fail closed without
  dispatch.
- Use native MIND V2 world-wide scope with `campaign_id=None` and GM admissibility.
  Buddy narrative focus may carry `campaign_id=longmont-c2` and
  `session_id=session-29` only in a separate context/ranking field. Neither value may
  become native scope, native `campaign_id`, native focus, or a Graph entity ID. Resolve
  any Session 29 entity ID from the adopted Graph during verification; report its
  absence rather than guessing.
- The local-operator loopback guard from #835 applies to the Agent graph route; MIND GM
  admissibility remains an independent visibility filter, not authentication. This is a
  local-operator capability, not named-user or remote GM access.
- Return a compact receipt with the managed World ID, native Graph `world_id`, binding
  version/state, native scope/admissibility, Plan revision basis, Buddy narrative focus,
  pinned head, head-at-resolution/current-head status, and exact evidence/source
  references. Show the bounded excerpts actually sent to the configured provider after
  the turn. Disclose provider destination and bounded Graph evidence/source use before
  dispatch. Do not send or log the full Graph or Plan Markdown, hidden prompts, or
  provider reasoning.
- A later head `R2` does not invalidate a correctly pinned `R1` read: it may finish
  against `R1` and truthfully report that `R1` is no longer head. If any subread loses
  the `R1` pin, repeat the full retrieval at a newly resolved head or fail closed. Never
  mix heads.

## 3. Source findings and evidence limits

The focused source audit at Buddy code head `672d18b` (Agent query code unchanged through docs-only #853 at design base `e6a4e7d3`) found that the source path does not yet consume #836's binding:

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
- #836 stores `native_graph_binding` on WorldContainerRecord, but the Agent query path
  does not read it. The current request `revision_pin` is copied through rather than
  being resolved as the current head once at turn start.
- Existing tests cover binding lifecycle separately and stub graph resolution in Agent
  turn tests. They do not prove a deliberately distinct managed ID resolves to the bound
  native ID, preserve binding/head pins, or fail before dispatch on inactive/stale
  binding.

These are source findings, not proof of a production Plan conversation, a current native
Graph head, or live C1/C2 answerability. The previously reported sealed-bundle counts
are static package evidence. The prior native observation at
rev:680c246047d67f9fe0293ee90526f670 is historical and is not a current live witness. No
live Graph read was performed for this handoff.

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
include `tests/test_world_graph_binding.py`, `tests/test_agent_turn_service.py`,
and `tests/test_agent_graph_auth.py`. MIND owner-boundary evidence should recheck
`tests/unit/test_world_graph_retrieval_service.py`,
`tests/unit/test_world_graph_read_context.py`, and
`tests/unit/test_world_graph_read_observability.py` at its current pinned ref.
These paths are investigation hints, not a current write lease. No MIND
implementation change is requested.

The owning-boundary evidence must prove:

1. **Distinct-ID positive path:** a deliberately distinct managed World ID is actively
   bound to native Graph `world_id`=`eldyrwild`. The real Agent turn path resolves
   native ID B from managed ID A, records the exact `binding_version`, resolves current
   native head `R1`, and calls every graph/evidence/source read with `R1`. The request
   cannot substitute its own native ID, scope, role, binding version, or revision pin.
2. **Fail-closed binding path:** missing, inactive, wrong, or stale binding fails before
   a MIND reader or provider call. A binding change during turn setup cannot silently
   retarget a turn.
3. **Answerability and citations:** on a read-only witness against the actual non-empty
   native `eldyrwild` Graph, use verified facts already present in the current graph for
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

The live `eldyrwild` witness is read-only. The fixture may publish only to its isolated
disposable native authority. A live managed-World binding action, if needed, requires
PRIME to confirm the exact target World and runtime owner under the #836 handoff. No
KnowledgeSpace creation, persistent demo DB target change, console/SQL repair, shared
service start, or real Graph mutation is authorized by this BLOCKED design.

## 5. Blockers and activation

This handoff remains BLOCKED. The exact path is not ready for implementation until:

1. PRIME assigns the production Agent runtime owner and exact lease for the merged #853
   conversation contract, including reconciliation of the suspended dirty checkout.
2. The serial DEMO Plan consumer cutover adopts that runtime and proves durable Plan
   conversation context. This J3 slice then adds Graph retrieval as its own
   capability/PR.
3. DEMO and PRIME refresh current Buddy/MIND refs, open PRs, worktrees, and runtime
   leases. Reconfirm #826 remains an independent paused KnowledgeSpace path; it is not a
   predecessor for reading existing `eldyrwild`.
4. RAKE completed the source-only route/test audit at Buddy code head `672d18b`. PRIME
   and DEMO must settle the applicable #835 route exposure gate for this exact Agent
   query route without expanding this slice into unrelated routes.
5. The designated runtime owner confirms a read-only current-head path for `eldyrwild`,
   verified C1/C2 questions supported at that head, and availability of isolated
   concurrent-publication/restart fixtures.
6. PRIME confirms the exact managed World for any real binding witness. The
   implementation handoff must then pin its own path allowlist, tests, ports, database,
   output directories, provider use, merge order, and return evidence.

Until these gates are satisfied, no Graph query, provider call, database connection,
server start, registry mutation, or UI implementation is authorized by this handoff.
PRIME owns implementation activation, exact-head review, and merge coordination. A
handoff message saying “done” is not acceptance; DEMO must inspect the returned diff and
run the original witness.

This slice does not close Session 28 recap admission, fresh-World source admission,
J1–J6 acceptance, visual acceptance, hosted readiness, or operator acceptance.
