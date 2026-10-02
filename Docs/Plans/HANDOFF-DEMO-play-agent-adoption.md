# HANDOFF — DEMO: Play Agent on an exact World Run

**Status:** BLOCKED — bounded design recorded; no implementation lease
**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Design anchor:** Buddy `main@3608663a950cde7472ea942628170f083e533b14`
**Topology:** serial successor. PRIME directed that this handoff remain BLOCKED until the #836 binding/authority review and #839 diagnostics gate settle. Re-anchor and request a pinned ACTIVE lease after both gates. No implementation or runtime lease is active.

## User transition

From a managed World with a selected World-owned Play Run, the operator can ask DungeonBuddy about the current moment of play and continue a surface-specific Play conversation. Each answer must use the exact selected Run snapshot and its pinned authored material. A late response or a change of Run must never make an answer about Run A appear to describe Run B.

This is one Buddy product capability: adopt the generic Agent turn contract on Play. It does not add Graph retrieval, citations, mutations, a new Agent framework, or changes to Run ownership.

## Current evidence and gates

Buddy #820 completed the World PlayRun C2 UI migration at `bfa741261e715eadb48d873f87fccc1764417da8`; its lease ended at merge. The generic POST /api/live/agent/turn request permits Play and Run locators, but the current work resolver accepts only Plan and returns work_kind_unresolved for a Run. Play has no Ask plugin. Its PlaySurfacePublisher builds legacy A7 publication context from campaign V1 records only, so that publication is not authority for a World V2 Agent turn.

The source contract review was performed against `012ff01acc4e490601f4993644903689af2708c4`. Buddy main was at `92d5ff9c35778a97527546aa9aa15ca8fb7290af` when evaluation-only PR #840 merged; current main and this design anchor are `3608663a950cde7472ea942628170f083e533b14`. The exact comparison from the prior anchor contains three Hermes-only commits and four paths: `Docs/Plans/HANDOFF-HERMES-host-latency.md`, `evals/hermes_tuning/README.md`, `evals/hermes_tuning/artifacts/host-latency-20261002T051413Z.json`, and `evals/hermes_tuning/run_host_latency.py`. No Agent or Play contract changed.

Buddy #836 is open at `18c5de19cb481742206f7c8c3cdfdc97a9097f77` and owns World binding paths plus ROADMAP-demo.md. Buddy #839 is open at `fccb75c5ce5392681bdbaf14beb15b79be220ecc`. Paused open #826 overlaps #836's World container/registry lease and remains inactive. GitHub changed-file lists at the exact #836 and #839 heads show no overlap with the proposed generic Agent resolver or Play page paths; #836 does not change the shared AgentInteractionChrome. PRIME directed DEMO to prepare this design BLOCKED and activate serially only after #836 and #839 settle, followed by a fresh re-anchor. PRIME also confirmed that this first Play slice requires an exact selected World-owned Run: with no Run, Ask stays unavailable and general World/Play chat is deferred to a separate capability.

RAKE DUTY's read-only audit found three current hazards. First, the generic route rejects Run primary work before dispatch but currently permits a Play request with no owner and no primary work to reach pointer/provider dispatch; strict World V2 Play checks are used only by the legacy query path. Second, the Play V2 publication omits World ID and its generic UI fallback uses a synthetic Play scope, so local threads can be shared across Worlds unless the new Play conversation explicitly scopes its local namespace by verified World and surface. Third, the structured pointer key includes owner, work kind/ID, and client thread ID but omits surface and Run revision; the store lock protects individual JSON operations, not the resolve-provider-commit sequence, so same-key turns can race. The proposed contract below addresses these issues. PRIME owns activation and final lease. This document grants no write lease.

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

This is a proposed set only. If the implementation needs another path, response/request contract, dependency, database/schema migration, cross-repository change, or shared runtime state, return to PRIME before editing. In particular, `ROADMAP-demo.md` is still in #836's open lease and cannot be changed until that lease ends.

## Activation checklist

PRIME must confirm that the #836 binding/authority review and #839 diagnostics gate have settled, then re-anchor main, relevant open PRs, and active leases. PRIME reviews this exact BLOCKED handoff and activates one serial implementation PR with a fresh base, explicit path/runtime lease, inherited failures, exact verification commands, and PR topology. RAKE DUTY's read-only Play findings and the exact GitHub changed-file checks above are part of the design evidence. Any changed owner boundary or contract returns to PRIME before editing. No implementation or runtime start is authorized by this BLOCKED document.
