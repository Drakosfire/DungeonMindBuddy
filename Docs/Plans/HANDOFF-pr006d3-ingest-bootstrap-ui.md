# HANDOFF — PR006D3 — `/ingest` review and activation UI

> Status: SUPERSEDED / DO NOT DISPATCH
> Superseded: 2026-07-12 after PR006D2 merged
> Replacement: [`HANDOFF-pr006d3a-ingest-bootstrap-review.md`](HANDOFF-pr006d3a-ingest-bootstrap-review.md)

The original handoff combined two independently useful and independently risky capabilities:

```text
inspect the exact certified bootstrap package
publish the bootstrap through prepare + confirm
```

That boundary is too broad for one implementation PR. It also risks treating the certified initial package as another run in the existing recap Graph Review pipeline.

Dispatch **PR006D3A** first, but only after its tracker re-anchor is merged:

> A GM can inspect the certified initial World Supergraph package in a distinct Bootstrap Activation Review gate so that they understand what may be published without entering or duplicating the ongoing recap Graph Review workflow.

PR006D3A is a separate top-level `/ingest` workflow. It consumes only:

```text
GET /api/live/world-graph-bootstrap/status
```

Its source of truth is `dmb_world_graph_bootstrap_status_v1` and the returned `BootstrapReview`.

It must not:

- load contribution bundles directly in the browser;
- reuse recap-run selectors, manifest paths, preview-union stores, gold/live lanes, or Graph Review state;
- add a bootstrap mode to preview APIs;
- add prepare, confirm, actor, proposal, token, acknowledgement, or publication behavior;
- suppress the existing Graph Review workbench when bootstrap status fails.

The existing recap/run Graph Review remains mounted and independently usable as a neighboring workflow.

A separate **PR006D3B** handoff may be written only after D3A implementation merges and the design/review owner re-anchors on the resulting `/ingest` surface. Do not infer or implement D3B from this superseded document.
