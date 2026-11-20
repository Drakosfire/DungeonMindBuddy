# INGEST — preserve DOCX table content

Status: ACTIVE. The operator's Sizzek onboarding goal authorizes this bounded
implementation. Base `4715f169d28f2fc6cade2f883fba4730b67445e8`; isolated branch
`codex/sizzek-docx-tables`. Serial implementation slice; the hosted World design
PR #4240 is an independent, non-runtime design, not a parent. No other open
implementation PR identified for these paths.

## Scope and invariant

The existing local DOCX converter silently drops tables. Preserve table-cell
text in document order along with ordinary paragraphs, without silently
inventing a header. Preserve existing paragraph/heading output. Escaped pipes
and multiline cells must not become extra columns or rows. This is a text
conversion improvement, not hosted DOCX upload, image ingestion, general
Word-layout fidelity, source admission, Graph publication, or a change to
source-anchor authority. Unsupported nested tables must fail explicitly instead
of silently dropping content. Do not use the private Sizzek files as committed
fixtures or expose their content.

The real table witness exposed hyperlink-label text inside otherwise ordinary
cells; the existing paragraph renderer skipped those runs. Preserve hyperlink
labels in document order as text (without asserting link-target fidelity) in the
shared renderer, which is necessary to preserve these table cells. Add a
synthetic hyperlink regression alongside the table tests.

Exclusive expected write paths: this handoff, `src/ingestion/docx_converter.py`,
`tests/test_docx_converter.py`, and `tests/test_chunker.py` for the owning chunk
boundary. No database, production state, providers, external files, configuration
or dependencies. If accurate conversion requires other paths or semantic
contracts, stop and revise this scope before editing them.

Use synthetic DOCX files to test paragraph/table/paragraph ordering, cell text,
pipe and line breaks, and explicit unsupported nested-table handling; verify
the real `chunk_document` boundary retains content without changing its existing
source-anchor contract. Run the focused converter and chunker tests with the
locked Python environment, inspect the cumulative diff, and independently review
the exact head. Open or update the assigned PR; merge and deployment remain
separate authority. The goal continues through hosted import and the real private
World witness after this slice.
