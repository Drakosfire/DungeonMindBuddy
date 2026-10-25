# BUILD: exact document source for governed authoring

Status: DELIVERED IN CODE, awaiting combined runtime delivery. #1723 merged at 9195d78397743dce812a545278eafa3454519b74 after independent exact-head approval f7a2b311f58768489d5cae522798b2a98764b8e4 and 108 passing tests. Successor: HANDOFF-BUILD-connected-page-operation.md. Independent design review approved OverMind 46012c83a1e90dae2ff5f4bc8ae7bfb235da78ea and this handoff at SHA-256 bea2998540f3557452ac6fe5215f62fe79f799c51b02a267b8ec15dcf6a69772 before activation.
Authority: operator's connected-page assignment, before resuming the paused broad goal. Cross-owner design: DungeonOverMind `Docs/Plans/HANDOFF-BUILD-connected-page-authoring.md` at pinned commit `46012c83a1e90dae2ff5f4bc8ae7bfb235da78ea` (PR #56).
Owner: PRIME solo; reuse `/home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy`, base e489c5e9beaa86a192c0ab211854b3398b47b0f3, branch `codex/build-document-authoring-source`; serial first of three planned capabilities. No overlapping open PR found after fetch. No serving changes or operator data writes during implementation.

## Invariant

An ordinary registered Build page can support an explicitly reviewed native object/relationship assertion without pretending to be an extraction Run. Add `documentSource` with documentId, revision and contentSha256 as exactly one of Run, Recap or document source. Server resolves an active committed World-scoped Build record and verifies bytes under its mutation lock. Persist an immutable body and span index before a confirmable prepare. The selector is signed into confirmation. Re-read exact frozen components, source ownership and managed/native mapping at confirmation; native publication/recovery remains existing prepare/commit authority. Later page edits do not rewrite historical evidence or make an already-applied operation impossible to recover. No arbitrary file paths, source selector fallback, automatic graph extraction or AI call. Permit relationship references to unique object proposals in the same sealed bundle, which the existing translator already resolves; reject missing, duplicate or mixed local/native references before native IO. This is required for the reviewed new-person/location bundle.

New connected-page creation and its UI/agent flow are later serial slices, not completion claims for this prerequisite. Original working draft handling belongs there: the new page's initial user-authored declaration is durably saved as a real registered committed revision with draft story authority before native prepare, and that exact revision supplies the native assertion source, while the originating working selection stays separately labeled and retained.

## Exclusive expected write lease

- This handoff.
- `apps/live_control_server/services/graph_document_source.py` (new, exact freeze/resolve).
- `apps/live_control_server/services/graph_object_authoring_prepare.py` (typed selector, resolve, sealed provenance).
- `apps/live_control_server/services/graph_object_authoring_commit.py` (exact selector verification/recovery).
- `apps/live_control_server/services/graph_run_registry.py` and `worldbuilding_source_span_read.py` (reuse immutable registered-document snapshots for historical citation reads without fabricating runs).
- `tests/test_graph_document_source.py` (new, registry/HTTP/native-port boundary tests).
- `tests/test_graph_object_authoring_prepare.py` only if compatibility expectations require update.

No Core/GE changes, lockfile/schema migrations, UI contract or generated client changes in this first prerequisite. No retained World mutation during tests. Implementation ends in tested exact cumulative diff, independent Bugbot review, commit/push/PR. PRIME merges only after applicable gates. Owning second slice consumes the source seam and settles actual merge evidence.

## Required proof

Real registered source and span verification through mounted prepare/commit using fake native authority only at the external port; object plus relationship local references; same exact confirmation recovers once. Refuse mixed selectors, missing/foreign World, invalid/stale initial revision/digest, wrong document kind/status, changed managed/native mapping, forged selector/token, corrupted frozen body/index and ambiguous occurrence. Historical source opens after source edit/reload and exact acknowledged/uncertain confirmation still resolves the sealed source. Preserve existing Run/Recap regression tests. No helper-only completion of connected-page experience.

## Pre-review evidence

Mounted HTTP tests use real file-backed Build registry, frozen body/index, occurrence verification, signed prepare/confirm and managed/native binding; only native authority/admission ports are fakes. The 108-test focused set covers new document-source behavior and existing Run/Recap/confirmation regressions. It proves two objects plus owns/operates in one publication, exact retry after later source save, response-loss recovery, historical passage opening, source/mapping/tamper refusals, immutable components and invalid local reference bundles. No UI, live native database or complete connected-page delivery is claimed.
