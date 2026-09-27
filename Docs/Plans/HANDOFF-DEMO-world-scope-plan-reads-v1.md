---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J1
  - Direction: STEWARD → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DEMO-world-scope-plan-reads-v1.md
  - PR topology: parallel-independent of #779

  ## Review contract
  A published managed World with a legitimate blank campaign ID must be
  inspectable and retrievable by Plan at its exact World revision. Campaign
  lenses remain strict. The pinned handoff and exact-head evidence govern.
---

# HANDOFF — DEMO: consume exact world-scope Plan reads

**Created:** 2026-09-27
**Status:** ACTIVE — DEMO-J1 world-scope Plan read repair
**Conversation/workstream:** LOCAL DEMO ACCEPTED / DEMO-J1
**Flow / owner:** DEMO / Buddy Plan and graph-read consumer
**Direction:** STEWARD → CODE → REVIEW
**Design authority base:** Buddy `main@58c650e80eee0825c4d713999fcbbd3789856c33` after #778 merge `d41a2cc59bff5e9f6133d774cc932e05e981b7f1`
**Activation gate:** satisfied 2026-09-27. The product owner directed the demo to resume functional work; the optional DEMO-READY roadmap decision sync records `RESUME_NON_UI`; both roadmap copies record #778 and the published World. Re-anchored to Buddy `main@712dbc93fa6721d35cb4a9ccf2b2db950ee709fd` before activation.
**Dispatch base:** fresh `origin/main` containing this handoff; record the exact SHA
**PR topology:** parallel-independent of open DEMO-J3 PR #779 at `b3eab88b27acc547e76998c7960cd9c06ad31e62`; #779 owns only a new PostgreSQL integration test and report, and has no behavioral dependency on this read repair. Exact head rechecked at activation.
**PR authorization:** open/update one PR titled `DEMO: read managed World scope in Plan`; no successor/repair PR.
**Runtime/state ownership:** implementation tests use fixtures; the post-implementation browser witness uses the existing isolated Of Conks DB, serialized with its current API/UI processes, never C1/C2 or another lane's database

## §1 Mission and merge-ready invariant

The GM can inspect a published managed-World object from Plan and ask
DungeonBuddy about that same World without an invented campaign. The invariant
for this managed World is that Plan sends the exact verified World ID,
`scope_mode=world`, blank campaign ID, and pinned revision through projection,
selected-object reads, Agent context, Hermes tool binding, and retrieval.
Campaign scope always requires its exact nonblank campaign. Other existing
world-scope callers may retain a nonblank narrative/focus campaign anchor; the
contract must not reinterpret that anchor as campaign-only filtering. Blank
campaign is valid only with explicit world scope. Cross-World, stale revision,
missing head and malformed requests fail closed. The Agent's graph tools must
inherit the server-resolved scope, not a model-supplied or UI-fabricated scope.

Pre-dispatch critique: the easy false fix is relaxing Plan's first guard while
Hermes still injects no `scopeMode` and retrieval still requires a nonblank
campaign. The owning proof must reach a real retrieval request and Plan Ask,
not merely a component helper. If this requires a new DungeonMind graph
schema, a new durable campaign mapping, or a new Agent conversation protocol,
stop and rebrief.

## §2 Authority, input, topology and remaining falsehoods

- Parent authorities: `Docs/Roadmaps/ROADMAP-demo.md`, completed selected-World
  and World-selection handoffs, #778's literal evidence correction, and the
  accepted DungeonMind world-scope projection/retrieval contract.
- Exact input: managed World `of-conks-j1-fresh-rehearsal`, published revision
  `rev:22ef509825ee1048efc73a1a1aa4a60c`, normal projection snapshot with
  `worldId` set, `scopeMode=world`, and `campaignId=''`; persisted Plan
  `23263744-03f3-4074-984c-b31f5d4704e4`.
- Observed failure: projection returns 21 objects and 5 relationships, but
  Plan View says exact scope is missing; Ask returns `Resolved
  world_graph_context is missing world_id or campaign_id.` No model answer
  was accepted. `WorldGraphRetrievalRequestContext` also has an unconditional
  `campaign_id` minimum length, and Hermes tool injection omits scope mode.
- No unmerged behavioral dependency on #779. The two lanes must not share
  files, disposable databases, migration source, or test outputs. If overlap
  appears, serialize/transfer before edits.
- Named successor: DEMO-J1 Plan authoring/generation and the remaining J1–J6
  journey. This slice does not make extraction complete, make Agent writing
  useful, fix publication qualification, or certify the human demo.
- Backward-looking state sync before activation: the DEMO steward updated
  `Docs/Roadmaps/ROADMAP-demo.md` and its byte-identical active mirror in one
  guarded transaction, recording #778 and the actual 21-object/5-edge World
  publication. This implementation PR does not edit those roadmap paths. After
  merge, the next dependent DEMO handoff carries the accepted repair and new J1
  frontier as predecessor sync; if no successor is ready, the steward updates
  the roadmap and mirror directly after re-anchoring.

