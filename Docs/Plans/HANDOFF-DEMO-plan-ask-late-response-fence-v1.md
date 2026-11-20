# HANDOFF — DEMO: fence late saved-Plan Ask responses

**Status:** SETTLED — Buddy PR #915 merged at `e287cb875ddf763fb8376b76fde2c5bc3091732e` on 2026-10-04 from reviewed head `49173201e7466d40aeb41ac617b0d779ef1584ac`; the implementation lease is released.

**Owner:** DEMO

**Repository/base:** DungeonMindBuddy `origin/main@47fcb50b1a392be89b19eb51032adac705f9c13b` (2026-10-04)

**Branch/checkout:** `codex/demo-plan-ask-late-response-fence-v1` in the clean isolated managed checkout `/home/drakosfire/.codex/worktrees/demo-plan-ask-late-response-fence-v1/DungeonMindBuddy`, created at the exact base above. Do not use the stale steward checkout or PR #914 checkout.

**Topology:** `parallel-independent` from open draft PR #914. PRIME checked all 12 currently open PRs and found zero path overlap with the two UI/test files below. PR #914 remains on the same base and owns card/runbook projection files, its handoff and roadmap; it has no behavioral dependency on this slice and retains its independent visual review hold. No shared service, database, provider, port or external state is used.

