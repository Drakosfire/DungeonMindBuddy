# AGENT — Jev source structural continuations

ACTIVE; PRIME solo, independent ARCHITECTURE review. Serial successor to merged Jev loop52e3ddfc5fb847080569832b1ae5c7951d1d870d. Base52e3ddfc5fb847080569832b1ae5c7951d1d870d; branch codex/jev-source-continuations; /tmp/prime-recap-mention-boundaries. Non-serving evaluation only; no runtime, DB or World write, no Luna. Open DOGFOOD Ingest leases do not overlap.

Write set: this handoff; evals/graph_memory_layer/jev_evidence_loop.py; tests/test_jev_evidence_loop.py.

Measured first Jev cases: Float1.094s/two rounds covers2/3gold; it selected a saved Build section containing only a heading. Council0.911s/two rounds covers9/10gold; it incorrectly accepted Elara-leading-council as evidence of the governing relationship. These are frozen source replay, not live DB or writer latency.

One capability: code follows explicit same-snapshot saved-section continuation IDs when the current unit contains only Markdown headings/whitespace. Record every action. Reject unknown, backward/overlapping, non-section continuations before inference; never repeat a visited action. No model picks a continuation merely to reach body text. Snapshot preparation derives continuations mechanically from source section order, not gold. Human requirement G2 is clarified to require an explicit governs relationship; no gold answer enters inference. Preserve original runs and source revision, classify revised-input runs separately.

Tests: heading-only chain reaches substantive body in one acquisition wave; substantive sections do not expand; invalid foreign/backward/cyclic pointers reject; owning trace records structural reason. Existing17controller gates continue. Independent review before merge. Measured successor records actual Jev decisions, input/output usage, selected passages, source coverage and false sufficiency; semantic review stays separate from quote coverage. No claim that a small pilot establishes general accuracy.
