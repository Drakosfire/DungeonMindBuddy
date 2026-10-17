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

Live follow-up ACTIVE: operator requests removing redundant generated title/intro
from their current draft. Preserve other content; verify exact DOM selection before
editing. Investigate live toggle after an event-loop turn before claiming acceptance.
Same code write lease; serial corrective PR if needed. Initial merge79a18514.

Operator follow-up extends this corrective slice: natural expanded table height,
no internal scrollbar; floating/sticky authoring toolbar; server still rejects
all pipe tables despite editor support. Additional exclusive paths:
apps/live-control-ui/src/buildSurface/buildSurface.css;
apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts and
useWorkspaceDocumentAuthoring.test.tsx; apps/live_control_server/services/
tiptap_markdown_write.py and tests/test_tiptap_markdown_write.py. Permit only
parser-proven flat canonical editor tables at worldbuilding prepare/commit,
preserve other unsupported syntax and frontmatter gates. Show actual save reasons.
Verify actual prepare/commit/readback fixture, preserve operator's unsaved draft.
