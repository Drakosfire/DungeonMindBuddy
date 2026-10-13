# DOGFOOD: grounded Plan proposal review

Status: ACTIVE. Authorized by the operator's continuing dogfood work and the bounded PRIME dispatch after PR #1108 merged.

Authority: Buddy `main` at `0b10f9554999818142350511fdc84a263bebfcd9` (GitHub `main`, verified 2026-10-12). Branch `codex/dogfood-grounded-proposal-review` in isolated worktree `/home/drakosfire/.codex/worktrees/grounded-proposal-review/DungeonMindBuddy`. Serial PR against `main`; PRIME owns review and merge. Open PRs checked before activation: no active UI lease on the files below. The live 5202/8000/7860 checkout at `/tmp/buddy-sourced-plan-edit-consultation` remains read-only.

Exclusive expected write set:

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- This handoff

No API, SERVER, APP, schema, storage, reader, runtime, corpus, or provider changes. No listening ports, retained databases, or external state are owned by this lane.

Invariant: A saved Plan edit proposal's human-readable World claims and pinned evidence appear with its Before/After review only when the current World conversation action projection proves the same action, origin, pointer, Plan basis, draft, selection, and result. The claim text, citation state, and source target must agree. The view distinguishes a passage Buddy actually read from a Graph citation whose passage was not opened. Opening a source uses the existing pinned reader. Missing or mismatched support is shown honestly and cannot borrow another action's evidence. Historical proposals remain read-only after reload or conversation change.

Failure cases to verify: late or stale action projection; wrong action, World, conversation pointer, Plan basis, draft, or selected text; a citation without a matching claim or target; a source read that fails or returns mismatched authority; a New Conversation switch; a legacy proposal with no consultation; and a saved proposal whose review expired after reload.

Verification: `npm test -- src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx` passed (197 tests); `npm run typecheck` passed; `git diff --check` passed. Mounted coverage checks matched proposal facts beside Before/After, source-open success and failure, cross-action/scope rejection, reload/New Conversation, and draft-only Apply. Review the cumulative base-to-head diff before merging; the final PR head is recorded in the PR.
