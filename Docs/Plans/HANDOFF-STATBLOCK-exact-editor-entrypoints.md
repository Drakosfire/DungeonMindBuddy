# STATBLOCK: exact saved-version editor entry points

ACTIVE under the operator statblock goal. PRIME owns this serial UI-only slice.
Branch codex/exact-statblock-entrypoints from remote main375be185b0414361f7afae676029365cd8ce0a61.
Reuse buddy-context-loop/dependencies; no new worktree/environment/provider calls.
Plan entry2248 and native creation2246/2247 are delivered. Qualified2244/2249 are
delivered; no unmerged runtime dependency. ADVERSARY owns reserved0134, untouched.

Outcome: the full reader opens its exact saved revision in the existing shared
editor, rather than a Workbench hint or original version. One editor owner keeps
same-version dirty work across triggers; changing version/draft refuses while
work, image selection or Save is unresolved. A clean explicit request may change
version even when the editor previously changed selection internally. Each accepted
selection has an owner token so stale callbacks cannot mutate the next selection.

A pending Save belongs to its original source version. Opening a different exact
version must not silently retarget that Save. Use existing history/inspection and
recovery owners; explicitly open the source for recovery, or fence an absent Save,
then retry the requested version. Keep raw recovery and all saved versions intact.
No new statblock store, Graph association, node/inline projection, API/schema/model
or mechanics publication. Those remain subsequent required goal slices.

Writes: this handoff; statblocks/SavedStatblockSession.tsx and .test.tsx;
statblocks/StatblockPage.tsx and .test.tsx;
statblocks/revision/SavedMechanicsRevisionEditor.tsx and .test.tsx (all UI paths
under apps/live-control-ui/src). No backend, dependencies, routing or shared App.
Verify exact target vs hint, same-version shared dirty editor, clean version switch,
reselection after internal dropdown changes, late callbacks, explicit unknown/other-
version Save recovery, read failures/retry, full-page edit and foreign World guards.
Run owning tests/build, independent cumulative source/integration/transport review,
CI and protected UI-only delivery; controlled real ooze original/portrait version
opens, close/reopen and full-page return with no provider or content writes.
