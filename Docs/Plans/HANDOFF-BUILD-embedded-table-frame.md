# Embedded table presentation

Status: ACTIVE — operator requests collapsible, fitted inserted content objects.
PRIME implements; ARCHITECTURE independently reviews. Serial branch
codex/embedded-table-frame, base9a415e61; checkout/tmp/prime-recap-mention-boundaries.

Use the existing durable table node and GFM representation; add an independent
editor NodeView frame with row count, keyboard-accessible collapse/expand, compact
numeric columns and bounded scrolling. Preserve editable cells, undo, exact
serialized content and Save/reopen. Collapse is transient presentation state,
initially expanded; never emit document edits for toggling. The generic frame is
reusable by future typed media nodes; this slice does not implement image/audio
artifacts, new persistence contracts or model tools.

Exclusive write set: this handoff; apps/live-control-ui/src/tiptap/extensions/
planTableExtensions.ts, EmbeddedTableView.ts(new), EmbeddedTableView.test.ts(new),
embeddedContentFrame.ts(new), embeddedContentFrame.css(new). Reuse shared editor
table rendering across surfaces; HTML export/read-only readers remain plain tables.
Verify actual editor collapse/edit/serialization and existing Build insertion
Save/reopen boundary, typecheck/build, independent review and PR/merge. Deploy only
UI5202 after preserving the operator's unsaved draft. Do not Save or discard it.
