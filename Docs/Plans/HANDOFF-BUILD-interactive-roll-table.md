# Interactive titled roll table

Status: ACTIVE — explicit operator request. PRIME implements; ARCHITECTURE reviews.
Serial branch codex/interactive-roll-table from remote main3742c7f6 at
/tmp/prime-recap-mention-boundaries. No provider or Graph mutation.

Recognize first-column dN tables only when numeric/range rows cover every face
exactly once. Offer Roll dN and show face plus matching soldier/details, including
when collapsed. Use unbiased local randomness; result remains transient and does
not modify the document. Ordinary or malformed tables get no misleading roll action.

Use an immediately preceding H2 as the table title, presented inside its editor
frame instead of duplicated outside it. Editable frame title updates that H2 or
inserts one before the table. Standard Markdown heading/table storage and read-only
exports stay unchanged; do not introduce a parallel artifact database or custom
Markdown syntax. Preserve unsaved draft, cells, collapse, editing and Save/reopen.

Exclusive writes: this handoff; apps/live-control-ui/src/tiptap/extensions/
EmbeddedTableView.ts, EmbeddedTableView.test.ts, embeddedContentFrame.ts,
embeddedContentFrame.css, planTableExtensions.ts, rollTable.ts(new),
rollTable.test.ts(new). Verify deterministic faces/ranges/invalid tables and actual
editor title save/reopen, result/no document edits, reattachment. Typecheck/build,
independent exact review, PR/merge and UI5202-only rollout; APIs unchanged. Set the
operator-requested title on their existing table using its visible control, leave
Save explicit. No new provider calls.

Operator adds whole-object drag/drop. Extend exclusive set with
EmbeddedTableMove.ts and EmbeddedTableMove.test.ts. Move the adjacent caption H2
and table atomically in one editor transaction, preserve undo and cells. Accept
only same-editor, in-memory-token drags against the unchanged source document;
resolve drop to top-level boundaries. Provide keyboard Alt+Up/Down on the handle.
No cross-document transfer, foreign HTML import or hidden source edits.
