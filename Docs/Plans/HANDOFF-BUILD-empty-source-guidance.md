# Empty Build conversation guidance

ACTIVE: user requested diagnostic repairs and Trace deployment. Serial branch `codex/frontend-build-empty-source-test`, based on `origin/main` at `e3782b509`, follows #4811. Scope: empty Build source guidance, its mounted integration test, the affected action catalog entry, and this brief.

The empty Build composer offers an "Open source actions" button, but that menu is absent until a source is selected. Remove that dead control and retain the "Choose a source" focus action, now pointing to the document-picker button. Update the mounted test for the current inventory and picker while preserving disabled/unsaved source, no-write, exact selection and empty-return checks. Verify affected integration and conversation cases, clean exact-SHA hosted verification and independent review; full discovery at the next integrated checkpoint.
