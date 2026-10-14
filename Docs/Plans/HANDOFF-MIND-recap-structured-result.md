# MIND: consume structured extraction results

Status: ACTIVE. Owner: PRIME, working solo under operator instruction.
Authority base: Buddy `2a000cf762172675dc6e1d577eb3833c0c0bf484`.
Topology: serial; current open PR inventory inspected, no active extraction implementation overlap. Other stewards stopped.

## Outcome and contract

Buddy consumes GenerationEngine's schema-validated parsed object rather than reparsing its raw provider text. Preserve raw response evidence and independently validate the parsed object at Buddy's owning boundary. Existing plain-text results remain subject to JSON parsing. No changed schemas, provider routes, retries, publication, or serving processes.

## Write lease

- `src/graph_memory/extraction/bounded_recap_execution.py`
- `tests/test_bounded_recap_execution.py`
- this handoff

No runtime lease: non-serving isolated source; no retained database writes.
Verification: fenced raw text with valid parsed object succeeds and raw evidence remains exact; invalid parsed object fails schema checks; focused owning-client suite. Exact cumulative diff inspection required.
PRIME authors this change; independent human review required before merge during the solo experiment. Carry implementation through PR; leave merge held. Rollout follows accepted merge and a new candidate-only extraction case; current servers unchanged.

## Evidence

Private solo C1S16 experiment on the base stopped after three responses, 17.16 seconds. GE reported completed structured generation, but Buddy rejected collective raw Markdown-fenced text at JSON position zero. Three raw responses and ledger preserved locally. No World publication. This is an execution-contract defect, not evidence of full corpus readiness.
