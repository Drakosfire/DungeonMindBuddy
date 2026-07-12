# HANDOFF — PR006D3 — `/ingest` review and activation UI

> Status: SUPERSEDED / DO NOT DISPATCH
> Superseded: 2026-07-12 after PR006D2 merged
> Replacement: [`HANDOFF-pr006d3a-ingest-bootstrap-review.md`](HANDOFF-pr006d3a-ingest-bootstrap-review.md)

The original handoff combined two independently useful and independently risky capabilities:

```text
inspect the exact approved bootstrap memory
publish the bootstrap through prepare + confirm
```

That boundary is too broad for one implementation PR. The read-only contract/rendering risk must be reviewable before the irreversible publication interaction is introduced.

Dispatch **PR006D3A** first:

> An `/ingest` user can inspect the approved Eldyrwild bootstrap memory so that activation is understandable before any write is offered.

PR006D3A consumes only:

```text
GET /api/live/world-graph-bootstrap/status
```

It must not add prepare, confirm, actor, proposal, token, or publication behavior.

A separate **PR006D3B** handoff may be written only after D3A merges and the design/review owner re-anchors on the resulting `/ingest` surface. Do not infer or implement D3B from this superseded document.
