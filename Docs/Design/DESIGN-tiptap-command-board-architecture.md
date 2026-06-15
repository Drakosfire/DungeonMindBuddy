---
document_id: dmb-design-tiptap-command-board-architecture
title: "DESIGN — Tiptap Command Board architecture"
document_class: design
status: draft architecture
created_at: "2026-06-15"
last_updated_at: "2026-06-15"
related:
  - Docs/Design/DESIGN-tiptap-role-in-command-board.md
  - Docs/Design/DeepResearchTipTapGuide.md
  - Docs/Design/DESIGN-mireward-command-board-shell.md
  - Docs/Plans/HANDOFF-composable-editable-command-board-research.md
---

# DESIGN — Tiptap Command Board architecture

## 1. Architecture Thesis

The editable Command Board should use **Tiptap JSON as working document state** and **Markdown as corpus interchange/commit format**.

This is the central architectural split:

```text
             ┌──────────────────────────────────────────┐
             │ Command Board shell                       │
             │ nav · toolbar · toolbox · combat · APIs   │
             └──────────────────────────────────────────┘
                                │
                                ▼
             ┌──────────────────────────────────────────┐
             │ Tiptap editor kernel                      │
             │ schema · commands · selections · history  │
             └──────────────────────────────────────────┘
                                │
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                        ▼
┌───────────────┐      ┌────────────────┐       ┌──────────────────┐
│ Board JSON     │      │ Operational UI │       │ Corpus writer     │
│ draft/layout   │      │ widgets/state  │       │ preview/commit    │
└───────────────┘      └────────────────┘       └──────────────────┘
        │                                                 ▲
        ▼                                                 │
┌────────────────┐                              ┌──────────────────┐
│ Markdown export │ ──────────────────────────▶ │ Allowlisted paths │
└────────────────┘                              └──────────────────┘
```

Tiptap becomes the editable block engine. It does not replace the corpus writer, dynamic index services, combat tracker, or Command Board shell.

## 2. Runtime Layers

| Layer | Responsibility | Likely implementation |
|---|---|---|
| Shell | Page chrome, global nav, drawer/toolbox, route-level layout | Existing static shell patterns, later React module if approved |
| Editor host | Create/destroy editor, bind toolbar, expose commands | React component around `@tiptap/react` |
| Schema/extensions | Define allowed nodes, marks, commands, paste rules | Explicit extension list, not unbounded `StarterKit` forever |
| Node views | Render interactive embeds inside the editor | React node views only where plain rendering is insufficient |
| Document store | Persist board working state | JSON document store; local first or FastAPI-backed |
| Serialization | Import/export Markdown/HTML/plain text | Tiptap static renderer / Markdown package, validated per target |
| Save adapters | Route accepted edits to correct target | Local draft, board JSON, corpus writer, generated lane |
| AI operation adapter | Structured selection reads and staged edits | DungeonBuddy-owned model call + preview layer |

## 3. Document Formats

### 3.1 Tiptap JSON

Use Tiptap JSON for editable board state because it is schema-aware, deterministic, and well suited to programmatic operations.

Example shape:

```json
{
  "type": "doc",
  "content": [
    {
      "type": "sceneBeat",
      "attrs": {
        "title": "North gate pressure",
        "saveTarget": "boardDraft"
      },
      "content": [
        {
          "type": "paragraph",
          "content": [{ "type": "text", "text": "Keep the fight clock visible." }]
        }
      ]
    }
  ]
}
```

### 3.2 Markdown

Use Markdown for:

- Existing canon files.
- Human-readable exports.
- Writer payloads for allowlisted corpus paths.
- Review diffs before commit.

Do not assume Markdown import/export preserves byte identity. Validate it against real corpus files before allowing a save target to depend on it.

### 3.3 HTML

Use HTML for:

- Editor rendering.
- Clipboard interop.
- Preview surfaces.

Do not use unsanitized HTML as a persistence format.

