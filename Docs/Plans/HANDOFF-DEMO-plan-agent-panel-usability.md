# DEMO handoff: Plan Agent conversation composer usability

## Status and authority

**Status: ACTIVE.** This bounded implementation is authorized by the operator’s DEMO appointment and PRIME’s direct assignment/correction in the current task. The operator’s correction supersedes the earlier two-flow suggestion: one conversation composer, with proposed edits represented as conversation events and reviewed inline.

- Pinned base: DungeonMindBuddy `origin/main` at `0f42fec0812655bb37c87b6be9a7fe5741d7f25f`.
- Implementation branch: `codex/demo-plan-agent-panel-usability`, rebased onto that main commit before the latest review correction.
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

Do not edit `PlanSurfacePage.tsx`, `PlanSurfacePage.test.tsx`, global styles, API/types, server/auth code, roadmap, dependency manifests/lockfiles, or any operator data. No credential generation, API restart, user-tab reload, provider call, Graph mutation, or Plan mutation is in scope. Runtime port 5202 is reserved to the operator; port 5203 belongs to DOGFOOD and remains untouched.

## Re-anchor and collision audit

At initial activation this lane was based on `main@707ffdfa6da742e3503323908ad4826f692b12fd`. After PRIME published the operator-adopted card roadmap on 2026-10-03, a fresh fetch pinned `origin/main` at `d9b7d1e1ef9c1ad4401e107694260ad4f19455b6`. The 2026-10-04 authority reconciliation advanced `origin/main` to `0f42fec0812655bb37c87b6be9a7fe5741d7f25f`; the exact intervening diff is limited to `Docs/Plans/HANDOFF-DEMO-plan-navigation-shell.md`, `Docs/Plans/STEWARDS-HANDOFF-demo.md`, and `Docs/Roadmaps/ROADMAP-demo.md`, all outside this lease. Rechecked open PRs: #904 was open at `b59abf0784301d71d00cf002c2a3b697f0216a46`; #886 remained Draft/HOLD at `717727c33fe70fc154aee291e4397e2d53ac425c`; #887 remained on its separate prototype paths at `4b91c09d8a50188dfb1c9ce795358b32d17c02d7`. #886's `PlanSurfacePage.test.tsx` lease is transferred to PRIME's mounted-harness repair worker; this lane did not touch it. This branch was rebased onto `0f42fec0` before the latest correction. The merged World conversation cutover/proposal-context predecessors remain released. An older dirty #900 worktree is historical and must not be copied, reset, cleaned, or edited.

### Topology: parallel-independent

- Concurrent lane: PR #886, exact remote head `717727c33fe70fc154aee291e4397e2d53ac425c`, base `8dc639f06e05cf1809f42ecaba4c791ef21af66b`; navigation-shell paths and its own geometry tests. This slice does not depend on #886’s unmerged behavior and has no shared file/runtime ownership. Keep #886 Draft/HOLD until its own geometry gate is satisfied.
- PR #887 remains the DOGFOOD prototype on its separate prototype path and reserved port 5203; this slice did not use that runtime. PR #869 remains a separate statblock movement-reference lane.
- This lane owns the five paths listed above. The component boundary isolates the work from #886’s shell ownership.
- 5202 and 5203 are operator/runtime lanes rather than implementation branches; both are excluded from this slice’s runtime activity.

## Verification and delivery gates

Before requesting PRIME review:

- Add focused owning-boundary tests for shared composer intent submission, inline proposal review/apply, exact-basis graphless Ask, recovery/auth state, and fail-closed behavior.
- Run both allowlisted conversation test files and relevant component/type checks. Preserve and classify inherited failures rather than attributing them to this change.
- Inspect the cumulative base-to-head diff and prove the allowlist is respected.
- Capture and inspect the desktop and mobile layouts using a separate non-reserved preview/runtime path. Do not use or alter ports 5202 or 5203.
- Commit the intended changes, push this branch, and open/update the single assigned PR for PRIME. Record exact head SHA, tests, screenshots/evidence, and any remaining limitation below. Merge remains PRIME/operator authority.

## Execution record

- Authority handoff commit on the latest rebased branch: `cea37b3a131b27f926f599758ab86e8dbc3b6abc`.
- Implementation PR: [#904](https://github.com/Drakosfire/DungeonMindBuddy/pull/904).
- Initial implementation code commit on the latest rebased branch: `0363c939ed11e8132c212a2f35315b3217f73b9f`.
- Review correction commit on the latest rebased branch: `36790d89228424df418f84c823b7edb6e5abf46f`. It orders local proposal events at their verified World conversation sequence boundary, detaches events when that conversation cannot be verified, labels them as local proposals, and lets the narrow panel scroll when Settings is expanded.
- The later handoff receipt is documentation-only; PR #904 metadata records the final branch head.
- Verification:
  - `rtk npm test -- --reporter=dot --maxWorkers=1 src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx` — 22 passed after the review correction; the only later rebase change was the three authority documents listed above.
  - `rtk npm exec vite build -- --outDir /tmp/dmb-demo-pr904-build-20261004` — passed (Vite reports the existing large-chunk advisory). The default output directory could not be cleared because the worktree's existing `dist/assets` is read-only (`EROFS`); the build was directed to fresh `/tmp` output.
  - `rtk npm run typecheck -- --pretty false` — blocked by `TS2503: Cannot find namespace 'JSX'` at `src/statblocks/publication/ThreatPublicationPanel.tsx:553`, outside this lease and unchanged by this branch.
  - `git diff --check` — passed.
- Desktop/mobile evidence: captured and inspected a separate synthetic preview on UI port 54124 with a loopback-only mock API on 54125; it used a synthetic World/Plan and an authorization-rejected response. At 1310×900, expanded Settings and the full composer fit in the viewport (composer bottom at y=884). At 390×844 with Settings expanded, the panel reports `overflow-y: auto`; scrolling 239px exposes the full composer and disabled Send button (composer y=541–832, button y=781–818). Screenshots were captured and inspected in the browser session but were not saved as shareable files, so no screenshot path is available. No credential was entered, no user Plan was edited or saved, and the live API or ports 5202/5203 were not contacted.
