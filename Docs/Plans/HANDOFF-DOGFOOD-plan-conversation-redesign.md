# DOGFOOD — Rebuild the Plan conversation presentation

Status: ACTIVE implementation slice, authorized by the user and PRIME on 2026-10-07. No merge authority.

Branch: `codex/dogfood-plan-proposal-scope` (PR #1007).

Published source pin: `01ebe8ef6079b5e234aba88fba50686f1ff13569`, against `main@228bbe6c4b41cce9323d71614153b7e69c6f0c2d`. Its tree equals the owner’s final local `30ea09ffd7647cd27398c9658aa28cae331a8710`; the functional code is unchanged from independently reviewed `94f078c2b5e15399870fed67a3dd82955d355bcf`. Later publication settlement is documentation only; obtain the latest head from PR #1007.
Topology: #1008 and #1009 are merged. #1007 is the single production adopter PR against main; its five-path diff contains no backend or SDK reversion. The first inspection release deliberately uses reviewed #1009 base plus this UX increment, excluding #1010’s Core dependency upgrade. It is not a claim that the runtime equals current main. #979 remains historical context without an active write lease.

## Outcome

Replace the Plan conversation’s record-heavy, multi-box reading path with a compact conversation presentation in the existing resizable bottom dock. Keep the saved Plan as the primary workspace. Show the latest user/assistant exchange first; collapse earlier exchanges, local-only proposals, provenance, Graph receipts, traces, and recovery records until opened. Keep the composer visible and usable at the bottom, with one input and automatic Discuss/Propose intent routing.

## Invariants

- Keep `WorldPlanAgentConversation` as the sole controller for durable World history, request identity, context capture, recovery, proposal review/apply, and exact target fences.
- Preserve `isWorldPlanGraphCompletion`, `isWorldPlanGraphExecution`, `isWorldPlanContextProjection`, the strict receipt checks, and their imported types. No source IO, provider reroute, Graph write, schema, or backend change.
- Failed or interrupted turns get short human-readable status in the conversation; precise lifecycle, provenance, target receipt and Graph evidence remain inspectable in turn details.
- Do not automatically repost uncertain requests. Preserve exact saved request bytes, ID, refresh-only confirmation, and existing retry rules.
- Editing language routes to the existing proposal/review/apply flow. Questions route to the existing durable discussion flow. No classifier policy changes to Agent/server APIs.
- Default context control starts at “Plan + World” and resets when the verified World changes. The user asked to remove the per-question Graph checkbox gate. Keep Plan-only available as an explicit scope switch; do not claim the known Graph completion failure is repaired.
- Keep the resizable dock and its single composer. Do not add another chat state/store or move the composer out of the existing dock.
- Citation presentation must not claim source text was opened unless the validated server contract can represent that state. The stacked SERVER V2 contract supports the boolean only when source-read IDs match the validated reads; preserve the strict V1 false and V2 binding checks.
- In dock presentation, arriving replies must not pull a reader away from older turns. Show a small “New reply · jump to latest” affordance and move only when the reader chooses it.
- Keep classifier routing as the default, but expose a compact correction for the current message so an ambiguous request can be switched between question and Plan change without adding a second composer or persistent mode state.

## Exclusive expected write set

Modify:

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`
- `apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.css`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`

Create:

- `Docs/Plans/HANDOFF-DOGFOOD-plan-conversation-redesign.md`

No other paths are leased. Do not edit API types, validators, adapters, schema, backend/provider, shared Graph policy, lockfiles, runtime services, or database state in this slice. If a source-read status branch is required, SERVER owns that contract and can consume or narrowly lease its phrase after the type/validator lands.

## Verification and handback

Verification at candidate code head `94f078c2b5e15399870fed67a3dd82955d355bcf` (before the documentation-only handoff update):

- `npm --prefix apps/live-control-ui test -- src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx --reporter=dot`: **107 passed, 0 failed**. Includes the exact-ID Graph recovery case across a changed Plan basis; it verifies the saved request stays unresent, exact bytes remain in storage, recovery is inspectable under its disclosures, and the active conversation is not contaminated by the recovered answer.
- `npm --prefix apps/live-control-ui run typecheck`: passed.
- `npm --prefix apps/live-control-ui run build -- --outDir /tmp/plan-chat-rebased-dist`: passed; 671 modules transformed. Vite reports the existing large-chunk warning. Build artifacts were directed to `/tmp`.
- Cumulative `git diff --check 0c83cb7a...HEAD`: passed before the final handoff text update. The feature-base tree and #1009 merge tree were compared and have no diff.
- CUA visual inspection of the 5204 candidate at 701×900: the saved Plan remains above a resizable bottom Buddy dock; the composer is pinned at the bottom. The dock currently shows a local authorization rejection and disables the composer; no Agent request was sent. The screenshot is visible inline in the Codex thread but has no exported local path. This proves the rendered failure state and layout only, not a successful Agent conversation.

Operator runtime 5202 remains untouched. The local `npm ci --offline` attempt earlier failed because the cache lacks `react@19.1.0` (`ENOTCACHED`); the existing app dependencies were available in the candidate worktree for the passing checks above. PR #1007 remains draft pending independent review and operator inspection. No merge or production adoption is claimed or authorized here.

Publication status: local branch head `77cc1acf` contains the verified code plus this handoff update. The existing PR #1007 still points to remote head `b4cd1a6f` and its former #1008 base because three guarded Git pushes returned GitHub `Internal Server Error`; a GitHub blob API fallback also returned an internal error. The PR was re-read after the failed pushes and remained unchanged. Do not represent this local candidate as published until the remote head/base and PR body are verified.

## Publication settlement and remaining inspection

GitHub publication recovered after service errors. The reviewed code is published at the pin above; no merge, rollout, successful connected conversation, or operator acceptance is claimed here. The earlier offline dependency-cache failure is historical and superseded by the verified dependency setup and final checks.

Intent routing is a heuristic with a per-message correction control, not complete semantic intent understanding. Indirect requests such as “This scene needs a location,” “Could this include a sensory detail?” and “Use your second idea” default to discussion. Keep this limitation explicit during inspection and evaluate whether the correction is discoverable; do not describe the candidate as fully natural conversational editing.

The 701×900 preview showed the document above the bottom dock and a pinned composer, but local authorization was rejected there and no Agent request was sent. The real 5202 discussion → edit → review/Apply → Save/reopen witness and operator design inspection remain outstanding after coordinated rollout.

## Composer clearing follow-up — 2026-10-07

The operator asked that a sent message leave the composer clear. Both Discuss and Propose capture the exact raw composer value at dispatch, normalize only the request text, and clear after a valid successful response only when the field still matches the submitted snapshot. Failed or uncertain requests retain the original draft; changed composer content is not cleared. The composer tests cover trimmed input on successful Discuss and Propose, preservation of a newer draft after each succeeds, and draft retention for uncertain Discuss recovery. The textarea remains disabled while a proposal is composing.

Verification after this follow-up: WorldPlanAgentConversation.worldHistory.test.tsx 109/109 passed; UI typecheck passed; production build passed (671 modules, existing large-chunk warning); git diff --check passed. Runtime 5202 still needs an identified rollout and operator recheck; this commit does not claim it is current.
