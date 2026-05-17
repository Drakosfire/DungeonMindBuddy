# PR43 artifacts

These are PR-scoped diagnostic artifacts, not canonical benchmark truth. PR43 changes rendering and canvas inspection only; it should not change retrieval/admission benchmark results from PR42 except for additive rendered-context fields.

## Scope truthfulness (important)

This repository **does not** ship the runtime Cursor canvas accordion/details UI component for PR43.
PR43 in this repo wires:

- `rendered_context_packet` data per question row/card
- `uiHints` (`Rendered LLM Context`, `details`)
- guardrail metadata declaring UI ownership boundary

The actual interactive accordion/details rendering is owned by the external Cursor canvas shell/runtime.