**PR topology:** One implementation PR for this capability: [PR #915](https://github.com/Drakosfire/DungeonMindBuddy/pull/915), opened from this branch after implementation and exact cumulative review. Implementation commit: `efaa86da`; PRIME merged the reviewed head after independent acceptance. DEMO does not merge.

**Activation record:** PRIME’s explicit activation names the base, branch, parallel-independent topology, exact write lease, handoff-first commit, acceptance witnesses, one-PR limit and exclusions. The reviewed pre-activation design draft SHA-256 was `39d3e9ed0c7b3b56378056a6ff4a4f4381eed41f26490e3d1d5cc39fda8d16c5`.

**Capability:** A saved-World Plan Ask remains attached to the exact durable turn, committed Plan basis, and optional selected Playable target submitted with that request, even when the user changes the selected card or committed basis before the response returns. A delayed answer must not be presented as an answer or evidence for the newly selected card/basis. Preserve the existing Ask, exact retry envelope, history, and card-target request behavior.

## Evidence and owner ruling

At base, `WorldPlanAgentConversation` used a request/preparation fence from verified World, document, surface instance, Plan revision, readiness, and Save state. `sendPendingAsk` verifies response identity against the original pending envelope, while its post-dispatch ownership guard checks mount, current World/document scope, and request token. The implementation keeps those pre-dispatch and owner fences intact, and adds a separate presentation fence for the selected target identity/basis, stale state, editor selection/content generations, and dirty state. A successful response still clears the local recovery envelope and refreshes canonical World history; a changed presentation fence only changes the completion notice to name the submitted origin.

The accepted canonical history carries primary-work revision and typed Playable-target provenance, and the renderer labels the original target. The mounted tests hold a successful response across a target switch and a same-card basis change, then verify history readback and reopen behavior. A malformed typed target receipt remains in generic history with an unavailable-receipt warning, without target inference on B or after reopening A. The existing delayed-result test still covers an initial failure followed by retry after switching conversations.

ARCHITECTURE ruling: keep a successful late Ask as one durable turn under its original submitted envelope/basis/card. Never rebind it to the current selection or discard it. A fence mismatch means “not current selection,” not cancellation of the server-accepted turn. Shared World history may refresh while B remains selected when the completed row is visibly and structurally attributed to A’s exact card and Plan revision and is excluded from B’s active answer/evidence projection. The accepted history contract guarantees a typed target receipt for every accepted targeted Ask. Missing/malformed receipts must never be inferred from current selection or used to attach the answer to A after reopen; the UI may retain only the existing generic history projection with its unavailable-receipt warning where available. The malformed-receipt test verifies the row stays generic and is not attributed to B. No local persistence is added.

## Exact ACTIVE implementation write set (released at merge)

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `Docs/Plans/HANDOFF-DEMO-plan-ask-late-response-fence-v1.md` — only to pin this ACTIVE authority and record truthful verification/PR settlement.

This was an exclusive expected write lease, released at merge; no other path was edited under this activation. The handoff was the first lane commit (`ce5610c7`) before either source/test file changed. The implementation commit was `efaa86da`; post-merge settlement is recorded in a docs-only steward sync. No `PlanSurfacePage`, API type/error, server, APP-STATE, schema/migration, provider, Graph, or roadmap path was included. Request/response authority stays server-owned; this UI slice only fences presentation and verifies the original turn’s canonical provenance.

## Resources and state

No service, server, database, provider, port, credential, corpus, or external state is used. Verification is a deterministic Vitest mounted test with deferred mocked API responses only. Test output stays in the existing package's normal transient output locations.

## Owning-boundary acceptance

1. Start an Ask for card A at committed basis A and hold the successful fake response. Switch to card B, then release A’s response. Assert the exact original request/turn is dispatched once; it remains tied to A’s origin/provenance; shared history may refresh with a clearly A-labeled historical row while B remains selected; B’s selected context and active answer/evidence projection are unchanged; reopening A shows the same completed turn. No automatic retry or duplicate dispatch.
2. Repeat with the same card identity but changed selection/content generation and committed content digest/revision while the request is pending. The old answer remains attributed to the submitted basis and must not be treated as evidence for the new basis.
3. If history returns a missing/malformed target receipt, keep the turn only in the generic World history projection; a malformed receipt uses the existing unavailable-receipt warning. Never infer a target from current selection or attach the answer to B, and reopening A does not repair missing/malformed provenance. No local origin persistence is added.
4. Preserve the existing World/document/conversation fences and exact retry-envelope behavior. Legacy graphless Ask and typed-card Ask tests remain green.
5. `git diff --check`; inspect exact cumulative base-to-head diff; focused Plan conversation/history tests pass. No visual acceptance, live provider call, or Graph behavior is claimed by this slice.

## Verification recorded on 2026-10-04

- The focused mounted conversation, Plan surface, and Agent history suites passed: **104 tests, 0 failures**. They ran in `/tmp/dembuddy-current-main-47fcb/apps/live-control-ui`, an exact-base source archive, with the two leased source/test files copied from this lane; SHA-256 checks confirmed those files matched the branch. The isolated implementation checkout has no `node_modules`, so the suite was executed against the exact copied bytes in the archive.
- `git diff --check origin/main` passed for the cumulative lane diff.
- `pnpm run typecheck` reports `src/statblocks/publication/ThreatPublicationPanel.tsx(553,77): error TS2503: Cannot find namespace 'JSX'`. This is outside the lease and unchanged. The same error reproduced after restoring the exact `origin/main` versions of both leased source/test files in the archive, so it is a base failure; no package typecheck PASS is claimed.

## Explicit exclusions

Do not add or modify Graph policy/receipt/completion rendering, stale-retry HTTP 409 error projection, saved-Plan editing, proposal targeting, visual styling, backend persistence, or the APP-STATE/SERVER Graph Ask implementation. The separate blocked Graph Ask handoff remains governed by its owner publication and PRIME activation gates.

## Post-merge settlement — 2026-10-04

- PR #915 merged at `e287cb875ddf763fb8376b76fde2c5bc3091732e` from the exact reviewed head `49173201e7466d40aeb41ac617b0d779ef1584ac`.
- PRIME reported independent exact-head review as ACCEPT. Its focused mounted history rerun passed **16/16**; the captured run is `/tmp/prime-915-ui-review.log`. DEMO's three-suite owning-boundary run passed **104/104** with branch/archive source and test SHA-256 matches, and the cumulative diff check passed.
- The only inherited package typecheck failure is recorded above. No runtime, service, database, provider, or external state was used. All three leased paths are released.
