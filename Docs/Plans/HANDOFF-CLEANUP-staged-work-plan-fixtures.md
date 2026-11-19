# CLEANUP: restore staged work-plan test fixtures

Status: ACTIVE under the user's cleanup goal and standing review/merge authority.
Base: 59bf34efb8e703d0d208362403dd3071132262b9, fetched origin/main.
Branch: codex/staged-work-plan-fixtures in the existing cleanup checkout.
Topology: one serial PR after merged #3532; no unmerged behavioral dependency.
Owner: cleanup steward, with independent Bugbot review. Follow-up owner #4074.

Outcome: exercise the existing work-plan editing, retention, context and Save
assertions without a strict mock crashing current native inspection children.
The API mock lacks two current catalog exports. A real trace proves the resulting
React errors remove the tested subtree. Provide explicit typed empty catalogs,
scoped to the requested managed World and the existing synthetic native pin.
Wait for the existing placement control to become enabled before two user clicks.

Write lease: apps/live-control-ui/src/surface/workPlans/StagedWorkPlan.test.tsx
and this handoff only. All 61 open PR file lists checked at activation; neither
path overlaps active PR work. No runtime, selectors, assertion deletion, shared
classification/CI registry, auth, schema or deployment changes. The source DOM
attribute experiment did not fix the failures and is deliberately not shipped.

Verification: isolated baseline reports 1 pass/9 failures; the complete catalog
and enabled-control fixture experiment reports 10 passes with original assertions
retained. Those are diagnostics, not final commit acceptance. Run exact-commit
focused cases, repo-owned hosted verifier/validator and full default-discovered
diagnostic; compare every case against retained byte-identical parent frontend
source. Expected resolution is the nine existing work-plan failures, not blanket
green qualification. Preserve any other inherited failure and inventory discrepancy.
Independently review the cumulative exact head and raw evidence before merge.

Runtime: no application, database, provider or remote host resources. Frontend
checks honor the global resource lock and use task-owned external scratch/cache
on the verified Projects filesystem. SSH signing and the original release/Recap
ownership gates remain separate; this fixture repair does not complete them.
