# INGEST: verified source and candidate selection context

Status: ACTIVE under PRIME's authorized ingestion editing scope, 2026-10-15.
Base: `d03fdb67da877c604e19242d0bdc254515fe89f7`.
Lane: `codex/ingest-selection-context`, `/tmp/prime-recap-mention-boundaries`.
Topology: serial successor; PRIME implementation, ARCHITECTURE independent review.

## Capability

Read-only POST on an exact extraction run resolves selected candidate nodes,
edges and optional frozen source passage for direct or conversational review.
Client revisions/digests are preconditions; server run/components/source remain
authority. Unicode source offsets are half-open code-point positions relative
to the unmodified source. Annotation is attributed operator input, never a recap
quotation. Return deterministic bounded neighborhoods, explicit truncation,
record hashes and a context digest. No model call, proposal application, candidate
child, native identity binding or World mutation. Relationship proposals consume
and revalidate this context in the next slice. Full editing remains outstanding.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-INGEST-recap-actor-source-handles.md` (settle #1210).
- `apps/live_control_server/models/ingest_selection_context.py`
- `apps/live_control_server/services/ingest_selection_context.py`
- `apps/live_control_server/routes/extract_promote.py` (authenticated read endpoint).
- `tests/test_ingest_selection_context.py`

DOGFOOD owns disjoint UI files in #1183/#1188/#1190/#1191. Other historical held
correction lanes are not active writers. Preserve serving runtimes, databases,
private corpus and frozen candidate. Verify real route/auth and source/record
validation, stale/cross-scope substitutions, emoji/combining characters, repeated
paragraphs, neighborhood truncation and no artifact mutation. DOGFOOD must later
witness real selected passage/node context; helper tests do not prove UI adoption.
