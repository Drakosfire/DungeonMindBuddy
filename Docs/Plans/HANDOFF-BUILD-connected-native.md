# BUILD: native connected-page creation

Status: ACTIVE for slice 1 only. PRIME owns design, implementation and merge under the operator's request to repair normal Buddy connected-page creation. Independent exact-head review is required. No runtime or provider lease is activated by this handoff.

## Outcome and topology

Three serial Buddy PRs, never stacked: (1) database-owned recoverable connected-page operations, (2) current native identity selection and reviewed publication, (3) normal Build-out orchestration and ordinary-control acceptance. Each successor starts from fetched main after its predecessor merges. Slice 1 does not claim to repair native publication. Retain existing Edge and Exchange writing and the old review draft; no fresh ingestion or manual Graph curation.

## Active slice 1

Existing buddy-context-loop checkout; branch codex/connected-page-operation-storage, base 81c0e9e8128b84348e6b74019f6d27a97ff06b81. Expected exclusive write set: this handoff, application_state/content/connected_pages.py, migration 20261105_0116_connected_page_operations.py, connected_page_authoring.py, the existing graph_object_authoring_commit.py recovery-only boundary, scripts/adopt_connected_page_operation.py, tests/test_connected_page_authoring.py, tests/test_build_destination_menu.py (the prior reader fence must remain an ancestor, not permanently be head), and focused operation-storage tests and their existing CI selector. Open PRs checked: INGEST lanes and REFERENCE design/retirement work have no overlap. No shared venv, live runtime, database or UI changes; tests use disposable APP PostgreSQL.

## Invariant and failure cases

The existing Content page owner retains page bytes and reserved page identity. A DB operation journal owns intent and durable phase recovery, serialized by operation ID across processes. Phase commits survive downstream failure; database absence never falls back to registry files. Preserve exact intent and existing publication receipts. Explicit one-shot adoption accepts only a completed historical operation verified against the existing publication owner and its exact retained page/source/World; incomplete historical operations require separate recovery review and remain retained as files; conflict must reject, never overwrite either operation or page. No directory discovery or implicit request-time adoption. Live services stop using file locks and operation JSON. Source verification, native authorization and page ownership checks remain in place.

Prove concurrent duplicate requests reserve one page, changed intent and foreign World fail closed, lost responses recover once, and newer source/page writing survives retries. Prove explicit adoption is idempotent, rejects changed state, and live reads cannot use a file in lieu of DB state. Review cumulative diff and owning mounted tests before push/PR; CI and independent review precede merge. Delivery/adoption requires a separately re-anchored exact runtime lease and retained-state checks.
