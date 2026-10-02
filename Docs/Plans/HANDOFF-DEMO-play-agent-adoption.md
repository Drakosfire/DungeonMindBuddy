# HANDOFF — DEMO: Play Agent on an exact World Run

**Status:** BLOCKED — refreshed design ready for PRIME activation review; no implementation lease
**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Design anchor:** Buddy `main@c3904bc1e08df689b92d5a0b710b546f77af4600`
**Topology:** serial. #836 and #839 are settled; #848's additive trace-instrumentation PR is merged. PR #826 is still the unresolved prior implementation PR, so this Play handoff remains BLOCKED and cannot be dispatched until #826 is resolved/closed or PRIME explicitly records a superseding disposition/topology. No implementation or runtime lease is active.

## User transition

From a managed World with a selected World-owned Play Run, the operator can ask DungeonBuddy about the current moment of play and continue a surface-specific Play conversation. Each answer must use the exact selected Run snapshot and its pinned authored material. A late response or a change of Run must never make an answer about Run A appear to describe Run B.

This is one Buddy product capability: adopt the generic Agent turn contract on Play. It does not add Graph retrieval, citations, mutations, a new Agent framework, or changes to Run ownership.

## Current evidence and gates

Buddy #820 completed the World PlayRun C2 UI migration at `bfa741261e715eadb48d873f87fccc1764417da8`; its lease ended at merge. The generic POST /api/live/agent/turn request permits Play and Run locators, but the current work resolver accepts only Plan and returns work_kind_unresolved for a Run. Play has no Ask plugin. Its PlaySurfacePublisher builds legacy A7 publication context from campaign V1 records only, so that publication is not authority for a World V2 Agent turn.

This handoff is re-anchored at Buddy `main@c3904bc1e08df689b92d5a0b710b546f77af4600`.
PR #836 merged at `6de8d831ab82308086677fb3038122936ab9a756` from
`cf226c24da4973f88bbfb904889b45e857ffef31`; it adds the managed-World to
native-Graph binding but does not change the generic Agent resolver or Play
request contract. PR #839 merged at
`47f9955fd054017a1739dfa8129df65dd61d6bcd` and changes Plan source-bundle
diagnostics only. Both predecessor gates named in the original design are
settled.

PR #848 merged its worker-phase instrumentation at
`be608e77ee86ecc2cd57336e98b289c9901823e7`. The merged change adds
allowlisted internal trace phases; it does not change Run resolution, pointer
lookup, provider dispatch, turn results, or concurrency. RAKE DUTY's comparison
of #848 with this Play design found no resolver or receipt dependency. Play
must tolerate additive trace names, keep its Run/Runbook receipt distinct from
trace telemetry, and never put Run identity or authored Play prose in timing
spans.

PR #826 remains OPEN/paused and unmergeable at head
`4fa28e586783f0e63edb85fa664afa53521367f6`, based on stale
`5b7e1e4543c94708e11687feb60093d98d6db93f`. Its exact eight changed paths
are:
- `apps/live_control_server/integrations/dungeonmind/world_space_provisioning.py`
- `apps/live_control_server/routes/world_containers.py`
- `apps/live_control_server/services/world_container_registry.py`
- `apps/live_control_server/services/world_space_binding.py`
- `pyproject.toml`
- `tests/integration/test_world_space_binding_postgres.py`
- `tests/test_world_space_binding.py`
- `uv.lock`

RAKE DUTY's read-only rework audit
against Buddy main `c3904bc1e08df689b92d5a0b710b546f77af4600` and merged #836
found that #826's v1 contract cannot be resumed unchanged:

- #826 adds flat `space_*` fields to v1 registry records, while current main
  stores v2 records with nested `native_graph_binding` and forbids extras. The
  v1 reader cannot consume those added fields, and #826's v1-only model cannot
  consume v2 records. Redesign on v2 with a distinct typed
  `knowledge_space_binding`; preserve the existing native Graph relation and
  current read-only v1 compatibility. Adapt writes to v2 CAS and preserve both
  relations when committing after the external MIND call.
- #826 and #836 both change `world_containers.py`; keep #836's guarded Graph
  bind/deactivate routes and redacted DTO. #826's KnowledgeSpace POST currently
  has no auth guard. ARCHITECTURE ruled on 2026-10-02 that current provisioning
  must remain local-only and use the loopback local-operator bearer guard before
  repository, registry, PostgreSQL, or MIND side effects; fail closed unless
  the local-operator request is proven. This guard does not establish named
  remote-user or per-World authorization, so do not expose the route remotely.
  Before any remote exposure, a separate contract must authenticate the actor
  and authorize provisioning against this exact managed World server-side
  before side effects. Do not infer authority from UI selection, campaign
  identity, or the MIND allocation receipt.
