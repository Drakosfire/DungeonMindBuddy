# DOGFOOD: truthful shared conversation pending status

Status COMPLETED. PR #1181 merged at
977eabee4ec6c96ad7e68b3f9704a6a3fc1aabf8 after ARCHITECTURE cycle 1 ACCEPTABLE
on exact head f870bdf84808451316119a4e8c64e7b17d5b3de2. Bugbot reported no issues.
The exclusive three-path implementation lease is released. PRIME authorized one
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

## Settlement evidence and runtime boundary

All 37 mounted shared conversation tests passed independently in review. Author
TypeScript check and production build passed; inherited React act and bundle-size
warnings remain. GitHub status list was empty; no CI-green claim. No failed live
turn was retried and no provider call was made for this UI repair.

The serving runtime remains a8a19345 until separately verified adoption. This
presentation repair does not resolve the failed Agent execution. Coordinate any
optional matched rollout with SERVER only after its current failed-turn diagnosis;
do not interrupt an uncertain provider attempt.