| Field | Required content |
|---|---|
| Runtime/state ownership | Dedicated fixture state for automated tests; serialized use of the existing isolated Of Conks DB on ports 8815/5196 for post-implementation browser proof; no writes to #779's disposable PostgreSQL database or C1/C2 |

## §3 Observable paths and adversarial sequences

| Path | Required outcome | Owning boundary |
|---|---|---|
| Managed World objects → View | Exact world-scope projection opens the selected complete object with `campaignId=""` | UI reference resolution + complete-object request |
| Plan Ask → graph retrieval | Server-resolved world scope reaches Hermes tools and returns source-grounded World context | query route, Agent assembly, Hermes binding, retrieval request |
| Campaign C1/C2 | Nonblank campaign and focus rules unchanged | existing contract/surface regressions |
| World with blank campaign | Allowed only with explicit world mode and exact World/revision | request validation |
| World with narrative anchor | Existing nonblank anchor remains legal under world mode and does not narrow retrieval to campaign mode | existing C1/C2 controls |
| Campaign with blank campaign | Rejected, never upgraded to world mode | request validation |
| Model supplies a different scope | Authoritative World/revision/mode overrides or rejects it | Hermes graph-tool binding |
| World switch or head change mid-request | Stale answer/object not presented as current | Plan surface + server pin validation |
| No head, unknown World, malformed scope | Visible unavailable/error; no C2/Eldyrwild fallback | route and UI integration |

