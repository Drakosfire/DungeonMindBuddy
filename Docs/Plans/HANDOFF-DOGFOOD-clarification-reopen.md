# DOGFOOD: reopen saved Build clarifying questions

ACTIVE single-PR assignment from Alan's explicit request to check the signed-in
clarification flow first, fix what breaks, and deploy the writer fix while
preserving production changes. DOGFOOD owns implementation/review/delivery.
Branch codex/dogfood-clarification-reopen starts at observed serving source
33180d5bda8c33f02814c432ef4c69f547e72102 (healthy imagea1ebe10f, APP0209).
Primary checkout: dogfood-build-reply-contract/DungeonMindBuddy. Its previous
exact-M backend work completed all three contracts, with workers closed before
this checkout changed. PR4642 is committed/pushed and parked in the separate CI
checkout; no part of its unregistered protocol is required for this fix.

Outcome: an active signed-in Build conversation reopened from lightweight saved
messages displays its typed clarifying-question workbook, restores its existing
scoped local question/answer notes, and adds reviewed answers to the composer
only on author action. Page content stays unchanged. Do not parse prose into
new questions, fetch full execution history merely to restore the form, or
weaken source/pointer/World checks. Server library projection already supplies
the typed questions descriptor. This is a frontend rendering defect.

Write lease: only renderConversationEvent's lightweight saved-Build branch in
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx,
the owning hosted worldHistory test/helper for these new cases, and this brief.
No Plan behavior, PlanJevDriver lease, backend protocol, schema, model/provider,
benchmark or deployment-security changes. Older Plan release overlays4512/4474
are transport artifacts; the leased Plan expansion4580 and evaluator4584 paths
are untouched. Restore clarifying questions has been notified of this exact
runtime ownership and observed failure. Any new file/contract needs checkpoint.

Verification: mounted lightweight-message response without full history hydration;
editable questions/answers and exact formatted message; unmount/remount restores
notes; no automatic provider/page writes; descriptor source/pointer mismatch
controls. Preserve a failing regression before the fix. Run exact-source hosted
frontend and full default-discovered diagnostic at an integrated checkpoint;
retain known failures and do not call the diagnostic green without proof.
Independently review the cumulative source/evidence. Recheck actual signed-in
Build form, edited answers, continuation and reload after deployment.

Observed hosted witness: synthetic Dogfood Context Reuse World,
world-25ff3b0bf99844229e0007d188be8113; Memory Ferry page
1387273a-0aae-4bf7-bb4b-f1d1434889a4 stayed saved at revision2. Actual fresh
questions turn3a00f05f-0e2f-429d-ba39-b7a28e972802 and answered continuation
e66d423e-a297-4d0e-97b8-1f532bf8b554 succeeded (UI trace windows11.5s/6.0s).
After browser reload, questions were plain text and workbook absent; answers
and proposal text survived. This is app evidence, not a scripted model benchmark.
Screenshot is retained in this chat's visualizations as
buddy-clarification-reopen-missing-form.jpg. No new page was saved/created.

Resources: no database allocation or local server for this UI slice. Recovery
qualification runs separately on the same retained App under reviewed owner
2124990; do not alter its source, workers, database or evaluator. Frontend runs
honor the shared verification lock and pinned Node/npm on verified Projects
storage. Runtime release composition later preserves all then-current production
changes and merged writer4630; the old4f-bound packet is ineligible. Deployment
and recovery evidence do not substitute for the app acceptance above.
