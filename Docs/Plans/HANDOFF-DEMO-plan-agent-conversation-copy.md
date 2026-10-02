# HANDOFF — DEMO managed-World Plan conversation witness alignment

**Status:** COMPLETE — merged in Buddy PR #847.
**Repository:** `Drakosfire/DungeonMindBuddy`
**Base:** Buddy `main@ff5234bba6456928f820b55e12482f1de88be554`
**Branch:** `codex/demo-plan-conversation-copy`
**Topology:** Parallel-independent with #836 and #839 at their observed heads. This slice edits one separate mounted integration test and has no runtime, API, or shared-shell dependency. PRIME owns review and merge.

## Outcome and observed failure

Keep the saved managed-World Plan conversation's mounted proposal/apply/save/reload witness executable against the current Ask contract. On the prior #836 checkout, `WorldPlanAgentReviewedEdit.integration.test.tsx` reports 2/4 failures because its parameterized prose and READ-ALOUD cases still expect old copy saying Ask does not send Plan text. Current Buddy main renders the accepted truthful notice: Ask sends the exact committed Plan text, excludes unsaved editor changes, and records the committed revision; Compose/Revise uses the current mounted draft. `PlanSurfacePage.test.tsx` already asserts the current notice.

The failures occur before proposal interaction. The two delayed-response/thread-switch tests pass. This is an outdated assertion, not evidence of a runtime or API regression.

## Invariant and failure cases

- The witness must describe the actual Ask payload boundary: committed document content and revision are sent; divergent unsaved editor content is excluded.
- Compose/Revise remains a distinct reviewed edit path using the mounted draft; Apply does not persist until the ordinary Save path.
- Do not weaken the assertion to generic presence or change product text to satisfy stale test wording.
- Do not modify product behavior, API contracts, shared Agent host, or runtime state.

## Exclusive write lease

Only these paths may be edited:

~~~text
Docs/Plans/HANDOFF-DEMO-plan-agent-conversation-copy.md
apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx
~~~

No other path, service, provider, database, runtime, persistent demo data, or PR lease is included.

## Acceptance and verification

- Replace the single obsolete notice assertion with one that matches the current exact committed-text notice. The parameterized plain-prose and READ-ALOUD cases must both reach proposal review, Apply, Save, unmount/reload, and pass.
- Keep the delayed proposal-after-unmount and deferred-Apply thread-switch race cases passing.
- Run `npm --prefix apps/live-control-ui test -- src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx` and `git diff --check`.
- Inspect the cumulative base-to-head diff; it must contain only this handoff and the one test assertion change.
- No browser, provider, database, or shared runtime witness is claimed. PRIME owns review and merge; no merge authority is granted here.

## Settlement

Buddy PR #847 was reviewed and merged on 2026-10-02 at `01a292ba5487d39e581c62690c65c5f6d15e5722` from head `9e33dda202f64e17174a06e38d0089ba002b87cc`. DEMO ran the mounted integration suite on that exact head: **4 passed**. The cumulative `git diff --check` against base `ff5234bba6456928f820b55e12482f1de88be554` passed. This closes only the test-verification slice; no live J1–J6 witness is claimed. The write lease is released.