## 4. Initial Command Board Schema

Start with a constrained schema. Add blocks because the product needs them, not because Tiptap supports them.

### 4.1 Core prose nodes

- `doc`
- `paragraph`
- `heading`
- `bulletList`
- `orderedList`
- `taskList`
- `taskItem`
- `blockquote`
- `horizontalRule`
- `hardBreak`

### 4.2 Core marks

- `bold`
- `italic`
- `strike`
- `code`
- `link`
- `gmHighlight`
- `reviewTag`

### 4.3 DungeonBuddy block nodes

| Node | Purpose | Persisted attributes |
|---|---|---|
| `callout` | GM-facing emphasis, warnings, rules reminders | `tone`, `title`, `saveTarget` |
| `sceneBeat` | Runnable beat in a session board | `title`, `status`, `sourcePath`, `saveTarget` |
| `gmNote` | Private note distinct from table-facing prose | `visibility`, `saveTarget` |
| `npcRef` | Link/chip/card for an NPC hub | `slug`, `displayName`, `corpusPath`, `mode` |
| `locationRef` | Link/chip/card for a location hub | `slug`, `displayName`, `corpusPath`, `mode` |
| `statblockRef` | Reference to statblock or generated draft | `creatureName`, `corpusPath`, `draftId`, `cr`, `mode` |
| `rollTableRef` | Reference to roll table source | `tableId`, `title`, `corpusPath`, `dice`, `mode` |
| `imageAsset` | Map/token/handout/media reference | `src`, `alt`, `provenance`, `storageClass` |
| `corpusMarkdownEmbed` | Read-only rendered corpus excerpt | `corpusPath`, `startAnchor`, `endAnchor`, `mode` |
| `combatWidgetRef` | Placeholder for live combat module | `combatStateId`, `mode` |

Node views can render cards, controls, and previews. Persisted attributes must remain semantic enough to render without the node view.

## 5. Save Targets

Every editable block or document should declare where it can save.

| Save target | Meaning | Commit behavior |
|---|---|---|
| `localDraft` | Browser-local scratch or transient at-table state | Save locally; no corpus write |
| `boardDraft` | Persistent Command Board document JSON | Save JSON through board document API |
| `sessionPrepAppend` | Append or update allowed session prep material | Preview Markdown diff, then corpus writer commit |
| `recapDraft` | Draft recap candidate | Route through recap-write workflow or dedicated preview |
| `timelineCandidate` | Candidate row, not automatic canon | Present decision surface, then append through allowed writer |
| `generatedStatblockDraft` | Draft generated by toolbox | Save in generated lane; promote through existing flow |
| `readOnlyCanon` | Protected corpus material | No inline write; allow copy/fork/draft actions only |

The UI should show the current save target near the editing surface. A hidden save target is a data-loss and canon-corruption risk.

## 6. Corpus Write Flow

Corpus writes stay two-phase.

```text
User edits Tiptap block
  → board stores JSON draft
  → user chooses "commit to corpus"
  → save adapter exports allowed Markdown payload
  → writer dry-run returns diff + confirm token
  → user reviews diff
  → writer commit validates token and file state
  → index refresh event reloads affected pane
```

Rules:

- No direct `Path.write_text` or client-side corpus writes.
- No commit to denied basenames such as dossiers, seeds, or statblocks unless an explicit future workflow changes the server allowlist.
- No silent conversion of full corpus files through Tiptap Markdown round-trip.
- Save adapters must name the target path and validator before preview.

## 7. AI Operation Protocol

The open-source path should implement the useful AI Toolkit patterns without depending on the paid package.

Agent/edit actions should follow this contract:

1. Read the current selection/range from Tiptap state.
2. Serialize compact context as JSON plus plain text or Markdown when useful.
3. Send a task to the model with the editor schema and save target constraints.
4. Receive a minimal structured operation, not arbitrary DOM code.
5. Preflight the operation with `editor.can()` or a schema validation pass.
6. Apply to a staged copy or decorate the live document as a preview.
7. Let the GM accept/reject.
8. Persist through the same save adapter as human edits.

