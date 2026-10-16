# Build host-derived citation evidence

- Status: ACTIVE; PRIME solo implementation, ARCHITECTURE independent review.
- Authority: active Mirathorn lifecycle goal; architecture advice after the retained Thalia citation failure.
- Base: Buddy origin/main `fc1daff4b7fc8f6ba7d35445dd22e9fca15f6d49`.
- Branch: `codex/build-host-citation-evidence`; checkout `/tmp/prime-recap-mention-boundaries`.
- Topology: parallel-independent of DOGFOOD Ingest PRs #1235, #1237, #1244, #1251; their write paths inspected and disjoint.

## Outcome and contract

Build Agent selects exact admitted Graph targets and writes prose without retyping long evidence identifiers. Parent supplies sorted evidence references and revision from complete per-target records actually present in the producing provider envelope. Existing durable completion schemas, producing-event binding, source-read inclusion, and APP validation remain authoritative. Plan wire behavior is unchanged.

Initial support derives only from the verified initial provider packet, exact per-target declared references, and admitted anchor mapping. Expanded support derives only from exact complete delivered records/reassembled fragments and their complete delivered anchors, never discovery views, cumulative claim ledger, packet-wide evidence unions, or all effective pins. Conflicting per-target closures fail ambiguous. Unknown targets, foreign revisions/envelopes, partial records, and model-supplied reference fields fail closed. Raw rejected drafts stay retained. Semantic entailment remains separately reviewed.

## Exclusive expected write set

- This handoff.
- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/graph_tool_presentation.py`
- `tests/test_agent_build_governed_graph.py`
- `tests/test_graph_tool_presentation.py`
- `tests/test_build_host_citation_evidence.py`

## Verification and holds

Prove real governed Build persistence with initial and expanded targets, disjoint evidence sets, multi-ref records, partial/reassembled pages, omitted source reads, ambiguous closures, unknown targets, forbidden model refs, and old-envelope separation. Verify Plan regressions unchanged. Review exact cumulative diff and open one PR; independent review before merge. No serving, provider, corpus, schema or retained World writes in this lane. Runtime adoption and ordinary live question follow reviewed merge separately.
