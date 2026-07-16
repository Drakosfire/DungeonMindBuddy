# Workspace document local state

This directory owns the browser-local persistence contract for authored
workspace documents (Plan boards and Tiptap runbooks).

## Data flow

```text
Tiptap editor JSON
    -> schema-versioned localStorage working state
    -> semantic Markdown exporter
    -> registry-authorized prepare/commit write
```

The Tiptap JSON is the editable source of truth for the local draft.
`exported_markdown` is derived from that JSON. Durable identity and publish
path come from the server workspace document registry
(`Docs/Design/CONTRACT-workspace-document-identity-v1.md`).

## Boundary

- Storage key: `dmb.workspaceDocument.<documentId>` (opaque UUID).
- Schema: `dmb_workspace_document_local_state_v2` in `tiptapLocalState.ts`.
- Stored `document_id` must match the loaded registry descriptor; mismatch
  resets to starter content. Old semantic-ID / v1 keys are not dual-read.
- Editing and resetting write only to `window.localStorage`.
- This state does not invent campaign/session/kind from the ID, call the live
  API on its own, write corpus files, or synchronize across browsers.

Markdown prepare/commit submits `document_id` + markdown only. Title and
`target_relpath` are resolved server-side from the registry.
