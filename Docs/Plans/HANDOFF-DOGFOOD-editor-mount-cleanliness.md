# DOGFOOD: editor mount cleanliness

Status: ACTIVE; explicitly activated by PRIME on 2026-10-14.
Base: 8cfba654cb25f2e264a3f64d69b0cd2eac011cef.
Branch: codex/editor-mount-cleanliness.
Checkout: /home/drakosfire/.codex/worktrees/editor-mount-cleanliness/DungeonMindBuddy.
Topology: serial, one PR; independent ARCHITECTURE review before adoption.

## Invariant and exclusive write lease

Opening or toggling the rich editor without a document edit must preserve clean
saved-source authority, exact exported Markdown, saved revision and digest. The
first genuine user transaction must still become dirty. Do not suppress real
edits, weaken exact equality, change serialization, overwrite existing drafts or
auto-save a normalization. Metadata-only editable-state changes are not edits.

Allowed paths:
- apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx
- apps/live-control-ui/src/tiptap/MarkdownEditorCore.test.tsx
- apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.markdownFidelity.test.tsx
- this handoff

Production authoring-hook changes require a precise scope amendment first.
No Build ingestion/controller/native binding, corpus, shared source authority,
schemas, lockfiles, private configuration or serializer changes.

## Ownership and failure critique

PRIME owns the disjoint native-source binding lane. The deployed 5202 reader
candidate at 69cb3ffc is read-only; 5876 is independent and untouched. This
implementation has no runtime lease to adopt itself before review/coordination.
No model calls, extraction or native publication are part of this slice.

Observed: merely entering Edit on the imported Mirathorn source reports unsaved
changes; the saved revision 2/hash remain unchanged. Installed TipTap defaults
setEditable's emitUpdate argument to true, while the shared authoring hook uses
nonprogrammatic updates to serialize and compare exact source bytes. Establish
an owning mounted reproduction before assigning the cause; do not infer it from
an isolated helper. Preserve existing dirty drafts and unsafe Markdown authority.

Required evidence: actual Read→Edit mounting with noncanonical saved Markdown,
unchanged editor JSON/source/hash/revision, editable toggles, first genuine
transaction dirty, existing shared authoring fidelity and editor regressions,
app TypeScript, cumulative base→head diff. Commit/push/open the assigned PR.

## Owning reproduction and repair evidence

The real authoring hook plus MarkdownEditorCore is mounted conditionally as in
Read/Edit, inside the same StrictMode used by the app. Synthetic saved source
contains CRLF frontmatter and noncanonical heading whitespace. On the base,
Read→Edit makes dirty true without a content edit; outside StrictMode the initial
mount stays clean but editable toggles reproduce the same defect. TipTap adds
schema-default null attributes on mount; comparisons distinguish those defaults
from an actual subsequent document change.

The only production change passes false as setEditable's emitUpdate argument.
No authoring-hook, serializer, exact-equality or authority logic changed. Existing
mount test now expects no artificial update, then verifies the first real update
is nonprogrammatic. The mounted regression verifies unchanged JSON after toggles,
exact clean local Markdown/state, first real transaction dirty, existing dirty
JSON/export retained through remount, unchanged CAS base/source snapshot, and
zero prepare/commit calls. Existing unsafe-source fidelity protections still pass.

19 focused Core/fidelity tests pass. App TypeScript and cumulative diff check pass.
No runtime adoption or browser/source Save was performed. Architecture review and
ordinary rendered acceptance of the approved runtime remain separate gates.