Possible operation shape:

```json
{
  "operation": "replaceSelection",
  "contentType": "tiptap-json",
  "content": {
    "type": "paragraph",
    "content": [{ "type": "text", "text": "Rewritten text." }]
  },
  "reason": "Tightened the scene beat while preserving the threat clock."
}
```

The model should never be asked to rewrite arbitrary rendered HTML as the primary edit channel.

## 8. Node View Policy

Use React node views selectively.

Good node-view candidates:

- Statblock reference card with collapse/expand.
- Roll table reference with roll controls.
- Image/media block with preview and provenance.
- Corpus embed with source link and read-only marker.
- Combat widget placeholder.

Poor node-view candidates:

- Every paragraph.
- Simple callouts that can render through standard HTML.
- Pure formatting marks.

Node views are for editor experience. They are not the persisted source of business meaning.

## 9. Security and Import Policy

- Prefer JSON for trusted board state.
- Sanitize untrusted HTML before parsing or setting content.
- Treat pasted HTML as hostile until transformed.
- Use explicit paste rules for corpus links and entity chips.
- Keep dependencies current, especially Tiptap/ProseMirror packages.
- Use CSP-compatible rendering options when integrating into the live-control app.

## 10. Performance Policy

- Keep the editor isolated in its own React component.
- Subscribe only to needed editor state for toolbar/UI.
- Avoid one mega-editor for the whole campaign.
- Prefer multiple focused editors or board sections for large pages.
- Use React node views only when the interaction requires them.
- Profile rich block pages before declaring a schema acceptable.

There is no assumed first-party virtualization strategy. Very large, widget-heavy boards need their own proof before adoption.

## 11. First Proving Slice

The first implementation slice should prove the architecture without touching canon corpus files.

Recommended proving slice:

1. Add an editable `Live notes` or `Session scratch` board surface.
2. Persist Tiptap JSON as `boardDraft`.
3. Add `callout`, `npcRef`, and `statblockRef` custom nodes.
4. Export a selected range to Markdown.
5. Preview the Markdown diff against a synthetic or explicitly allowlisted target.
6. Reject any attempted commit without a preview token.

Falsification signals:

- Custom node JSON cannot round-trip through reload.
- Markdown export mangles common corpus patterns.
- Node views make the page visibly sluggish.
- The save target is unclear to the operator.
- The implementation pressures protected corpus files into casual inline edit.

## 12. Migration Map

| Current surface | Tiptap path | Notes |
|---|---|---|
| `live-notes.html` scratch | First editable board draft | Best initial target because it is already session-scoped. |
| Locations/NPC/roll-table indexes | Keep API-driven; add editable annotations later | Indexes remain read/query surfaces. |
| Markdown modal | Replace or augment with editable draft viewer | Canon embeds remain read-only until routed through writer. |
| Toolbox statblock draft | Use Tiptap for draft prose around generated mechanics | Promotion remains existing generated-lane flow. |
| Combat tracker | Embed refs/notes, do not rewrite tracker as prose | Combat state stays operational JSON. |

## 13. Verification Requirements

Before promoting Tiptap beyond a scratch surface, prove:

- JSON persistence survives reload and schema version checks.
- At least one custom node renders, edits, serializes, and reloads.
- Markdown export for supported nodes produces reviewable diffs.
- Denied corpus paths cannot be committed from the editor.
- Keyboard navigation and toolbar controls are accessible.
- A rich page with representative embeds remains responsive.

## 14. Open Decisions

- Board document storage path and API shape.
- Schema versioning and migration strategy for saved board JSON.
- Exact Markdown export policy per block type.
- Image storage authority and provenance fields.
- Whether collaboration via Y.js/Hocuspocus is in scope later.
- Whether Tiptap should enter through static Vite pages first or a new React module.
