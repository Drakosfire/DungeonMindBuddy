# INGEST: whole-surface mention boundaries

Status: ACTIVE under PRIME's operator-authorized ingestion/authoring repair.
Base: `98dfb01ff9ba88364b0f329521beb7ba7bb2f01c`.
Lane: `codex/recap-mention-boundaries`, `/tmp/prime-recap-mention-boundaries`.
Topology: serial successor to merged #1207; solo implementation, ARCHITECTURE review.

## Invariant and failure cases

A free-text node surface must not link a prefix inside another word (tea/team).
Use the same correct word/backslash/bracket guards whether or not the caller also
supplies exact located mentions. Preserve Markdown/code protection, punctuation,
case-insensitive matching, ambiguity handling and deliberate located selections.
This changes display/authoring projections only; no source bytes, extraction
candidate, canonical identity, or retained World knowledge are rewritten.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-INGEST-recap-generationengine-default.md` (settle merged lease).
- `src/graph_memory/projection/markdown_mentions.py`
- `tests/test_recap_mention_word_boundaries.py`

DOGFOOD owns document-first Ingest UI; no overlapping files. The live GE process
uses a separate accepted-code checkout and owns its private candidate directory.
No serving port, provider, database or retained data mutation in this slice.

## Evidence

Reproduce the substring defect before fixing. Exercise both the neutral linker
and ordinary recap adapter, with/without located bindings, Unicode words,
underscores, escapes/brackets, standalone legitimate tea and protected Markdown.
Retain source text exactly when no legitimate node surface occurs. Review the
cumulative diff and existing characterization suite; intentional behavior changes
must be explained, not hidden by rewriting historical characterization evidence.
