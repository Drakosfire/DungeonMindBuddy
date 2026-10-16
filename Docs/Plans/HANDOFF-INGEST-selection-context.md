# INGEST: verified source and candidate selection context

Status: SETTLED. Merged #1211 as `8c13f6e93e9fa89e7b3fd6dcafb672a19d6454d5` after independent review PASS at `ee321a2a86d1955be08711c98fe5e09e2a2e8352` (29 independent context tests, 180 combined author tests). Implementation lease ended; rendered adoption remains outstanding.
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

## Implementation evidence

The real retained Session29 run `f43e48e6-c775-4960-824f-fb398fe50bb9`
revision 5 resolved the sleeping-children passage and `loc:warehouse` into three
candidate nodes and two incident edges under managed `elderwyld` → native
`eldyrwild`, binding version 1. Private local receipt:
`~/.local/state/dungeonmindbuddy/experiments/session29-selection-context-20261016/context.json`.
This is backend source/record resolution, not a browser or Agent-action witness.
The candidate and native World were not changed. New selection and existing
immutable-correction suites pass 180 tests together; Ruff/diff checks pass.
