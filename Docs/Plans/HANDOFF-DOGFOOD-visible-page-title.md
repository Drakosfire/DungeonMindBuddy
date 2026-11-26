# Visible editable Build page title

Status: ACTIVE. User reported that the page title is not visible or editable in the document. This serial slice adds the existing revision-checked metadata rename control beside the visible Build page title, while preserving the existing Source actions control. The title remains metadata; the Markdown body is unchanged. Guest behavior remains read-only for rename. Scope is this handoff and the Build title, shell, page and focused test files.

Verification: the existing dirty-rename → save → hard-reopen case passed through the new visible title control. Build shell and rename owner tests passed (43, one Chromium-dependent layout test skipped); React act warnings were emitted. Local `tsc -b` passed. Independent review required. The separate Jev 400 diagnostic and prompt/response issues are not resolved by this change.

Review found that the new control must also disable during a page switch or creation. The controller's existing transition state is now passed to it, matching the established Source actions control. A focused delayed-switch case is queued behind the shared local verification lock; do not treat that case as passed until its result is recorded.
