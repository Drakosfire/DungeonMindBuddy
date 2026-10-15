# DOGFOOD: truthful shared conversation pending status

Status ACTIVE. PRIME grants exclusive three-path lease and implementation to one
serial repair PR. Base ba2bd03d (fetched origin/main); branch
codex/conversation-pending-status; checkout /tmp/buddy-conversation-pending-status.
No conflicting UI lane. SERVER exclusively owns runtime failure investigation.

Invariant: a saved recovery envelope is not itself a failed or uncertain request.
Hide the recovery panel only while an actual request is in flight; preserve exact
retry/history controls after uncertainty and after reload. Terminal reply wording
uses historical turn surface: Build saved source, Plan Plan, Play Run.

Exclusive write paths:
- Docs/Plans/HANDOFF-DOGFOOD-conversation-pending-status.md
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx

No store, dispatch, idempotency, API, provider, runtime or Graph changes. Preserve
failed live turn; no retry/provider witness. Mounted tests must prove deferred
Build dispatch has no recovery panel while Working, uncertain and reloaded saved
requests retain recovery, and Build historical failure/interruption wording is
correct even when projected onto Plan. Existing Plan/Play wording remains intact.
Verify tests/typecheck/build and cumulative base-to-head diff; commit/push/open one
PR and send exact head to ARCHITECTURE. Merge is PRIME's separate authority.
