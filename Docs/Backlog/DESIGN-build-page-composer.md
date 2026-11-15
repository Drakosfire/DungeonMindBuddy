# Design proposal: Build page composer

**Status:** Proposed for discussion. This does not activate implementation, change the roadmap, or authorize a storage migration.

## What we want to be able to make

- On an Edge page, put editable prose beside an existing illustration. Then make a section with two ordinary tables flanking the illustration. A different section can use an entirely different split.
- Put a live title or short label directly over existing artwork, such as an Edge section title or a label on a printable token. The words stay editable and searchable; they are not baked into the pixels.
- On a sticker sheet, arrange cutouts of different heights in rows. The tallest cutout determines the row height; shorter ones retain their dimensions and align at the top. The Mother-of-Falling-Branches tokens are a useful print test if separate assets are available. A flattened sheet is not a substitute for that test.

Use the same composer for both. Keep the rest of a Build document in its normal flow and keep writing inside Tiptap; don't switch the whole page to a canvas.

## The primitive: a row of ordered slots

A page contains normal blocks and optional layout rows. Each row starts with one full-width slot; the author can split it into columns. Each slot contains an ordered sequence of normal editable blocks: paragraphs, artwork, tables, callouts. Widths are local to a row. Rows and slots have stable identities; moving existing blocks preserves their identities and asset references. Start with one to three slots per row, no nested layout rows, no overlap between slots, and no page-level x/y coordinates. A local image/text stack is an explicit exception inside a single block.

A **table** is a separate semantic block, not a styled layout row. Its column headings apply across rows; keyboard navigation, accessibility, copying, and export preserve actual cells and headers. A table can sit in a slot. Reuse sizing or resize-handle behavior if it fits both, not the node types or their navigation rules.

## Controls and rendering

| Control | Behavior |
| --- | --- |
| Add row / split row | Insert a full-width row, or split the current row; regular blocks above and below stay untouched. |
| Vertical divider | Resize adjacent column widths with snap increments and a usable minimum. Do not resize the artwork itself or change what comes first. |
| Horizontal row line | Drag to set a minimum row height, or reset to Auto. Actual height is at least the height required by content; never clip text, stretch shorter art, or force all rows to equal height. |
| Move a block | Use a dedicated handle and drop target, with a keyboard move equivalent. Only this explicit action changes reading order. Keep text selection and table editing native. |
| Image size | Use the existing image resize behavior within the slot, preserving aspect ratio. Slot width and image size are different controls. |
| Row lines | Default: dotted editing guide in Build, absent in the reading view. **Bordered:** deliberate solid rules appear in the rendered document. **Clean:** no idle guide; show the handle on selection, resize, or keyboard focus. Persistent rules are style; editing guides are not printed cut lines. |

Rows align content at the top. On narrow screens, stack slots in the same order the document is read: rows top to bottom, slots left to right, then blocks in slot order. Drop desktop-only minimum-height spacing in the stacked view. Tables retain their table semantics and use their own overflow treatment rather than widening the page. Expose resize handles with keyboard controls, accessible labels, and visible focus. One drag should undo as a single edit.

## Image with text on top

Add an opt-in **image + text** block that fits inside any slot or in the normal page flow. One existing image forms the base; one editable text block sits above it in visual depth. This is a local stack, not a new positioning mode for the page. Offer snap anchors (top/middle/bottom, left/center/right), inset padding, and a theme-aware backing or scrim so words can stay readable over busy art. Use the same text editor as the rest of the page; no rasterizing a title and no treating the title as alt text.

Keep the underlying asset and the overlaid words distinct. Moving the stack moves them together; editing the text, resizing the art, and changing its anchor are separately undoable. Use text and image identities in the saved revision. Anchors, insets, and backing are presentation only. In semantic output, emit the real text once in the stack's place, alongside the image reference when applicable; keep alt text available separately. Decorative images can be marked decorative, but that should never hide the title from reading or retrieval.

As the available width changes, reposition the text with its anchor and allow wrapping; don't shrink it to unreadable type or crop words. If it can't fit at a readable size, move the text into normal flow just below the image, without duplicating it or changing its document order. Check this fallback on a narrow view and with a deliberately long title. Start with one text layer: no arbitrary layer stack, rotation, blend modes, or drag-anywhere offsets.

## One document revision, two views

**Recommendation:** store structured layout with the same saved Build revision as content. Use the existing document save, version/conflict and recovery pathways. Prefer a structured editor representation if that path can retain it end to end; if it cannot, use a versioned layout record bound and saved atomically to the same revision, keyed by durable block identities. The design spike must compare these paths before any schema change. Never make local browser state the saved layout or infer structure back from visual coordinates.

Semantic Markdown follows the ordered block stream. It contains no resize measurements or invisible guides; a table still exports as table content, not page geometry. A resize-only save should leave semantic Markdown, evidence text and order unchanged; an explicit reorder updates the ordered stream. Existing exact revision citations must still reopen their original evidence. Existing Markdown-only revisions reopen in normal flow with no conversion on read.

Draft identity must include the layout, not just the Markdown. At the audited reconciliation pin, equal exported Markdown can be used as evidence that a dirty draft is a stale post-save overlay. A divider-only edit is the decisive counterexample: it must mark the draft dirty, survive leaving and recovery, save and reopen faithfully, and not overwrite a newer revision. Check both layout and content identity before dropping a recovered draft. Do not silently discard unsupported structured content or guess which block a stale layout referred to.

## Slices and evidence

1. **First useful slice: actual mixed-content Build section.** Add a two-slot row, move existing art beside editable prose, snap the divider and resize the image. Save and cold reopen. Undo/redo both actions separately. Verify keyboard use, narrow-screen stacking, and exact semantic output and citation reopening. In the same slice test a slot with a real table and callout; no special layout adapters for them. Make identical-Markdown layout edits and stale-revision handling part of the release gate, not cleanup.
2. **Finish the row controls.** Prove independent row splits (including three slots), Auto and minimum heights, and guide/border/clean states. Dogfood table / artwork / table in a single row and compare with the three-row layout. Prove that growing or shrinking content doesn't clip or stretch it and that old documents still edit normally.
3. **Prove the image + text stack.** Add a title to existing art, change its anchor/backing, then save and cold reopen. Check undo, keyboard editing, readable contrast, long-title fallback, and exactly one copy of the title in the accessible reading order and semantic export. Changing only the anchor must survive draft recovery without changing the evidence text. Do not make layering a prerequisite for the first mixed-content slice.
4. **Prove print separately before promising it.** Compose a varied-height sticker sheet from individually addressable art. Check real printed scale, gutters, keeping each cutout together across page breaks, and no editor guides on paper. Start with the existing print path if it suffices. Treat cut lines, explicit physical sizes, pagination rules and automatic packing as separately justified capabilities. Printing is not a prerequisite to ship the first authoring slice.

Do not add arbitrary spatial placement, nested grids, new map machinery, table-as-layout, or a second page editor. The first slice succeeds when the author can compose and reopen a useful page, not just when one image can be dragged.

Implementation starting points: [existing image node](../../apps/live-control-ui/src/tiptap/extensions/MediaImageNode.tsx), [Markdown adapter](../../apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts), [draft reconciliation](../../apps/live-control-ui/src/workspaceDocument/reconcileLocalDraft.ts).
