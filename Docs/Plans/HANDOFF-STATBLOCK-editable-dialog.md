# STATBLOCK — editable saved-statblock dialog

ACTIVE. PRIME owns one serial UI slice after delivered2224 and API-only2226.
Base6711fe778a6886239bb9abbd4eb0f4fe0e5c3ac2; branch
codex/statblock-editable-dialog; existing buddy-context-loop checkout/dependencies.
The approved live API57cf094e/UI47a9ec5d use immutable sources/assets. No process
reads this mutable checkout as product source. No implementation restart lease.

## Outcome and boundary

Open the actual saved statblock in a native dialog through the existing Workbench.
Adopt SavedMechanicsRevisionEditor and StatblockRenderer unchanged as the edit/
render owners. The dialog retains one editor instance after first opening: closing,
Escape, reopening and resizing must not discard a draft, reset a selected revision,
repeat reads or Save, or create another editing copy. Let the existing editor load
on first opening; subsequent explicit read/retry/Save/recovery keeps its own logic.
Use the established native HTML dialog pattern and existing visual tokens; preserve
native focus trapping and return focus to its opener.

No new source/store, provider/model, migration, API, mechanics generation or
association contract. This slice's expanded size is presentation, not the still
required full-render navigation. Images, native node-link activation, conversation
embedding and the Corrupted Edge ooze creation remain later bounded slices. They
must reuse this editor identity/version owner, not copy the statblock into documents.

## Exclusive writes

- This handoff and HANDOFF-STATBLOCK-saved-projection.md predecessor settlement.
- apps/live-control-ui/src/statblocks/SavedStatblockDialog.tsx, CSS and test.
- apps/live-control-ui/src/statblocks/revision/SavedMechanicsRevisionEditor.tsx
  and its test: optional first-mount read only; default behavior unchanged.
- apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx and its
  test: adopt the dialog at the already admitted saved-World-draft boundary.
- .github/workflows/hosted-validation.yml: register the affected dialog/editor/
  workbench test files in the existing UI cohort; no additional job/setup.

Check held Play2172 and experimental2223/2225 leases; do not resume them. ADVERSARY
owns backend experiments; no backend files or runtime writes in this slice.

## Verification

Use the real editor/renderer with existing exact-revision fixtures. Prove lazy
first read, one editor instance across close/reopen/resize, dirty input retention,
unknown Save retention, read failure/retry and scope remount. Existing owning tests,
TypeScript/build and controlled browser checks must cover desktop/narrow layout,
focus, Escape and actual retained exact reads. No operator dogfood/acceptance gate.
Inspect cumulative diff, independently review, push/open one PR, CI, merge and
protected UI-only delivery. Preserve API/schema, all retained rows/state and drafts.

## Remaining goal scope

Build/Plan filters, exact passage selection and reload were verified on delivered
UI, with55 shared-owner and5 focused history checks. Play full native integration
still depends on explicitly held2172. No selected-reference-only restriction is
offered. Do not count that picker category filter as evidence restriction or claim
all References closed. The old full-completion Graph-record disclosure remains a
separate single-Details audit item; this dialog does not change reply presentation.

## Candidate evidence

Private evidence root: runtime-evidence/q01-published-graph-authority.
177 owning dialog/editor/Workbench tests pass (statblock-dialog-escape-tests-v2.log);
TypeScript/Vite build passes (statblock-dialog-build-v4.log). Earlier renderer/
definition/projection coverage remains in statblock-dialog-tests-v3.log (199 tests
before the added Escape regression).

Actual retained read-only browser verification: statblock-dialog-browser-v3.json
(final run, script v3/log v4). Native focus containment/return, Escape, exact saved
render/ability table, unchanged saved render while editing, same dirty editor after
reopening, no repeated reads and 390px viewport bounds/zero horizontal overflow
pass. Two exact mechanics reads, zero candidate reads, blocked writes and browser
errors empty; session revoked. Browser-local assets only; not live delivery proof.
Original failed Escape/outer-host unmount and selector-overflow observations remain
in browser.json/browser-v2.json and statblock-dialog-overflow-failure.json. Escape
now stops propagation without preventing the native dialog close. Scoped selector
width fixes the existing 1000px global selector width inside the narrow popup.
