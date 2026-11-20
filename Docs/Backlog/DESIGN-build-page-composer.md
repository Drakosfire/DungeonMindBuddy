# Build page composer specification

**Status:** Proposed specification, ready for design review. This does not activate implementation, change the roadmap, or authorize a storage migration.

The original first-slice language below is design context. The [backlog evidence reconciliation](../../Backlog.md#idea-high-priority--shared-grid-page-constructor) distinguishes merged manual foundations from still-open print, agent-directed and broader acceptance work.

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

## Implementation contract (proposed)

### Editor schema and invariants

The names below describe the logical contract, not assigned wire names. Use a versioned, allowlisted Tiptap/ProseMirror representation. Do not store DOM, arbitrary HTML/CSS, or pixel rectangles.

| Node | Required state | Children and constraints |
| --- | --- | --- |
| Layout row | Stable row ID, optional minimum height, line mode (guide, border, clean) | One to three ordered slots. A row is a top-level block; no row inside a row, table cell, or overlay. |
| Layout slot | Stable slot ID, positive integer width in a 12-unit row | Ordered ordinary Build blocks. Widths sum to 12 per row; minimum two units per slot; defaults 12, 6/6 or 4/4/4. Empty slots use a screen-only editing affordance, not semantic content. |
| Image/text stack | Stable stack ID, one of nine alignment anchors, padding and backing presets | Exactly one existing media image followed by one editable paragraph or heading. No nested stacks, tables or callouts in the text layer. |
| Existing blocks | Existing identity, provenance, and asset references when present | Do not allocate new world object / asset IDs for a move. Copy/paste assigns new composer IDs, stays inside document permissions, and keeps permitted asset references. |

Treat minimum height as a bounded editor attribute (proposed: 8 CSS-pixel increments, 0–640; zero means Auto), not as content height. Use allowlisted style tokens for guide/border, padding, backing and foreground; no new theming dependency. Validate unknown schema versions, duplicate composer IDs, unsupported child types, invalid order/widths and out-of-range values before committing. Do not silently flatten unsupported input.

### Editing behavior

- **Add / split:** insert a row at a block boundary. Splitting adds an empty slot without moving current content. Default split balances widths; keyboard transitions between permitted sizes. Do not split a table or selection across slots. Page composition is opt-in and only available on supported Build document kinds.
- **Resize:** use a transient preview during a pointer gesture and commit one editor transaction on release. Escape cancels; keyboard resize steps use the same bounds, and Reset restores Auto height or an even width split. Avoid starting an editor drag from a text selection, image handle or table divider.
- **Move:** drop before/after a block or into an empty slot. If a target is invalid, leave the document unchanged. Offer the same move through a keyboard-accessible block menu. Remove an empty slot directly; if nonempty, require explicit selection of a destination or a lossless unwrap. Unwrap emits blocks in their existing reading order. Do not introduce another delete path that discards hidden or off-screen content.
- **Layer:** select an existing image and choose **Add text over image**. Place the caret in the live text. A local style/position control changes anchor or backing, not text or alt text. **Unstack** restores the original image and text as adjacent blocks with their references intact. Image replacement, resize, and text editing reuse existing controls where possible. WCAG AA contrast is the target for the built-in backing/foreground pairs; verify readable keyboard focus in all three line modes.
- **Responsive:** determine stacking by the composer container, not the device. Ship a single initial rule: stack the whole row when a multi-column slot would be narrower than 12rem (with gutters accounted for). Preserve widths on return to a wider view. In stacked mode ignore authored row minimum height; use each table's own scroll region. The image/text stack remains overlaid only when padded, wrapped text fits without clipping, overflows or type reduction. Otherwise render the same text once below the image. DOM order stays image then text in both modes.

### Saving, recovery, and evidence

**Preferred implementation:** an optional, versioned structured editor payload committed atomically with the semantic Markdown through the existing Build document authority. It is the editable source for a composed revision; Markdown is its ordered evidence/export projection. Do not keep two independently editable copies. If the current owner supports only Markdown + same-revision structured metadata, use that route only if it can preserve identities and round-trip the known nodes; prove equivalence before choosing it. Do not add storage on the side or make a layout-only write bypass document compare-and-swap.

| Boundary | Required result |
| --- | --- |
| Open | Snapshot restores the exact revision's structured content and semantic fingerprint. When absent, use the existing Markdown editor. A client that cannot interpret a composed revision may read its Markdown but must not overwrite structured state. |
| Prepare / commit | Bind the exact document and World scope, expected revision, normalized composer payload fingerprint, and semantic Markdown fingerprint to the existing prepare/commit policy. A stale or invalid payload must not mutate the document or source projection. Reuse World grants and document visibility; no new media access. |
| Recovery | A stored overlay includes both base fingerprints and the full dirty state, including layout. An equal Markdown hash is not a clean signal when layout differs. On stale base, keep the local draft recoverable and offer the existing conflict flow rather than automatic overwrite. Test a server commit that succeeds before the local dirty flag has cleared. |
| Semantic projection | Traverse rows, slots, and blocks in document order. Strip all presentation metadata from the evidence path. Preserve table headers/cells, image references/alt where supported, and a single copy of overlay text. Reordering is semantic; height, width, guide mode, backing and anchor alone must not affect text bytes. |
| Citation and publication | Reopen citations to the existing immutable source/revision, not whichever layout is current. A layout-only save may advance the authored revision; do not automatically publish another source artifact or re-ingest a World. Verify unchanged admitted evidence and historical citations; retain existing authority and review behavior. |

Before implementation, trace a real Edge-like Build kind through prepare → commit → cold snapshot → source publishing. The existing route exposes Markdown prepare/commit and the client has Markdown-based draft reconciliation. Confirm which current routes accept actual tables, images and callouts on that same kind; older documented authoring modes reject some constructs. If the selected route can't save a required mixed block or cannot atomically retain the structured payload, record the owning contract gap and use an explicit storage/compatibility slice first. Do not bypass source policy, use export as persistence, or promise the round trip based on editor rendering alone.

### Acceptance and delivery sequencing

| Slice | Exact browser proof | Owning boundary checks |
| --- | --- | --- |
| A. Mixed-content row and save | Existing Build page stays editable, wrap prose + art in a two-slot row, resize both the slot and the image, add a real table and callout, keyboard move and undo/redo, narrow and restore width, leave with only a resize pending, recover, save and cold reopen. | Schema rejects malformed payload and wrong tenancy; save is atomic; stale concurrent resize fails without losing draft; old revisions reopen and prior quotes resolve. Verify Markdown byte equality after resize and intended order after move. |
| B. Row controls | Table / art / table in one row plus two other independently sized rows. Exercise tall content, Auto/reset, all line modes, keyboard controls and touch/stacking. | Editor transaction/history tests; rendered borders and edit guides are distinct; nested rows and invalid moves are rejected without changes. |
| C. Image/text layer | Place an editable title on existing art, move it, edit and undo, try contrasting and busy art, resize until it falls below the image, widen to restore overlay, save and cold reopen. | One accessible and exported text instance; correct asset/alt and reading order; preserve draft after anchor-only changes; semantic output and historical citation unchanged by presentation. |
| D. Print dogfood, separate decision | A varied-height sticker sheet from separate token assets with cuttable gutters; check actual paper or print-to-PDF at the intended size and page break. | No dotted editor guides; no split or clipped cutout. Make physical sizing, printed cut paths and pagination explicit only after testing the existing print path. |

No implementation, storage migration, roll-out, or roadmap activation is implied by this specification. Keep these slices serial unless independently scoped and authorized.

Implementation starting points: [existing image node](../../apps/live-control-ui/src/tiptap/extensions/MediaImageNode.tsx), [Markdown adapter](../../apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts), [draft reconciliation](../../apps/live-control-ui/src/workspaceDocument/reconcileLocalDraft.ts).
