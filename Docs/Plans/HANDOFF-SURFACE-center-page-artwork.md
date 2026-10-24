# SURFACE — center paragraph artwork

ACTIVE PRIME UI-only correction at d934e31c5, codex/center-artwork-renderer-wrapper, existing
context-loop checkout. One serial PR. Operator wants easy centering immediately;
paragraph artwork displays on its own centered line by default in shared edit/read presentation. No new
save schema, model call, source mutation, API change or grid implementation.

Exclusive writes: MediaImageNode.css; Backlog.md high-priority grid constructor
capture; this handoff. Verify real resized artwork geometry in an isolated Build
tab and read-only shared presentation; production build, cumulative diff,
independent Bugbot, PRIME merge and protected UI5202 adoption. Keep API1709 and
broad goal paused; preserve original user tabs/drafts and document state.

Rendered discovery after PR1714: ReactNodeViewRenderer adds span.node-mediaImage
between the paragraph and node view. Correction includes that actual wrapper in
the same centering policy; verify measured equal paragraph margins before closure.
