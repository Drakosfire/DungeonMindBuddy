# DOGFOOD: continue from a newly created World page

ACTIVE under Alan's instruction to finish the actual-app conversation/page flow.
Owner DOGFOOD. Actual47d41c acceptance created/reviewed/saved/reopened one correct
page, with zero new source acquisition and idempotent UI confirmation. It exposed
a follow-on blocker: reviewed World-owned pages have no legacy campaign tag and
BuildSurfaceShell therefore publishes a neutral context. Do not close the goal
while its created page cannot be used for the next request.

One UI-only serial follow-up, branch codex/dogfood-world-page-context, isolated
managed checkout dogfood-lore-review/DungeonMindBuddy. Frozen base
codex/dogfood-world-page-context-base@3a6cc4437558597edb3ed882f9e661c2a1b4ab49,
explicitly adopted by COMBAT at origin/codex/combat-manual-statblock-serving-0188.
It preserves47d41c plus the exact three reviewed COMBAT workbench/test/handoff
paths. #4441 remains COMBAT's source PR; no main merge authority is inferred.
Activation order: COMBAT frozen3a6 candidate, then this source-preserving UI slice
in a coordinated window. Our PR merges only into our frozen dedicated base.
If serving remains47d41c, coordinate the shared reviewed successor explicitly;
never silently replace another activation or pull unrelated main.

Write lease: this handoff, BuildSurfaceShell.tsx and its existing test. No backend,
model/prompt, dependency, DTO, schema, Graph publication or source evidence changes.
Current open work checked: COMBAT's three paths are disjoint; ADVERSARY Plan
contracts and onboarding ingestion work do not declare a Shell/test lease.
ONBOARDING was asked to flag a competing current lease before implementation.

Keep the accepted campaign tag and campaign-specific Graph controls unchanged.
For conversation publication only, permit an already admitted World-owned source
with a null campaign tag to use its World identity as the existing local host
namespace (already supported when legacy tag equals World). Do not write a
campaign association or manufacture Core campaign authority. Refuse a conflicting
nonnull campaign tag, missing World, rejected/quarantined snapshot or foreign
source; retain the session/controller and server World checks.

Prove the mounted editor/session publishes the exact World/page source context,
retains edit/save, and clears it across invalid transitions. Run exact-head hosted
and integrated discovered diagnostics, independent cumulative review, then an
image-only188 cutover with the current compatible predecessor as recovery. The
serving188 fence is unavailable-corpus-conversation; main's independently assigned
caret188/189 lineage is a known collision, reported to ADVERSARY and not adopted.
Actual acceptance must reopen the created page, send the next ordinary request,
and preserve the previous page/create/no-acquisition evidence and real timings.
