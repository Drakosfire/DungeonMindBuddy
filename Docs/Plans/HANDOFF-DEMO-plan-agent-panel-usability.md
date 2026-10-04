# DEMO handoff: Plan Agent conversation composer usability

## Status and authority

**Status: ACTIVE.** This bounded implementation is authorized by the operator’s DEMO appointment and PRIME’s direct assignment/correction in the current task. The operator’s correction supersedes the earlier two-flow suggestion: one conversation composer, with proposed edits represented as conversation events and reviewed inline.

- Pinned base: DungeonMindBuddy `origin/main` at `6feb3059b2da4d2ec29966ce9723f0effc70108f`.
- Implementation branch: `codex/demo-plan-agent-panel-usability`, rebased onto that main commit after #906 merged.
- This handoff is the authority for the lease on this branch. Commit it before implementation edits; record that handoff commit here after pinning.
- Assigned PR: create one DEMO implementation PR for PRIME review. No merge authority is granted here.
- Scope: one independently useful Agent conversation composer usability capability.

## User outcome

The operator can discuss the saved World Plan or ask DungeonBuddy to propose an edit from the same message composer. The conversation remains the primary interface. A proposal appears inline with its summary, assumptions, before/after review, and explicit Discard / Apply actions. Use the operator-approved copy: “Apply changes your draft. Save keeps the changes.” Apply changes only the mounted Plan draft; the existing Plan Save action commits it. Settings and technical details do not compete with the conversation for attention. If authorization prevents history or Ask, the UI gives the operator a direct next action.

## Invariants and failure cases

Preserve these existing contracts and fences:

1. Plan Ask remains graphless (`graph_request.mode = "none"`, `graph_selection = null`) and uses the exact committed Plan basis. Unsaved editor text is never added to Ask.
2. Edit proposals continue through the existing Plan-action endpoint and server-owned bounded exact-basis conversation context. The UI must not claim that proposals have no prior context, infer automatic tool routing, or add a routing/API contract.
3. Proposal responses must stay correlated to their idempotency key/action and captured mounted draft. Apply remains an explicit review step, visibly changes only the live draft, rejects a stale target/basis, and does not Save. The operator explicitly Saves and reopens to verify durable content.
4. Preserve conversation-pointer checks, thread/surface fences, request recovery envelopes and exact retries, action indeterminacy handling, selection/caret semantics, editor selection precedence, save-in-flight guard, and World history behavior.
5. Local authorization stays memory-only. Never persist, export, log, or put a credential in request bodies. Do not generate/configure credentials or change auth/server behavior.
6. On missing/rejected credentials, history/Ask remain fail-closed. Give the operator a visible path to Settings; do not silently enable submission or weaken recovery.
7. At most one active composer and one controlled message field exist. Intent selection is explicit (`Discuss` or `Propose edit`); switching intent must not silently submit or clear the message. Only proposal intent exposes Plan target selection, and its insertion/replacement semantics remain visible.
8. If any required path, API contract, runtime state, or external service falls outside this lease, stop and return to PRIME before extending scope.

## Exclusive expected-path allowlist

Only this lane may write these paths while ACTIVE:

