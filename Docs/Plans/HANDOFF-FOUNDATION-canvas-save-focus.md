# FOUNDATION — preserve rich editor through saves

ACTIVE serial PRIME slice from9f6860574a9ef9170a2469ee578b27cfa56f8a51,
branch codex/canvas-save-focus in reused buddy-context-loop checkout. Current PR
census has no overlap. One Bugbot-reviewed PR and protected delivery5202.

Operator reports Build typing repeatedly loses the cursor. Shared authoring
changes documentKey after ordinary successful saves when no edit occurs during
the request, causing useEditor to replace TipTap. Build autosave makes this visible
at normal typing pauses. A save acknowledges existing content; it is not a document
replacement. Preserve editor identity/selection/focus/undo through acknowledgements
and missing-fingerprint failure. Keep explicit document load/import/discard/recovery
replacement behavior and existing dirty-during-save/CAS/verification guards.

Exclusive writes: this handoff; apps/live-control-ui/src/workspaceDocument/
useWorkspaceDocumentAuthoring.ts and matching authoring/fidelity tests;
Docs/Plans/HANDOFF-BUILD-native-kind-preflight.md predecessor settlement.
No API, migrations, source bytes or autosave timing changes. Use a separate
synthetic document for ordinary typing/reload proof; never modify the user's page.

Prove the regression with real editor identity and selection across clean save
and subsequent typing; cover uncertain/missing fingerprint and concurrent edits
with existing owner tests. Build and manually type across multiple autosaves using
ordinary browser controls. Record actual browser focus and persisted content;
unit checks alone do not establish the cursor fix.