- #826 upgrades `pyproject.toml` and `uv.lock` from MIND #85 to accepted MIND
  #96 merge `619329c2c8586572ffd04558a79b3555c2ca3764`; preserve that pin and
  regenerate the lock consistently. MIND's allocation receipt proves an
  idempotent allocation, not Buddy World ownership or user authorization.
- #826's submitted PostgreSQL integration test was skipped. Its reported
  focused tests are not a zero-skip owning-boundary witness. Activation requires
  the supplied `DMB_J3_PG_ADMIN_DSN`, a clean
  `DMB_J3_DUNGEONMIND_SOURCE` checkout at that MIND #96 merge, and Buddy's
  matching `dungeonmind[postgres]` pin; run
  `tests/integration/test_world_space_binding_postgres.py` with one passed,
  zero skipped. Extend it to prove provisioning preserves an existing v2 Graph
  relation and add route tests proving unauthorized requests have no registry
  or MIND side effects. RAKE accessed no database and ran no tests.

The #826 diff has eight files; its remaining provisioning adapter/service and
tests also assume v1 records and need v2 updates. The refreshed path census found
no Play code-path overlap, but the shared workstream topology is serial:
#826 remains the unresolved prior implementation PR, with no active lease.
The Play implementation cannot dispatch until #826's rework/evidence gates are
resolved and PRIME records its disposition, or PRIME explicitly supersedes it
and updates the topology. Do not run the two implementation slices in parallel.

The refreshed open-PR census at this anchor found #842, #843, and #844 are
one-file BLOCKED handoff PRs; they are design artifacts, not implementation
leases. #842's own one-file PR is the handoff being refreshed here. #843 and
#844 touch only their separate handoff files. #798 is backlog documentation,
#781 is the Build projection-action helper, #763–#765 are Rules work, and
#760–#761 are Canvas handoffs. Their exact changed-file lists do not overlap
the proposed Play implementation code paths. #843 Build and #844 Ingest remain
BLOCKED design handoffs and are not dispatched in parallel. The Play handoff is
a later serial successor only; #826's unresolved predecessor gate still
controls implementation dispatch.

RAKE DUTY's read-only Play audit remains applicable: generic Play turns must
fail before pointer/provider work unless a server-verified World and the exact
selected World-owned Run snapshot resolve; local conversation identity must
include verified World plus Play surface; provider continuation must be
segmented by exact Run and revision; and same-key lookup/provider/commit must
serialize or return a typed conflict. The implementation must prove the actual
deployment process topology before relying on a process-local lock.
This refreshed design grants no write or runtime lease.
## Request and authority contract

Keep the existing `dmb_agent_turn_request_v1` request shape. For a selected managed World Run, the client sends only:

- `surface.surface_id="play"` and a current Play `instance_id`;
- `owner_scope={kind:"world", world_id}` as a locator that the server verifies;
- `primary_work={kind:"run", object_id:run_id, expected_revision:run_revision}`;
- a stable Play `client_thread_id`, fresh `turn_id`, `client_work_state="saved_clean"`, `graph_request={mode:"none"}`, `graph_selection=null`, and the user's message.

Every Play Agent dispatch requires a server-verified managed World and a selected World-owned Run. If no Run is selected, the UI reports that current Run context is absent and keeps Ask unavailable until the operator selects or starts a Run; it does not create a provider pointer. A missing/rejected World or missing Run fails before pointer/provider work. The client does not send campaign identity, native Graph identity, Runbook content, Beat/Scene prose, manifest contents, or a claimed owner. A selected Run always carries its exact locator and revision. Never turn a failed or stale Run resolution into an absent-work request, and never invent a Run from a Runbook, browser pointer, or surface publication.

The generic Agent resolver must fail closed before structured pointer resolution or provider dispatch unless all of the following resolve as one exact snapshot:

1. The managed World is verified server-side and is the owner of the selected World V2 Run.
2. The Run ID exists in that World and its `run_revision` equals the request's expected revision.
3. The Run's exact pinned Runbook artifact, playable revision, immutable WorkRevision ID, and content SHA resolve under that same World and match the Run record.
4. The World Play Run reference manifest has schema `dmb_play_run_reference_manifest_v2`, is sealed, and matches the exact Run/artifact/revision/body-hash binding. Its sealed structure agrees with the pinned Runbook.
5. The current Beat exists in the sealed manifest and exact pinned authored Runbook. A selected Scene, when present, exists and belongs to that Beat.