## §4 Files in scope — ACTIVE write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.ts` | Stop substituting managed World ID into campaign ID |
| Modify | `apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.test.ts` | Managed World blank-campaign request and existing anchored-world controls |
| Modify | `apps/live-control-ui/src/graphLens/useWorldGraphLensProjection.test.tsx` | Preserve existing nonblank narrative-anchor world projection |
| Modify | `apps/live-control-ui/src/graphReference/resolveGraphReference.ts` | Accept blank campaign only for exact world scope |
| Modify | `apps/live-control-ui/src/graphReference/resolveGraphReference.test.ts` | Adversarial scope cases |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanWorldGraphObjectsPanel.test.tsx` | Plan object View integration with exact blank-campaign/world projection |
| Modify | `apps/live_control_server/models/world_graph_object_projection.py` | Permit blank campaign for world-scope complete-object reads; keep campaign strict |
| Modify | `tests/test_world_graph_object_projection.py` | Complete-object request validation and scope mapping |
| Modify | `apps/live_control_server/services/agent_world_graph_query_context.py` | Validate campaign conditionally by scope mode; preserve resolved mode |
| Modify | `apps/live_control_server/services/agent_context_assembler.py` | Preserve scope mode and validate campaign conditionally |
| Modify | `apps/live_control_server/services/agent_runtime.py` | Typed Agent scope mode, if required by propagation |
| Modify | `apps/live_control_server/services/hermes_agent_runtime.py` | Exact world-mode mapping into Hermes |
| Modify | `apps/live_control_server/services/hermes_graph_query.py` | Exact dispatch scope propagation, if required |
| Modify | `apps/live_control_server/services/hermes_graph_agent_contract.py` | Carry authoritative scope mode through strict policy and turn-request IPC |
| Modify | `apps/live_control_server/services/hermes_graph_agent.py` | Bind deserialized scope mode into tool capability scope and turn execution |
| Modify | `src/graph_memory/hermes_graph_plugin.py` | Inject authoritative scope mode into graph tools |
| Modify | `src/graph_memory/retrieval/models.py` | Conditional campaign validation by scope mode |
| Modify | `tests/test_agent_context_assembler.py`, `tests/test_hermes_agent_runtime.py`, `tests/test_live_query_hermes_graph.py`, `tests/test_hermes_graph_agent.py`, `tests/test_hermes_graph_agent_host.py`, `tests/test_graph_retrieval_interaction.py` | Owning query/service/host/retrieval proof |
| Create | `tests/test_world_graph_retrieval_contract.py` | Direct conditional scope validation: world with blank campaign accepted; campaign with blank campaign rejected; anchored world remains accepted |

**Bounded discovery:** up to four additional focused test files under the
listed UI/server/graph-memory test directories if the named tests cannot
exercise the actual route or graph tool. Name each in handback. Any additional
production path, schema, route, dependency, or contract owner is a stop report.

## §5 Explicit collision boundary

Do not edit #779's `tests/integration/test_demo_j3_play2_persistent_vnext_postgres.py`
or `Docs/Reports/REPORT-DEMO-J3-PLAY-2-persistent-vnext-postgres.md`;
DungeonMind/WorldKeeper repositories, DB migrations, package pins/lockfiles,
first-World prepare/confirm, extraction prompts/profiles, source corpus, Play,
Build, Combat, or generic C1/C2 lens policy are also out. Do not encode the
selected World ID as a fake campaign ID merely to pass validation.

## §6 Contract and failure behavior

```text
verified Plan document + published World revision
→ projection {worldId, campaignId:"", scopeMode:"world", revisionId}
→ exact Plan object View and server-resolved Agent scope
→ Hermes graph tools inject the same World/mode/revision
→ world-scope retrieval request/read
```

For `scopeMode=campaign`, `campaignId` remains required and exact. For this
managed World, Plan sends an empty campaign rather than copying the World ID or
Plan's storage campaign label. In general world scope, an explicitly supplied
narrative/focus campaign anchor remains legal and does not narrow the scope;
absence of an anchor is also legal. Focus and source admissibility retain
their existing checks. A graph tool's model arguments cannot override server
World, campaign anchor, mode or revision. Changing World or revision
invalidates stale resolution; no cached C2 result may be used as fallback.
Existing Plan document persistence is untouched.

## §7 Evidence required to merge

| Guarantee | Owning proof |
|---|---|
| Conditional blank-campaign rule | Projection, complete-object, retrieval request and UI exact-scope tests: world blank pass, campaign blank fail, invalid mode fail |
| Existing world anchors | C1/C2 and lens-projection regression: nonblank anchor remains legal under world mode |
| Agent scope propagation | Query-context, Agent assembler + Hermes IPC/runtime mapping tests assert exact world/mode/revision and no synthetic campaign |
| Tool authority | Host/plugin test supplies hostile model scope and observes authoritative injected scope |
| Real retrieval | Query-route/integration test reaches world-scope graph retrieval and returns a known object/evidence; C1/C2 controls remain green |
| Product transition | Exact-head browser: reopen saved Of Conks Plan, View Hempholm, Ask one grounded question, inspect response and query receipt; no C2/Eldyrwild fallback |
| Backward state truth | Steward's pre-dispatch roadmap sync is byte-identical and accurately describes #778 plus publication, not this PR as merged |

```bash
uv run pytest -q tests/test_world_graph_object_projection.py tests/test_agent_context_assembler.py tests/test_hermes_agent_runtime.py tests/test_live_query_hermes_graph.py tests/test_hermes_graph_agent.py tests/test_hermes_graph_agent_host.py tests/test_graph_retrieval_interaction.py tests/test_world_graph_retrieval_contract.py
npm --prefix apps/live-control-ui test -- src/graphReference/resolveGraphReference.test.ts src/planSurface/reference/planGraphContextRequest.test.ts src/planSurface/components/PlanWorldGraphObjectsPanel.test.tsx src/graphLens/useWorldGraphLensProjection.test.tsx
npm --prefix apps/live-control-ui run typecheck
uv run ruff check apps/live_control_server/models/world_graph_object_projection.py apps/live_control_server/services/agent_world_graph_query_context.py apps/live_control_server/services/agent_context_assembler.py apps/live_control_server/services/agent_runtime.py apps/live_control_server/services/hermes_agent_runtime.py apps/live_control_server/services/hermes_graph_query.py apps/live_control_server/services/hermes_graph_agent_contract.py apps/live_control_server/services/hermes_graph_agent.py src/graph_memory/hermes_graph_plugin.py src/graph_memory/retrieval/models.py
git diff --check
git diff --name-only origin/main...HEAD
```

If the local live browser/Agent runtime needs a model credential or dependency
unavailable to the PR worker, tests remain necessary but are not a substitute
for the product witness; report the exact unavailable gate and leave merge
on HOLD. Do not claim a semantic answer from a mocked Agent response.

## §8 Review handback

Give the reviewer exact base/head, PR URL, all changed paths vs §4, the
world/campaign/mode/revision values at each boundary, test and browser
  receipts, model-call/cost evidence, C1/C2 regression, roadmap mirror check,
baseline failures, and the remaining demo gaps. Review every distinct head.

## §9 Acceptance rubric and stop conditions

- [x] Steward activation and backward-looking #778/World publication sync preceded dispatch.
- [ ] The one assigned PR alone owns the listed paths and does not collide with #779.
- [ ] Managed World scope with empty campaign works in Plan View, selected-object View, and actual Ask retrieval.
- [ ] Existing C1/C2 world scope with a nonblank narrative anchor remains valid.
- [ ] Campaign scope and adversarial mismatch remain fail-closed.
- [ ] Hermes tools receive the server scope mode; no fabricated campaign or C2 fallback.
- [ ] Exact-head browser witness uses the published Of Conks World and saved Plan.
- [ ] Next dependent handoff or guarded steward sync records this PR's merged result; no claim of full DEMO-J1/J1–J6 acceptance.

Stop if World-scope Agent retrieval needs a new DungeonMind schema, a new
durable identity mapping, a second production route, a path outside §4, a
collision with #779, or a change to the meaning of campaign-scope reads.
