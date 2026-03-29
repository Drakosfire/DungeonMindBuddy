# Multi-Session Document Splitting Guide

## Requirement

For frontmatter-based ingestion, any document marked `document_class: play` must contain a single session identifier:

- `session: <int>=1`

If a markdown file contains recap content from multiple sessions, it must be split into per-session files before ingest.

## Why

- Fact chronology depends on `asserted_in_session`.
- A multi-session file with one mixed body creates ambiguous provenance.
- Split files keep session-level evidence deterministic and auditable.

## Required Frontmatter for Play Documents

```yaml
---
title: "Session 8 - Captain Lysandra Quest"
document_class: play
canon_layer: campaign
campaign_id: longmont-c1
session: 8
source_class: observed_session_recap
---
```

## Splitting Workflow

1. Identify session headings in the source document (for example `### Session N`).
2. Create one output markdown file per session section.
3. Add required play frontmatter to each output file.
4. Keep only the content for that session in each output file.
5. Reclassify the original mixed file as:
   - `document_class: reference`
   - `source_class: ledger_or_dossier`
   if you still need it for non-temporal reference.

## Practical Tooling

- Session heading discovery:
  - `rg "^### Session" "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md"`
- Validation smoke run:
  - `uv run pytest tests/ingestion/test_frontmatter.py tests/test_chunker.py -q`

## Minimum Done Definition

- At least one representative mixed campaign file is split into per-session files.
- New per-session files have valid frontmatter and pass ingestion tests.
- Mixed source file is no longer ingested as `document_class: play`.
