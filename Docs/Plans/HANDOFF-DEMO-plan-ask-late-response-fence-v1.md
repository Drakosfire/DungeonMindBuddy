# HANDOFF — DEMO: fence late saved-Plan Ask responses

**Status:** ACTIVE — PRIME authorized one isolated, parallel-independent implementation lane on 2026-10-04 after a fresh 12-open-PR GitHub file census found no overlap with either UI/test path. This handoff is pinned before source edits; PRIME owns review and merge.

**Owner:** DEMO

**Repository/base:** DungeonMindBuddy `origin/main@47fcb50b1a392be89b19eb51032adac705f9c13b` (2026-10-04)

**Branch/checkout:** `codex/demo-plan-ask-late-response-fence-v1` in the clean isolated managed checkout `/home/drakosfire/.codex/worktrees/demo-plan-ask-late-response-fence-v1/DungeonMindBuddy`, created at the exact base above. Do not use the stale steward checkout or PR #914 checkout.

**Topology:** `parallel-independent` from open draft PR #914. PRIME checked all 12 currently open PRs and found zero path overlap with the two UI/test files below. PR #914 remains on the same base and owns card/runbook projection files, its handoff and roadmap; it has no behavioral dependency on this slice and retains its independent visual review hold. No shared service, database, provider, port or external state is used.

**PR topology:** One implementation PR for this capability. No PR number was preassigned; open one from this branch after implementation and exact cumulative review. DEMO does not merge. PRIME owns review/merge coordination.

**Activation record:** PRIME’s explicit activation names the base, branch, parallel-independent topology, exact write lease, handoff-first commit, acceptance witnesses, one-PR limit and exclusions. The reviewed pre-activation design draft SHA-256 was `39d3e9ed0c7b3b56378056a6ff4a4f4381eed41f26490e3d1d5cc39fda8d16c5`.

**Capability:** A saved-World Plan Ask remains attached to the exact durable turn, committed Plan basis, and optional selected Playable target submitted with that request, even when the user changes the selected card or committed basis before the response returns. A delayed answer must not be presented as an answer or evidence for the newly selected card/basis. Preserve the existing Ask, exact retry envelope, history, and card-target request behavior.

## Evidence and owner ruling

Current `WorldPlanAgentConversation` creates a request fence from verified World, document, surface instance, Plan revision, readiness, and Save state. The optional `playableTarget`, its basis, and selection generation are not part of that fence. `sendPendingAsk` verifies response identity against the original pending envelope, but its live freshness guard checks mount, current World/document scope, and request token rather than the captured fence. A successful response clears the local recovery envelope and refreshes canonical World history even if the selected card or same-document basis has changed.

The accepted canonical history carries primary-work revision and typed Playable-target provenance, and the renderer labels the original target. This is necessary but not sufficient for the live client: no mounted test currently holds a successful response while target or basis changes. The existing delayed-result test covers an initial failure followed by retry after switching conversations.

ARCHITECTURE ruling: keep a successful late Ask as one durable turn under its original submitted envelope/basis/card. Never rebind it to the current selection or discard it. A fence mismatch means “not current selection,” not cancellation of the server-accepted turn. ARCHITECTURE clarified on 2026-10-04 that shared World history may refresh while B remains selected if the completed row is visibly and structurally attributed to A’s exact card and Plan revision and is excluded from B’s active answer/evidence projection. Defer presentation until A is reopened only if the mounted view cannot preserve that attribution or keep the result out of B’s projection; never defer durable completion, cancel, or redispatch it.

## Exact ACTIVE write set

- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`
- `Docs/Plans/HANDOFF-DEMO-plan-ask-late-response-fence-v1.md` — only to pin this ACTIVE authority and record truthful verification/PR settlement.

This is an exclusive expected write lease: no other path may be edited under this activation. Commit this handoff as the first lane commit before editing either source/test file. No `PlanSurfacePage`, API type/error, server, APP-STATE, schema/migration, provider, Graph, or roadmap path is included. Request/response authority stays server-owned; this UI slice only fences presentation and verifies the original turn’s canonical provenance.

## Resources and state

No service, server, database, provider, port, credential, corpus, or external state is used. Verification is a deterministic Vitest mounted test with deferred mocked API responses only. Test output stays in the existing package's normal transient output locations.

## Owning-boundary acceptance

1. Start an Ask for card A at committed basis A and hold the successful fake response. Switch to card B, then release A’s response. Assert the exact original request/turn is dispatched once; it remains tied to A’s origin/provenance; shared history may refresh with a clearly A-labeled historical row while B remains selected; B’s active answer/evidence projection is unchanged; reopening A shows the same completed turn. No automatic retry or duplicate dispatch.
2. Repeat with the same card identity but changed selection/content generation and committed content digest/revision while the request is pending. The old answer remains attributed to the submitted basis and must not be treated as evidence for the new basis.
3. Preserve the existing World/document/conversation fences and exact retry-envelope behavior. Legacy graphless Ask and typed-card Ask tests remain green.
4. `git diff --check`; inspect exact cumulative base-to-head diff; focused Plan conversation/history tests pass. No visual acceptance, live provider call, or Graph behavior is claimed by this slice.

## Explicit exclusions

Do not add or modify Graph policy/receipt/completion rendering, stale-retry HTTP 409 error projection, saved-Plan editing, proposal targeting, visual styling, backend persistence, or the APP-STATE/SERVER Graph Ask implementation. The separate blocked Graph Ask handoff remains governed by its owner publication and PRIME activation gates.