- `Docs/Plans/HANDOFF-DEMO-plan-agent-panel-usability.md`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` — PRIME's 2026-10-04 extension is limited to adapting mounted UI expectations for the shared composer, Settings, and diagnostics while retaining behavior and safety assertions. It adds no Plan page/runtime or shell ownership.

Do not edit `PlanSurfacePage.tsx`, global styles, API/types, server/auth code, roadmap, dependency manifests/lockfiles, or any operator data. No credential generation, API restart, user-tab reload, provider call, Graph mutation, or Plan mutation is in scope. Runtime port 5202 is reserved to the operator; port 5203 belongs to DOGFOOD and remains untouched.

## Re-anchor and collision audit

At initial activation this lane was based on `main@707ffdfa6da742e3503323908ad4826f692b12fd`. After PRIME published the operator-adopted card roadmap on 2026-10-03, a fresh fetch pinned `origin/main` at `d9b7d1e1ef9c1ad4401e107694260ad4f19455b6`. The 2026-10-04 authority reconciliation advanced `origin/main` to `0f42fec0812655bb37c87b6be9a7fe5741d7f25f`; the exact intervening diff was limited to three authority documents outside this lease. PR #904 was then pushed at `573f338312f77f1315b0069ad13fd542f9708f87`. On 2026-10-04, RAKE PR #906 merged at `6feb3059b2da4d2ec29966ce9723f0effc70108f` after its independently reviewed 50/50 PlanSurfacePage mounted-test repair. That merge released the temporary test-file lease; PRIME explicitly extended this #904 lane to `PlanSurfacePage.test.tsx` for UI-only expectation updates. #886 remains Draft/HOLD at head `717727c33fe70fc154aee291e4397e2d53ac425c` and retains Plan runtime/shell paths. #887 remains isolated at `4b91c09d8a50188dfb1c9ce795358b32d17c02d7`. This branch was rebased onto `6feb3059` before touching the extended test path. The merged World conversation cutover/proposal-context predecessors remain released. An older dirty #900 worktree is historical and must not be copied, reset, cleaned, or edited.

### Topology: parallel-independent

- Concurrent lane: PR #886, exact remote head `717727c33fe70fc154aee291e4397e2d53ac425c`, base `8dc639f06e05cf1809f42ecaba4c791ef21af66b`; navigation-shell paths and its own geometry tests. This slice does not depend on #886’s unmerged behavior and has no shared file/runtime ownership. Keep #886 Draft/HOLD until its own geometry gate is satisfied.
- PR #887 remains the DOGFOOD prototype on its separate prototype path and reserved port 5203; this slice did not use that runtime. PR #869 remains a separate statblock movement-reference lane.
- This lane owns the five paths listed above. The component boundary isolates the work from #886’s shell ownership.
- 5202 and 5203 are operator/runtime lanes rather than implementation branches; both are excluded from this slice’s runtime activity.

## Verification and delivery gates

Before requesting PRIME review:

- Add focused owning-boundary tests for shared composer intent submission, inline proposal review/apply, exact-basis graphless Ask, recovery/auth state, and fail-closed behavior; adapt the existing mounted Plan page expectations without deleting safety or behavior assertions.
- Run the 50-test mounted PlanSurfacePage suite plus both allowlisted conversation test files as one 72-test gate, and run relevant component/type checks. Preserve and classify inherited failures rather than attributing them to this change.
- Inspect the cumulative base-to-head diff and prove the allowlist is respected.
- Capture and inspect the desktop and mobile layouts using a separate non-reserved preview/runtime path. Include Settings, Propose edit, and multiple detached local proposals so their activity cannot conceal the composer. Do not use or alter ports 5202 or 5203.
- Commit the intended changes, push this branch, and open/update the single assigned PR for PRIME. Record exact head SHA, tests, screenshots/evidence, and any remaining limitation below. Merge remains PRIME/operator authority.

## Execution record

- Prior committed handoff record in the rebased ancestry: `8a23fa242e1349974d4112ffed702814cd4eba64`.
- Implementation PR: [#904](https://github.com/Drakosfire/DungeonMindBuddy/pull/904).
- Initial implementation code commit in the rebased ancestry: `841a259991d76df5d9ce7cea4ddee10bdfa6d229`.
- Review correction commit in the rebased ancestry: `a3b722657639bb63251acec043c9be114360d5de`. It orders local proposal events at their verified World conversation sequence boundary, detaches events when that conversation cannot be verified, labels them as local proposals, and lets the narrow panel scroll when Settings is expanded.
- Mounted-test adaptation and layout fix commit: `f54d2466ce5b8ecf04246b31885e0d1e2bc7d230`.
- CSS blob currently served by the preview at `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`: `b7e86e04fef7064fbf7c49941430dc67e639eac3`.
- This execution handoff update is documentation-only; PR #904 metadata records the final exact branch head after this receipt is committed.
- After rebasing onto `6feb3059b2da4d2ec29966ce9723f0effc70108f`, the mounted suite and two focused conversation suites ran together: **72 passed (72)**. Assertions for exact request basis/payload, storage exclusion, response validation, unresolved saves, stale revisions, and Plan-switch isolation remain. A first run was 71/72 because one Plan-switch test expected superseded empty-conversation copy; the expectation was updated to the current UI text and the full gate passed.
- After the final header-spacing CSS fix, the combined mounted plus focused 72-test gate passed again: **72/72**. No safety or behavior assertions were removed.
- PRIME's independent review accepted the previous exact head's 22 focused tests and requested a populated detached-proposal desktop/mobile check. Four proposals were created in a synthetic browser preview and detached across successive mock World conversations. At 1310×900 with Settings expanded and Propose edit selected, the old layout let proposal activity push the composer below the clipped panel. The scoped CSS fix bounds detached activity to a scrollable `min(28vh, 16rem)` region on desktop and lets it flow naturally inside the scrollable panel on mobile. A final 5.5rem header inset separates the fixed Close chat control from New conversation. The updated desktop view fits the full composer (top 500, bottom 884), with New conversation ending at x=1174 and Close chat starting at x=1216. At 390×844 the header controls stack without overlap; a 1,299px panel scroll exposes the full 531.5px composer (top 300, bottom 832). PRIME's independent reviewer accepted the final live layout; the served CSS blob and exact committed PR head are recorded for the final head comparison. The preview uses only loopback UI/API ports 54124/54125 with synthetic data; no credentials, live API, or reserved ports were used.
- Verification:
  - `rtk npm test -- --reporter=dot --maxWorkers=1 src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx` — 22 passed after the proposal-order review correction; the successor UI integration was separately rerun in the combined 72-test gate above.
  - `rtk npm exec vite build -- --outDir /tmp/dmb-demo-pr904-build-20261004` — passed (Vite reports the existing large-chunk advisory). The default output directory could not be cleared because the worktree's existing `dist/assets` is read-only (`EROFS`); the build was directed to fresh `/tmp` output.
  - Final bundle after the scoped layout fixes: `rtk npm exec vite build -- --outDir /tmp/dmb-demo-pr904-build-20261004c` — passed; Vite reports the existing large-chunk advisory.
  - `rtk npm run typecheck -- --pretty false` — blocked by `TS2503: Cannot find namespace 'JSX'` at `src/statblocks/publication/ThreatPublicationPanel.tsx:553`, outside this lease and unchanged by this branch.
  - `git diff --check` — passed.
- Desktop/mobile evidence: captured and inspected a separate synthetic preview on UI port 54124 with a loopback-only mock API on 54125; it used a synthetic World/Plan and an authorization-rejected response. At 1310×900, expanded Settings and the full composer fit in the viewport (composer bottom at y=884). At 390×844 with Settings expanded, the panel reports `overflow-y: auto`; scrolling 239px exposes the full composer and disabled Send button (composer y=541–832, button y=781–818). Screenshots were captured and inspected in the browser session but were not saved as shareable files, so no screenshot path is available. No credential was entered, no user Plan was edited or saved, and the live API or ports 5202/5203 were not contacted.
