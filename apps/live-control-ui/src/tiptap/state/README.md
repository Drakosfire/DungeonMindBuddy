# Tiptap local working-board state

This directory owns the browser-local persistence contract for the isolated
Tiptap callout spike.

## Data flow

```text
Tiptap editor JSON
  -> schema-versioned localStorage working state
  -> semantic Markdown exporter
  -> read-only Markdown preview/copy
```

The Tiptap JSON is the editable source of truth. `exported_markdown` is derived
from that JSON and stored beside it so the current export can be inspected or
copied without contacting a server.

## Boundary

- The stable key and `dmb_tiptap_working_board_state_v1` schema are defined in
  `tiptapLocalState.ts`.
- Invalid or obsolete stored values are ignored and starter content is loaded.
- Editing and resetting write only to `window.localStorage`.
- This state does not call the live API, write corpus files, import Markdown,
  synchronize across browsers, or resolve conflicts.

A later backend-write slice may submit `exported_markdown` through explicit
prepare/commit endpoints. It must not treat browser-local Tiptap JSON as corpus
authority.
