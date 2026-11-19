# CLEANUP: Build durable-save status regression fixtures

ACTIVE under standing cleanup implementation/review/merge authority.
Base3624806ddabcf7ac520c6c0b45111134bcd52035; serial after4101,
no unmerged dependency. Reuse isolated checkout; no runtime/provider/DB resources.

## Invariant and exclusive scope

BuildSurfacePage.test.tsx waits for retired Unsaved local changes/Committed labels.
Current DurableSaveStatus exposes unsaved/saved states and Unsaved changes/Saved.
The stale wait runs beyond800ms autosave and creates misleading later mock errors.
Disposable20-case proof using current labels resolves6of8failures, preserving
all assertions; bare landing Source actions and old graph-object context remain
independent failures. Do not change or restore runtime to satisfy old fixtures.

Lease: apps/live-control-ui/src/buildSurface/BuildSurfacePage.test.tsx and this
brief only. Replace retired status assertions with exact current data-save-state
checks, preserving create/edit/preparecommit/StrictMode/rename/reopen/dirty guards,
all case IDs and every non-status assertion. Current status markup stays real.
All60 open head/base diffs show no target overlap. API/runtime/shared helper,
Build Page, status component, save/autosave, registry and other owner tests read-only.

Pin this brief in pushed branch history before implementing; remove it from final
tree to avoid recreating settled execution clutter. PR links immutable assignment.
No policy change. Retain all unique diagnostics in external evidence.

## Verification

Focused module baseline12pass8fail; candidate18pass2fail. Establish final exact
state assertions and exercise a task-local incorrect unsaved-state presentation
fault: corrected dirty-state tests must fail even if visible copy remains current.
Source mutations stay in task-owned external scratch and are restored.
Run exact-head hosted/build/validator and full discovered diagnostic against
last frontend-testeddb1cf2db555a0d165b11eb039c056eb71c562931 after proving actual
parent UI/CI/verifier identity. Exactly6intended failures may resolve, no ID
additions/omissions/new failures/changed remaining leading messages. Keep two
remaining Build cases and all other inherited red diagnostics, conditional
inventory differences and earlier quote observation visibly open under4074.
Independent exact-head source/raw-evidence review before merge. No browser,
transport/write/backend or release qualification claim.
