# CLEANUP: remaining landing-regression relocation

Status: BLOCKED. Owner: CI classification worker/coordinator. Follow-up:
[#4074](https://github.com/Drakosfire/DungeonMindBuddy/issues/4074).
No successor implementation lane or write lease is allocated by this record.

## Completed predecessor

[#4091](https://github.com/Drakosfire/DungeonMindBuddy/pull/4091) merged at
ef2a3e5e50ab2dd4077230589767b2629e9d46ec: the unused blank component, publication
helper and CSS are removed. Current landing/Build/Back/Forward coverage remains
at [the registered test path](../../apps/live-control-ui/src/blankSurface/BlankSurface.test.tsx).
The directory is now test-only; its relocation is not completed.

[Runtime retirement scope and exact-source evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/4df6d3adfa2f0eee7ccba06166b5ec74a7a3fcb6/Docs/Plans/HANDOFF-CLEANUP-blank-runtime-demolition.md)
and the [completed fixture implementation records](https://github.com/Drakosfire/DungeonMindBuddy/tree/4df6d3adfa2f0eee7ccba06166b5ec74a7a3fcb6/Docs/Plans)
remain pinned in Git history. Those historical assignments do not activate new
work. Current failure counts and verification limits belong to #4074, not copied
snapshots in this continuation.

## Start prerequisite and bounded outcome

The [CI owner's pinned contract](https://github.com/Drakosfire/DungeonMindBuddy/blob/537447bb3bf1da4086d281195f6d97d990e37067/Docs/Plans/HANDOFF-CI-domain-shadow.md)
freezes classification ownership without a concurrent writer. Obtain explicit
release or a bounded split before editing [the classification manifest](../../ci/test-classification.json).
Re-anchor current main, open work and that ownership disposition before dispatch;
PR age or a passing local check does not release the lease.

After that prerequisite resolves, pin a successor branch/assignment and move the
regression to `apps/live-control-ui/src/home/BuddyLandingNavigation.test.tsx`.
Update its classification while preserving the current role and selection policy,
then remove the empty `blankSurface` directory. Expected writes are only the old
and new test paths, classification entry and this continuation; they are not an
ACTIVE allowlist until the owner authorizes the successor.

Verify current landing/Build/Back/Forward behavior and the exact old/new test ID
pair, with no other omissions or new failures. Use the repository's exact-source
local verification and independent review standard before merge. Keep inherited
red diagnostics visible; path relocation grants no deployment or release approval.
