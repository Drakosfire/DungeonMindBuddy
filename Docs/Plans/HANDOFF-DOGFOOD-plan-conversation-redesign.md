# DOGFOOD — Rebuild the Plan conversation presentation

Status: ACTIVE implementation slice, authorized by the user and PRIME on 2026-10-07. No merge authority.

Branch: `codex/dogfood-plan-proposal-scope` (PR #1007).

Reviewed presentation source pin: `aeda767c6c9dd785ce2e4344e17615e9efd439c7`. Current-scene capture published at `dcd5bccb18707735bf408b35e64b111f7043ee50` received ARCH source PASS and DOGFOOD selected-scene authoring/Save/reload PASS. The current conversation reset/immediate-echo logic is code `e255f206cf6ba5fb4338cbd99b54b51b4f11f76d`, pending independent review and presentation integration. Preparation merge `186c497687d59d435ce57e272967234134da8f7c` preserves dcd ancestry and accepted `main@eded41e68af6e5efb2fefcb6ee611374ee10a3a7`. Page/helper/tests and both CSS blobs remain unchanged from dcd. Obtain the final publication head from PR #1007.

Topology: #1007 remains the single production adopter PR against main. APP-STATE's completed temporary reconciliation covered the page test and handoff. PRIME transferred the conversation TSX, owning history test, and this handoff to DEMO for the bounded notice repair and publication settlement. The prepared merge preserves all published #1007 ancestors, including `c842648c`; publication uses a normal guarded fast-forward of the existing branch. The original DOGFOOD checkout remains untouched. Historical preview evidence below describes its original candidate rather than the current runtime. #979 remains historical context without an active write lease.

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

APP-STATE reconciliation and the seven-path current-scene capture transfer are completed predecessors. PRIME's current DEMO logic lease is only `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx` and `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`, plus this document for the authorized publication settlement. After the exact-head handback, this document transfers to DOGFOOD. DEMO retains the controller/test reservation for wiring callbacks/slots/context after DOGFOOD pins the presentation component API; DOGFOOD must not edit the controller concurrently. DOGFOOD's presentation-only review/dock/adapter work uses its separately pinned lane and write set. Existing #1007 remains the serial production adopter and operator-inspection hold remains binding. No runtime change is authorized by this packet. No API types, strict validators, schema, backend/provider, shared Graph policy, lockfiles, service, or database writes are leased.

## Verification and handback

Verification at candidate code head `94f078c2b5e15399870fed67a3dd82955d355bcf` (before the documentation-only handoff update):

- `npm --prefix apps/live-control-ui test -- src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx --reporter=dot`: **107 passed, 0 failed**. Includes the exact-ID Graph recovery case across a changed Plan basis; it verifies the saved request stays unresent, exact bytes remain in storage, recovery is inspectable under its disclosures, and the active conversation is not contaminated by the recovered answer.
- `npm --prefix apps/live-control-ui run typecheck`: passed.
- `npm --prefix apps/live-control-ui run build -- --outDir /tmp/plan-chat-rebased-dist`: passed; 671 modules transformed. Vite reports the existing large-chunk warning. Build artifacts were directed to `/tmp`.
- Cumulative `git diff --check 0c83cb7a...HEAD`: passed before the final handoff text update. The feature-base tree and #1009 merge tree were compared and have no diff.
- CUA visual inspection of the 5204 candidate at 701×900: the saved Plan remains above a resizable bottom Buddy dock; the composer is pinned at the bottom. The dock currently shows a local authorization rejection and disables the composer; no Agent request was sent. The screenshot is visible inline in the Codex thread but has no exported local path. This proves the rendered failure state and layout only, not a successful Agent conversation.

Operator runtime 5202 remains untouched. The local `npm ci --offline` attempt earlier failed because the cache lacks `react@19.1.0` (`ENOTCACHED`); the existing app dependencies were available in the candidate worktree for the passing checks above. PR #1007 remains draft pending independent review and operator inspection. No merge or production adoption is claimed or authorized here.

Historical publication failure (superseded by the settlement below): local branch head `77cc1acf` contains the verified code plus this handoff update. The existing PR #1007 still points to remote head `b4cd1a6f` and its former #1008 base because three guarded Git pushes returned GitHub `Internal Server Error`; a GitHub blob API fallback also returned an internal error. The PR was re-read after the failed pushes and remained unchanged. Do not represent this local candidate as published until the remote head/base and PR body are verified.

## Publication settlement and remaining inspection

GitHub publication recovered after service errors. The reviewed code is published at the pin above; no merge, rollout, successful connected conversation, or operator acceptance is claimed here. The earlier offline dependency-cache failure is historical and superseded by the verified dependency setup and final checks.

Intent routing is a heuristic with a per-message correction control, not complete semantic intent understanding. Indirect requests such as “This scene needs a location,” “Could this include a sensory detail?” and “Use your second idea” default to discussion. Keep this limitation explicit during inspection and evaluate whether the correction is discoverable; do not describe the candidate as fully natural conversational editing.

The 701×900 preview showed the document above the bottom dock and a pinned composer, but local authorization was rejected there and no Agent request was sent. The real 5202 discussion → edit → review/Apply → Save/reopen witness and operator design inspection remain outstanding after coordinated rollout.

## Composer clearing follow-up — 2026-10-07

The operator asked that a sent message leave the composer clear. Both Discuss and Propose capture the exact raw composer value at dispatch, normalize only the request text, and clear after a valid successful response only when the field still matches the submitted snapshot. Failed or uncertain requests retain the original draft; changed composer content is not cleared. The composer tests cover trimmed input on successful Discuss and Propose, preservation of a newer draft after each succeeds, and draft retention for uncertain Discuss recovery. The textarea remains disabled while a proposal is composing.

Verification after this follow-up: WorldPlanAgentConversation.worldHistory.test.tsx 109/109 passed; UI typecheck passed; production build passed (671 modules, existing large-chunk warning); git diff --check passed. Runtime 5202 still needs an identified rollout and operator recheck; this commit does not claim it is current.

## APP-STATE current-main test reconciliation — 2026-10-07

The combined candidate initially reproduced 11 failing PlanSurfacePage tests (52 passing), while all 109 owning conversation tests passed. The two completed-answer failures were fixture contract gaps: policy requests received V1 response/history rows without a Plan context completion. They were not missing text matchers. The fixture now returns a complete V2 policy response, a canonical SHA-256 sealed receipt with the exact submitted World/Plan basis and target, and V3 history with the server's UUIDv5 idempotency correlation. Persisted primary revision metadata matches that receipt. Web Crypto is installed in the jsdom test harness so the existing production validator checks the actual digest. The original answer text, questions, scope, basis, storage exclusions, target capture and pending request fences remain asserted. Plan-only requests retain their V1 response fixture.

Selectors follow the reviewed presentation: compact Question/Change target chips, the source/basis disclosure, the stable Send message accessible name during saving, and the new empty conversation text. The exact policy request shape now includes the default Plan + World policy rather than pretending this path is Plan-only.

Verification on exact main `6837baa9` plus the reviewed #1007 blobs and this test delta:

- `npm --prefix apps/live-control-ui test -- src/planSurface/PlanSurfacePage.test.tsx src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx --reporter=dot`: **172 passed, 0 failed** (63 page tests + 109 conversation tests). Evidence: `/tmp/app-state-1007-owning-fixed-3.log`.
- `git diff --check`: passed. The cumulative change has the original five #1007 paths plus only `PlanSurfacePage.test.tsx`.
- All three production UI blobs are unchanged from `aeda767c`: conversation TSX `86cebbbb55d22b9da01ccdd7cab0b94fc66f349d`, conversation CSS `01fff6ce457f3b92a90d4ac24791c4cd49b1be4f`, dock CSS `34b104cada058c14930e317cef90e9af91840b72`.

The combined run emits React act warnings for existing async page interactions; it has no test failures. Only the two owning suites were run for this reconciliation. Earlier typecheck/build and visual evidence remain tied to their recorded candidates. Independent review of the publication head and the real connected operator discussion → edit → review/Apply → Save/reopen witness remain required. PR #1007 stays draft; no merge, rollout, or operator acceptance is claimed.

## DEMO confirmed-Ask notice settlement — 2026-10-07

The server-confirmed Ask notice previously continued to say history was refreshing after matching history had loaded. Reviewed code `edd0daa7d53b7491ed98ec281be2f2d9dd5a0d44` changes that notice to a completed status only after validated history matches the submitted World, conversation, request, original target, and committed Plan basis. Graph requests reuse the strict V3 idempotency correlation and receipt/completion checks. A history refresh failure is distinguished from the already confirmed Ask. Superseded history generations and another current notice cannot be settled by the old refresh. The original target/basis attribution remains intact, and no uncertain request is resent.

Preparation base `d6d3bd4192cd3fe3b98e87f23b74444ae483c8a0` merges `main@049ecb5f` with portable #1007 `c842648c`. The notice commit changes only the conversation TSX and owning history test. Independent PASS was received for that exact code commit: **113/113 conversation tests**, UI TypeScript, and diff checks passed. The inherited **63 page tests** passed on `c842648c`; they were not rerun for this notice repair. Earlier build and visual evidence remains tied to its recorded candidates.

Current production blobs: conversation TSX `ecd283463a9a4d2e9794e4086764c0d2a0805d21`, conversation CSS `01fff6ce457f3b92a90d4ac24791c4cd49b1be4f`, dock CSS `34b104cada058c14930e317cef90e9af91840b72`. Owning conversation-test blob: `514f2239c773f409f960f1c0f3e48981a08395f8`.

PRIME authorized publication after reporting the actual full `./run` startup/stop checkpoint passed for frozen SERVER `4e4bb74a`, DMS `c386`, and Core `5d`. That checkpoint is operational evidence; this notice publication makes no live adoption or operator usefulness claim. #1007 remains draft under the operator-inspection merge hold. The connected discussion → edit → review/Apply → Save/reopen witness and design inspection remain pending.

## DEMO explicit-proposal routing repair — 2026-10-07

The observed input began “For this disposable synthetic Plan only, propose appending exactly this line…” and incorrectly routed to discussion. Reviewed code `81e1c25c0949b9eb5ac4793f378b445ee7f15643` extends the existing anchored routing rule to consume one introductory scope clause and recognize explicit proposal edit actions, including appending. Bare brainstorming such as “Propose three ways to resolve the siege” remains discussion. Nearby questions and hypothetical wording remain discussion; per-message correction remains available in both directions. This remains a bounded heuristic, not complete model intent understanding.

The repair changes only the conversation TSX and owning history tests atop published `490e7077`. **123/123 conversation tests**, UI TypeScript, and cumulative diff checks passed. PRIME independently passed the exact code after re-reading the raw source and executing the routing rule. No suite was repeated for the documentation-only settlement. Reviewed blobs: conversation TSX `3e928a5cc2d0b02a7a48b17cda6fd279a761b5ad`; owning conversation test `019daa219784583850d27c6b0400837debcac9d5`. CSS and inherited page-test evidence remain unchanged.

Automatic routing does not select an EditTarget: manual Select for Edit is still needed for the intended card body. Existing target capture, proposal review, Apply, and separate Save guards remain intact. PRIME reported the actual Goal 4 UI checkpoint completed: the old Run pin survived a later Plan edit and the real Run was restored. Final read-only preservation proof and operator inspection remain pending. That checkpoint is attributed runtime evidence, not evidence that this routing repair was deployed. Publication updates existing #1007 only; no runtime change, merge, or operator usefulness acceptance is claimed.

## DEMO current-scene conversational edit capture — 2026-10-07

DOGFOOD's exact retry on `b86fb0e0` passed routing but captured only a caret, despite a current Ask scene. The operator did not Apply or Save the incorrect proposal. PRIME authorized one bounded target capability on existing #1007: explicit editor range takes precedence over a manual Edit target, then the current Ask scene becomes default scope. A collapsed caret is not explicit selection. Scene focus supplies identity; no wording heuristic chooses a scene. Current label is visible before sending and the review names the captured label and exact ID with actual Before/body text.

Code `94a00f5f8017086f857ed23f4b8772f0e664ec2f` reuses the existing `replace_playable_body` contract, exact parsed body range, canonical body/hash, committed base revision/digest, working draft/hash, and editor/draft/selection generations. A local capture-source field guards recapture mode. Missing, duplicate, or stale scene capture fails; scene/basis/mode changes reject Apply. Scene-mode requests and Apply re-read the committed basis before provider/mutation and recheck current fences after the read. Protected marker/reference and admission guards are unchanged. With no active scene, ordinary non-scene caret behavior remains; a bounded current/selected-scene reference without a target is rejected, while “Add a new scene here” retains caret authoring.

Verification: the three owning suites passed **247 tests** (67 page, 125 conversation/history, 55 edit helper) on unchanged final production code. After tightening only fixture wording to DOGFOOD's exact input and adding actual range/hash assertions, **8 amended focused cases passed** (114 skipped); no unchanged full-suite repeat. UI TypeScript and cumulative diff checks passed. Mounted tests cover unchecked Select for Edit, current scene's full Before/body/hash, actual Apply preserving both markers and the other scene, editor selection precedence, current-scene review retirement, stale committed basis before provider, and stale committed basis before Apply. Helper cases cover missing/duplicate/stale capture and basis/scene/mode/stale recapture rejection with unchanged editor bytes. Existing React act warnings remain; no test failures remain. Logs: `/tmp/dmb-scene-target-verified.log`, `/tmp/dmb-scene-amended-focused.log`.

Production blobs: page `47215d5b88f588ad235907291c33afa2f519e1a0`; controller `62aab4838b9903528761a28a56cb3a0482047164`; edit helper `a74ad971c62f56b02be4425d05bd198e31f9e51c`. The delta from `147765aa` stays within the seven leased paths; the cumulative main049 diff adds the page and edit helper/test to the prior six paths, retaining both unchanged CSS blobs and no API/backend/runtime delta. This supersedes the manual-EditTarget requirement above for the default current Ask scene only. Independent review, DOGFOOD before/after-target QC, rollout, and operator acceptance remain pending; publication does not deploy or merge this repair.

## Conversation reset and immediate submitted-message echo — 2026-10-07

PRIME subsequently reported ARCH PASS on exact dcd/tree93b565 and DOGFOOD PASS for selected-scene authoring with durable Save/reload. Operator inspection remains pending. New operator findings authorized fresh New Conversation behavior and immediate display of Discuss/edit messages. The observed HTTP401/pending reset is assigned to APP-STATE for authentication diagnosis; this logic does not mask a failed reset as success.

Code `e255f206cf6ba5fb4338cbd99b54b51b4f11f76d` requires a validated fresh active-conversation/pointer response before retiring the active local proposal thread and clearing the visible transcript. Earlier transcript pages cannot repopulate the confirmed fresh conversation. Old durable history, local proposal bytes and original order attribution remain preserved in detached local activity; the fresh transcript survives remount. Failed reset preserves the transcript, composer draft, and exact CAS command envelope. Replaying a confirmed command after storage cleanup failure does not retire the fresh thread twice.

Submitted Discuss/edit text appears before asynchronous committed-basis preparation or target capture, with truthful pending state. Echoes belong to the original World/document/conversation or initial pointer, disappear when matching durable history/local proposal arrives, and cannot migrate to an unrelated conversation. Existing late-response, idempotence, target capture and uncertain-request recovery guards remain. Following the latest message respects readers viewing older messages. There is no duplicate model post or provider/runtime/operator-tab action.

Verification: **129/129 owning conversation tests** passed on final production code. One subsequently added cleanup-replay case passed in a focused run (**1 passed, 129 skipped**); no full130 run is claimed. Final TypeScript and cumulative diff checks passed. Logs: `/tmp/dmb-fresh-conversation-verified.log` and `/tmp/dmb-reset-replay-test.log`. Controller blob `bc64fd257352ed2966077a6b7b9bb93f9d53dd0e`; owning test blob `430dfd747941fef575336378fb2260559d0b5154`. Unchanged current-scene page/helper/test/CSS acceptance carries only by exact byte equality. The maineded cumulative diff contains the same nine UI/test/handoff paths, with no backend revert.

This settlement transfers this handoff to DOGFOOD after exact-head handback. Primary chat clarity, quiet chrome/fullscreen, and rendered inline proposal presentation belong to DOGFOOD's separate presentation work. Fullscreen must retain the mounted editor/composer/transcript and drafts. DEMO will wire the pinned component API through its reserved controller/test paths; edit ownership must be serialized. Independent review of this logic, presentation integration, DOGFOOD QC, and operator acceptance remain pending. Neither publication nor document transfer authorizes deployment or merge.
