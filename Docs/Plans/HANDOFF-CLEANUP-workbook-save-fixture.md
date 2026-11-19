# CLEANUP: restore current workbook save fixture

Status: ACTIVE under the user-authorized cleanup goal, including review/merge.
Base: ef2a3e5e50ab2dd4077230589767b2629e9d46ec.
Branch: codex/workbook-save-fixture, existing cleanup checkout.
Topology: serial after merged #4091; no unmerged behavioral dependency.
Owner: cleanup steward; independent Bugbot review before merge. Follow-up #4074.

Outcome: keep the real pure planObjective export in the test API mock while
mocking get/save/continue transport. Preserve both typed actions and the deferred
second action. Enter an authored expected outcome and verify exactly one save
with exact World/conversation/turn/source scope, both rows and that outcome.
Explicitly require no continuation, dispatch callback or composer insertion.
This deliberately pending-save case proves submission, not backend persistence;
existing companion DurableWorkPlan contracts cover completion/recovery.
No runtime, API protocol, provider or storage policy change.

Write lease: apps/live-control-ui/src/planSurface/components/ConversationWorkbook.test.tsx,
this brief and HANDOFF-CLEANUP-blank-runtime-demolition.md for settlement.
All 60 pinned open PR head/base diffs checked at activation; no target overlap.
The predecessor's CI-owned relocation remains blocked and is not absorbed here.

Verification: focused workbook plus companion durable-plan modules: baseline
24 passes/1 failure, corrected 25 passes. These are working-tree diagnostics.
Run exact-head local hosted
verifier/build/validator, then full discovered diagnostic under the global lock
with verified Projects external scratch. Require one intended failure resolved,
all original cases retained and no new failures or changed remaining leading
messages. Preserve unrelated red results, conditional inventory extras and the
earlier unresolved quote observation. Independent cumulative exact-head source
and raw-evidence approval before merge. No servers, providers, databases or remote
hosts are written. Original cleanup owner/release gates remain outstanding.