Reuse or refactor the strict V2 authority core in `services/agent_play_surface_context.py`; do not duplicate A7 checks or use the A7 `/api/live/query` wrapper as the generic resolver. That wrapper intentionally turns invalid optional enrichment into warnings. Generic Play primary work must return a typed stale/rejected/unavailable result and make **zero** pointer-store and provider calls on any failed pin. There is no fallback to another World, latest Runbook revision, campaign V1 identity, or contextless answer after a selected Run fails validation.

Pass only the bounded authored current Beat and optional Scene through the established `AgentSurfaceContext.current_play` seam. Preserve its descriptive-data treatment, clipping, and instruction boundaries. Keep authority IDs, revisions, hashes, manifest internals, provider internals, and complete Runbook text out of model-facing prose. This slice remains graphless; graph intent, native Graph focus, citations, and publication are outside scope.

## Typed response and compatibility

Do not add fields to `dmb_agent_turn_response_v1`: the Pydantic model forbids extras and the existing Plan client validates exact keys. Preserve the exact Index and Plan v1 responses. Play needs a versioned Play-specific response envelope, proposed discriminator `dmb_agent_play_turn_response_v1`; the Play client requires that discriminator and validates all exact keys and values against its submitted request.

PR #848 adds bounded, allowlisted internal runtime phase spans on current main.
Treat trace span names as additive. Keep the typed Play Run receipt separate
from trace telemetry, and do not put World/Run identity, source text, or authored
Play prose into timing spans.

The Play envelope's typed `primary_work` receipt must include:

- `status="resolved"`, `kind="run"`, `object_id=run_id`, and `expected_revision == revision_used == run_revision`;
- `play_basis`: server-resolved `world_id`, `run_id`, and `run_revision`;
- `runbook`: `artifact_id`, `playable_revision`, `work_revision_id`, and `content_sha256`;
- `manifest_binding`: schema version, `run_id`, `playable_artifact_id`, `playable_revision`, `playable_content_sha256`, and `sealed_at`;
- `current_beat`: exact `id` and authored `title`; `current_scene`: exact `id` and authored `title`, or `null`.

The current manifest has no independent revision number or manifest digest. `playable_content_sha256` hashes the pinned Runbook content, not the manifest JSON. Do not invent a manifest hash/revision or relabel the Runbook SHA. If an independent manifest digest is needed, stop for a separately designed source contract.

Echo the resolved basis in a bounded internal pre-provider dispatch/trace receipt so the exact context used is auditable. Do not include full prose, provider response, private session IDs, or internal manifest arrays in the client receipt. The response describes the immutable snapshot actually used; it does not claim the mutable Run remained current after dispatch.

## Conversation isolation and stale-response fences

The user-visible Play conversation is World-owned and surface-specific. Its logical continuity key is the server-verified World, Play surface, and stable `client_thread_id`; it must not rehydrate or reuse a Plan transcript. World identity from browser storage is only a local key; every request verifies it server-side. Keep this logical thread stable across Run A→B.

`run_id` and `run_revision` are per-turn work fences, not the logical conversation key. Segment the provider continuation by verified World, Play surface, thread, exact Run ID, and exact `run_revision`, so a new Run/revision receives no stale provider history or Run tool state. Older turns may remain in the visible local transcript only with their exact Run/revision basis attached; they are not carried into a new provider continuation as current context. The current pointer key omits surface and Run revision, so add a compatible Play-specific binding epoch or equivalent server-owned rotation. Existing Index/Plan v1 pointer keys and persisted bindings must keep their behavior.

Every UI submission captures {world_id, surface=play, client_thread_id, turn_id, run_id, run_revision}. Validate the returned Play receipt against that captured basis and the current UI thread. If selection changes while a request is in flight, either keep the completed response attached to the original turn and visibly labeled with its captured basis, or discard it; never append or present it as the answer for the newly selected Run. A Plan result stays on its Plan thread.

Concurrent requests for one exact World/surface/thread/Run/revision key must serialize across pointer lookup, provider execution, and pointer/transcript commit, or fail with a typed conflict. Prove the deployment's process topology and use a cross-process lock/CAS if a process-local lock is insufficient. The current store lock protects individual JSON-store operations only; it does not cover the provider call.

## Owning-boundary verification

Backend tests must exercise `POST /api/live/agent/turn` with a provider spy and World V2 fixtures. Prove:

- World A success reports and dispatches the exact resolver receipt; World B is rejected before pointer/provider work, including when legacy campaign strings match.
- Missing World, absent primary_work, unbound legacy/campaign Run, wrong/stale Run revision, bad Runbook revision/SHA, wrong World, missing/unsealed/mismatched manifest, invalid Beat, and mismatched Scene all fail before pointer/provider calls.
- Current Beat/Scene prose is the bounded exact pinned content; no graph or citation call occurs.
- Strict Index/Plan response shapes and persisted pointers remain compatible; v1 clients reject the Play discriminator; the Play validator rejects any mismatched/missing receipt field.
- Run A→B, same-Run revision changes, Plan→Play, late results, and same-key concurrent turns obey the isolation and serialization rules above.
- The Play response/consumer tolerates additive internal trace span names; the Run receipt stays separate, and timing spans contain no World/Run identity or authored Play prose.

Mounted Play UI tests use mocked APIs/provider responses and prove Ask remains unavailable without a selected Run; with a selected Run they prove the exact request, validated World V2 selection, surface-specific thread, Play receipt display, Run A→B switch, and stale-response fencing. No live provider, application server, product database, Graph service, or corpus is needed for the implementation PR. After merge, DEMO will run the authorized configured-provider Play conversation witness in the designated demo environment and record the exact World/Run/revision, response basis, and multi-turn continuity without changing runtime ownership.

Proposed focused commands after activation:

```bash
.venv/bin/pytest -q tests/test_agent_turn_route.py tests/test_agent_turn_service.py tests/test_agent_play_surface_context.py tests/test_hermes_session_store.py
cd apps/live-control-ui && npm test -- --run src/playSurface/PlayAgentConversation.test.tsx src/playSurface/PlaySurfacePage.test.tsx src/planSurface/components/agentInteractionHistory.test.ts src/api/liveApi.test.ts
cd apps/live-control-ui && npm run typecheck
```

Record inherited failures honestly. Buddy main has an existing UI typecheck failure at `ThreatPublicationPanel.tsx(553,77): Cannot find namespace 'JSX'`, outside the proposed slice.

## Proposed paths — not an active allowlist

After re-anchoring and PRIME activation, the single implementation PR is expected to use only these paths (new Play files are new paths):

```text
Docs/Plans/HANDOFF-DEMO-play-agent-adoption.md
Docs/Plans/HANDOFF-DEMO-world-owned-play-runs.md
Docs/Roadmaps/ROADMAP-demo.md
apps/live_control_server/models/agent_turn.py
apps/live_control_server/routes/agent.py
apps/live_control_server/services/agent_turn_service.py
apps/live_control_server/services/agent_play_surface_context.py
apps/live_control_server/services/hermes_session_store.py
tests/test_agent_turn_route.py
tests/test_agent_turn_service.py
tests/test_agent_play_surface_context.py
tests/test_hermes_session_store.py
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.ts
apps/live-control-ui/src/planSurface/components/agentInteractionHistory.test.ts
apps/live-control-ui/src/api/types.ts
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/liveApi.test.ts
apps/live-control-ui/src/App.tsx
apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx
apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx
apps/live-control-ui/src/playSurface/PlayAgentConversation.tsx
apps/live-control-ui/src/playSurface/PlayAgentConversation.css
apps/live-control-ui/src/playSurface/PlayAgentConversation.test.tsx
```

This is a proposed set only, not an active allowlist. PR #836 released the Roadmap lease when it merged. The current open-PR path census found no active implementation owner on these proposed Play paths; #843 and #844 remain BLOCKED design handoffs. If implementation needs another path, response/request contract, dependency, database/schema migration, cross-repository change, or shared runtime state, return to PRIME before editing. PRIME must pin the final write allowlist, base, verification, and runtime/process-topology boundaries before implementation.

## Activation checklist

Re-anchor Buddy remote main before any activation decision. At this handoff
revision, main is `c3904bc1e08df689b92d5a0b710b546f77af4600`; #836 and #839 are
merged, #848 is merged, #826 remains paused and unmergeable at its stale head,
and #843/#844 remain BLOCKED. RAKE DUTY's audit identifies unresolved v2
registry, authorization, and zero-skip PostgreSQL gates for #826. The proposed
Play paths have no current open-PR code-path collision, but serial workstream
topology still blocks dispatch behind #826.

PRIME may review this BLOCKED handoff. Before Play can activate, record #826's
resolution/closure or PRIME's explicit superseding disposition/topology; do not
dispatch two implementation slices in parallel. Then PRIME must pin the current
base, exact final write allowlist, inherited failures, verification commands,
and concurrency topology/lock boundary. Runtime use during implementation
tests is not required; any configured-provider post-merge witness still needs
PRIME's designated isolated environment and exact pin. Any changed owner
boundary or contract returns to PRIME before editing. This BLOCKED document
grants no implementation or runtime authority.
