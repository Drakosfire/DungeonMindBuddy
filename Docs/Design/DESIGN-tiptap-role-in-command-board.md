---
document_id: dmb-design-tiptap-role-command-board
title: "DESIGN — Tiptap role in the DungeonBuddy Command Board"
document_class: design
status: living decision record
created_at: "2026-06-15"
last_updated_at: "2026-06-15"
related:
  - Docs/Design/DESIGN-tiptap-command-board-architecture.md
  - Docs/Design/DeepResearchTipTapGuide.md
  - Docs/Design/Mastering Tiptap’s AI Toolkit.md
  - Docs/Design/DESIGN-mireward-command-board-shell.md
  - Docs/Plans/HANDOFF-composable-editable-command-board-research.md
---

# DESIGN — Tiptap role in the DungeonBuddy Command Board

## 1. Decision

Use **open-source Tiptap** as the editable text and block-document kernel for the DungeonBuddy Command Board.

Do **not** depend on the paid Tiptap AI Toolkit for the core product direction. The paid toolkit remains useful as a reference architecture for selection-aware reads, structured edits, suggestions, and review flows, but DungeonBuddy should own those flows through its existing model, corpus, writer, and review contracts.

The role split is:

| Layer | Owner | Notes |
|---|---|---|
| Command Board shell | DungeonBuddy | Navigation, page toolbar, drawer/toolbox, combat-first layout, API wiring. |
| Editable prose and block composition | Tiptap | Rich text, selections, keyboard behavior, custom document schema, undo/redo inside editable documents. |
| Corpus truth and write safety | DungeonBuddy | Markdown corpus, writer allowlists, two-phase preview/commit, denied paths. |
| AI operations | DungeonBuddy | Selection reads, operation proposals, diff preview, human accept/reject, model cost tracking. |
| Combat and live widgets | DungeonBuddy | HP, initiative, clocks, timers, generated statblock promotion, local play state. |

Short form: **Tiptap owns editable text blocks; Command Board owns the workspace and canon boundaries.**

## 2. Why Tiptap

Tiptap fits the Command Board because it is a headless, schema-driven editor on top of ProseMirror. That lets DungeonBuddy define a constrained document model instead of accepting arbitrary HTML or building a raw contenteditable surface.

The properties that matter here:

- **Schema-first documents:** allowed nodes, marks, and attributes are explicit.
- **Custom blocks:** statblock references, NPC chips, roll-table embeds, callouts, images, and corpus links can be first-class document nodes.
- **Programmatic edits:** toolbar actions, user commands, and future AI edits can run through commands/transactions instead of rewriting DOM strings.
- **Selection awareness:** the board can support line/block/selection-level actions without replacing entire documents.
- **Headless UI:** the current Command Board shell decisions remain valid; Tiptap does not impose a toolbar or app chrome.
- **React compatibility:** a future React command-board module can embed Tiptap cleanly while preserving the current Vite/FastAPI serving model.

## 3. What Tiptap Is Not

Tiptap should not become the whole application architecture.

It is **not**:

- The global navigation shell.
- The command toolbox drawer.
- The combat tracker state machine.
- The dynamic corpus index/query layer.
- The canonical corpus writer.
- The statblock generator promotion authority.
- A reason to bypass two-phase commit.
- A reason to store every campaign source file as ProseMirror JSON.

The Command Board has already earned operator trust through fast, local, combat-first surfaces. Tiptap should enter as the editable document engine inside that product shape, not as a replacement product thesis.

## 4. Surfaces Tiptap Should Own

Good first-class Tiptap surfaces:

- Live notes.
- Session prep scratch.
- Scene beats and location blurbs.
- Roll table prose and table annotations.
- GM callouts and checklists.
- Draft recap prose before corpus write.
- Generated statblock drafts before promotion.
- Editable board pages composed from prose + references + widgets.

Surfaces Tiptap should only reference or embed:

- Combat tracker rows and HP state.
- Initiative ordering.
- Dynamic statblock/NPC/location/roll-table indexes.
- Toolbox controls.
- Timers, clocks, threat tracks, and other operational widgets.
- Canon statblock mechanical sheets.

For those operational surfaces, Tiptap can host a reference node or embedded widget placeholder, but the underlying state remains owned by the relevant Command Board module.

## 5. Canon Boundary

DungeonBuddy's corpus remains Markdown-first for campaign canon. Tiptap JSON is allowed as a working document format for editable board state, but it is not automatically canon.

The intended storage distinction:

| Storage class | Format | Examples | Save authority |
|---|---|---|---|
| Canon corpus | Markdown | Hubs, prep docs, recaps, timelines, static references | Corpus writer with allowlist + preview token |
| Board document state | Tiptap JSON | Composable session boards, editable scratch pages, local layouts | Command Board document store |
| Operational state | JSON/local state | Combat HP, initiative, toolbox state, open folds | Owning live module |
| Export/commit payload | Markdown diff or structured writer payload | Recap draft, prep append, timeline candidate | Existing writer or dedicated safe adapter |

This avoids forcing every keystroke through Markdown round-trip and avoids silently rewriting hand-authored corpus files.

## 6. Paid AI Toolkit Stance

The paid AI Toolkit is **not required** for the current architecture.

Open-source Tiptap plus DungeonBuddy-owned adapters can cover the core needs:

- Read selected content with `editor.getJSON()`, `getText()`, `getHTML()`, or Markdown serialization when validated.
- Capture selection/range from editor state.
- Ask the model for a structured operation or replacement draft.
- Apply proposed changes through commands or a command chain.
- Render previews with decorations, staged suggestions, or side-by-side diff.
- Commit only after human approval and the appropriate save adapter accepts the target.

The paid toolkit remains a product reference for the shape of good AI UX: small reads, structured edits, reviewable suggestions, and explicit accept/reject controls.

## 7. Product Rules

1. **Every editable block needs a visible save target.** The GM should know whether an edit is local scratch, board draft, generated artifact, or corpus-bound.
2. **Protected corpus files do not become casual inline-edit targets.** Dossiers, seeds, and statblocks stay denied unless a future explicit workflow changes that policy.
3. **At-table typing must not require an LLM call.** AI can assist, but editing and saving drafts must work without model latency.
4. **Custom nodes store semantic attributes, not rendered DOM meaning.** Node views make editing pleasant; persisted node attributes carry the product contract.
5. **Markdown export must be proven against the corpus shape before being trusted.** Tiptap Markdown support is useful, but not assumed byte-perfect for canon writes.

## 8. Open Questions

- Should the board document store live as `.board.json` files under a new allowed corpus-adjacent lane, or under app-local state managed by FastAPI?
- Which corpus paths are allowed to receive Markdown exported from board documents?
- Are images stored in git corpus, object storage, or both?
- Is collaboration a future requirement, or is single-GM local-first enough for now?
- What is the minimum acceptable Markdown fidelity for each save target: semantic equivalence, stable formatting, or byte preservation?

## 9. Next Design Dependency

`Docs/Design/DESIGN-tiptap-command-board-architecture.md` defines the concrete architecture: schema, custom nodes, storage, save adapters, AI operation protocol, migration path, and falsification tests.
