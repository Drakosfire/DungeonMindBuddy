# BUILD: save body edits while preserving imported YAML metadata

Status: ACTIVE — PRIME solo implementation; ARCHITECTURE independent review.

Base `52e6598151a527e88c005049fbbbf9decc58b11d`; branch `codex/build-preserved-frontmatter-save`; non-serving checkout `/tmp/prime-recap-mention-boundaries`. Serial one PR. Current open work/leases inspected: DOGFOOD owns six UI welcome paths, not this writer. The disposable actual-Mirathorn historical-edit witness at operational pin `10b1f9cd06d1e926ae13c582dae30c698ca457a3` reproduces ordinary prepare refusing the unchanged source header delimiters at lines1/11. Retained files and APP rows are unchanged.

## Invariant / exclusive write set

Existing worldbuilding-source authoring may preserve an existing recognized leading YAML envelope byte-for-byte and edit its supported Markdown body. Resolve original bytes under the existing exact revision/file-state CAS. Do not newly author, remove or replace the envelope through this body-edit exception. Match the frontend's recognized leading envelope, including LF/CRLF and key discrimination. Retain full checking for malformed/unclosed or added headers, later thematic breaks and unsupported body content. Diagnostics retain full-source line numbers. Import eligibility, revision/file-state tokens, atomic save/rollback and Plan behavior remain unchanged.

- `Docs/Plans/HANDOFF-BUILD-preserved-frontmatter-save.md`
- `apps/live_control_server/services/tiptap_markdown_write.py`
- `tests/test_tiptap_markdown_write.py`

## Verification

Owning prepare→commit→reopen with unchanged header/body edit and exact newline fidelity; changed/added/deleted header, malformed/unclosed envelopes, later lossy content with exact original line numbers, stale CAS and import behavior. Reproduce failure on accepted base. Run affected writer and historical-source tests, inspect cumulative diff, Ruff/diff check, commit/push/open one review PR. Independent ARCHITECTURE review required before PRIME merge. No provider calls, serving changes, actual Mirathorn edit, extraction or retained World/APP publication in this implementation slice. Resume the isolated actual-source lifecycle proof only after acceptance under a new matched runtime pin.
