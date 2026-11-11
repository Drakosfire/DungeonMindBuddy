# Verified source import

This serial slice starts from Buddy main ec646dab1. It reuses the existing
Build Import source flow and the existing server prepare and commit boundary.
Write scope covers the Build create/import control, Tiptap Markdown write
service, focused tests for both, and this handoff. No live runtime lease.

Build offers a Markdown file picker. It checks the extension, decodes UTF-8
strictly, and rejects blank text, PDF signatures and binary control characters
before opening a source or creating a World. The server checks text again
before document lookup in both prepare and commit. Accepted imports retain
the submitted text and existing source revision and admission rules.

Validate a renamed PDF, binary input, and byte preservation. Run the focused
Build UI and Markdown import tests. PNG, JPEG and PDF need their own byte
readers and ingestion consumers. The image classifier belongs after successful
decode and before model routing, with separate depiction and campaign use
results. Its decisions do not grant source admission.
