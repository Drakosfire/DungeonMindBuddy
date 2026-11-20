# INGEST: complete recap relationship responses

Status: SETTLED. Merged #1209 as `de4100b6c1b9ac8e5e586d112d0bdd0880f6834d` after independent review of `7c55646f83297a9a18c0045119f2bd75418bb253`. Implementation lease ended; runtime rollout and semantic acceptance remain separate.
Base: `c6db599311209b434b830f495b2df35b8f9dbb92`.
Lane: `codex/recap-edge-response-capacity`, `/tmp/prime-recap-mention-boundaries`.
Topology: serial successor; solo PRIME implementation, ARCHITECTURE review.

## Capability and evidence

Ordinary recap GE execution selects the adapter's existing 16384-token edge-only
output capacity. Other passes retain 8192, profile-derived invocation budgets,
120s per-call and 480s run deadlines, no provider fallback/transport retries.
A real Session29 attempt exhausted 8192 twice; a controlled followup reused six
verified completed responses, changed only the edge capacity, and completed edge
plus party fill. It produced a reviewable candidate, still HELD for independent
source-fidelity findings. Larger output capacity proves completion, not truth.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-INGEST-recap-mention-boundaries.md` (settle merged lease).
- `apps/live_control_server/services/graph_preview_runner.py`
- `tests/test_recap_generationengine_default.py`

DOGFOOD owns UI work on disjoint files. The prompt-only experiment uses another
checkout and private evidence directory, with no serving runtime or publication.
No provider call or retained data mutation in this implementation slice. Prove
actual ordinary service→GE edge request capacity and unchanged node settings.
