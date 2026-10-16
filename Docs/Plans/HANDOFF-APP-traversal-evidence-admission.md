# APP: distinguish delivered traversal evidence from source-index hints

Status: ACTIVE — PRIME solo implementation; ARCHITECTURE independent review.

Base `65ab104be533854e72e5b5277e07744bcfe2e1f9`; branch `codex/graph-traversal-evidence-admission`; isolated non-serving lane `/tmp/prime-recap-mention-boundaries`. Serial, one implementation PR. Current open work inspected; DOGFOOD owns separate Ingest presentation/Combat paths. No shared runtime or extraction changes.

## Invariant

A Graph claim may use evidence actually delivered by a mapped, validated traversal event in the final producing envelope without opening every provenance passage. Source-index hints alone still require their matching successful included source reads. Compute traversal authority per claim's target and mapped event, never from the envelope's global evidence union alone. Preserve support-packet, revision, sufficiency, coverage, presentation, source-opening and persistence checks.

The ordinary Festival experiment at accepted main reached five acknowledged provider calls, two Graph operations and one successful passage read, but rejected a three-ref object claim because all refs absent from the initial input were classified as index-only. Reuse its protected saved response offline; do not replay inference or publish corpus evidence.

## Exclusive write set

- `Docs/Plans/HANDOFF-APP-traversal-evidence-admission.md`
- `Docs/Plans/HANDOFF-AGENT-uncapped-graph-consumer.md` — predecessor settlement
- `src/application_state/agent_conversation/types.py` — evidence authority classification only
- `tests/application_state/test_agent_conversation_service.py`
- `tests/test_agent_build_governed_graph.py`

## Verification and completion

Prove later target/three refs with one or no opened passage; truthful citations; reject overview-only/omitted event or refs/unrelated-event/foreign-revision authority. Genuine index-only read rules remain strict, including omitted/failed/foreign reads. Preserve mixed support and partial status. Exercise the actual parent presentation and producing authorization through host citation derivation, APP completion and fresh readback. Run focused regression, inspect cumulative diff, commit/push/open one PR. ARCHITECTURE reviews exact head before PRIME merge. Runtime follow-through requires a separate accepted pin. No provider calls, serving changes, retained World mutation or new schema/version in this implementation slice.

## Author evidence

Affected APP, governed Build and uncapped integration suites: 118 passed, one deselected known inherited submitted-intent fingerprint failure. Ruff and cumulative diff check pass. The new real parent-presentation/authorization/host-citation/APP/fresh-service-readback witness delivers three provenance refs from a later object, opens one passage, and exposes all three source targets with only one marked read. Replacing only the evidence derivation function with exact accepted base `65ab104b` makes that witness fail at out-of-dispatch evidence admission. APP cases retain index-only read requirements, mixed authority and partial coverage; omitted event/ref, unrelated target/event and foreign revision reject.

Protected captured real Festival response passes deterministic parsing as `graph_grounded_partial` with this repair; its original failed turn remains unchanged. No new inference, serving changes or corpus/World publication occurred. Logs remain local under `/tmp/traversal-evidence-{regression,base}.log`; private corpus response is not committed. This is deterministic repair evidence, not a new successful live or rendered turn.
