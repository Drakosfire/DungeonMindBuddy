# CLEANUP: late native Plan turn recovery

Status: ACTIVE. User's standing cleanup goal authorizes implementation, independent review and merge. Base: cd000322af26adda1aff7ada6c6fbbd6fa801637. Serial successor to merged #4116; no open cleanup implementation PR. Branch: codex/plan-late-turn-recovery; existing isolated checkout buddy-bounded-production-logs/DungeonMindBuddy.

Write lease: only the existing delayed-proposal/unmount case in apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx, plus this temporary brief. No runtime, shared fixture, parser, schema, CI or other case changes. Inspected all 61 current open heads: none changes the test file. Shared runtime and fixture paths are read-only.

Invariant: a native initial Plan turn completing after unmount must not apply or persist document changes or resurrect obsolete browser threads. Preserve intentionally durable server-accepted turn settlement and recover the saved suggestion on a fresh mount without reposting. Do not equate no localStorage writes with durable-history deletion. Keep the clarification/remount/linked-continuation obligation separate and unchanged.

Validation: targeted old/new diagnostic, adversarial stale-write/recovery control as applicable, nineteen other case bodies unchanged, standard isolated exact-SHA hosted/build/validator, full default-discovery paired comparison, cumulative diff and independent exact-head review. Synthetic client transport proves no provider/database/deployment acceptance. Inherited failures/pending/inventory discrepancies remain visible. Scratch stays in existing verified Projects task storage under global frontend lock; no runtime ports/databases/services allocated.

Before merge remove this temporary brief from the final tree, retaining the pinned assignment in history. Record actual results and merge in the external cleanup ledger and owning #4074; never pre-mark completion.
