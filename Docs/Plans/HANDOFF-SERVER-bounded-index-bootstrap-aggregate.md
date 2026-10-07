# HANDOFF — SERVER: bounded source-index bootstrap aggregate

**Status:** REVIEW READY — PRIME authorized this bounded product bootstrap slice after #1010 merged. **Base:** Buddy `main@228bbe6c4b41cce9323d71614153b7e69c6f0c2d` (#1010). **Core pin:** DungeonMind `5d4e98963991995bdc280e57df52b8d0fe8de79e`. **Topology:** serial predecessor to a separate APP-STATE V2 completion-admission contract; #1007 UX and #826/#917 parked work have no write lease here. PRIME owns review and merge.

## Primary question

Can a saved-Plan turn freeze the exact complete bounded native source index as candidate metadata, while keeping initial claim retrieval, provider dispatch, source-read admission, and coverage semantics tied to their existing authorities?

The SERVER resolver must request the index at the same exact Graph revision and scope as initial search. Overflow, stale snapshots, incomplete tuples, or a disagreement between an initially readable pin and the index fail before provider dispatch. A complete index supplies only opaque `(anchor, evidence, artifact, source revision)` tuples; it never opens content, creates a claim, marks evidence sufficient, or grants a source read by itself. Actual source IO still needs an anchor admitted in the active retrieval session and a durable V2 authorization before the read.
The reusable source-session handle must bind the exact Plan Markdown bytes as well as submitted request and Graph revision, so a changed Plan projection cannot reuse a prior session's claims or anchors during bootstrap reconstruction.

## Receipt contract

For a complete nonempty index, `candidate_evidence_ref_ids` becomes the sorted union of initial and indexed evidence IDs as required by APP-STATE V2's frozen scope validator. Set `selection_policy_version=parent_initial_retrieval_with_bounded_source_index_v1`. Compute `retrieval_packet_sha256` over one canonical composite containing the exact initial claim packet, an explicit bounded-index commitment version and count, every exact sorted index tuple, and that selection policy. Keep `dispatched_packet_sha256` over only the actual initial provider packet. Initial assertion/relationship candidates, fact sufficiency, coverage, and assembled dispatch membership remain based on initial retrieval and its provider envelope. An index-only candidate leaves the initial packet omitted as insufficient. Existing no-index V1 behavior retains its original selection policy and packet hash.

## Write lease and stops

Expected paths: `apps/live_control_server/routes/agent.py`, `apps/live_control_server/services/agent_turn_service.py`, directly owning tests in `tests/test_agent_turn_route.py` and `tests/test_agent_turn_service.py`, and this handoff. Do not edit APP-STATE validators/migrations, Core, Hermes, UI, provider prompts, dependency pins, or runtime data. A required public receipt schema change, claim admission from index alone, automatic source session expansion, or completion acceptance for index-only evidence is a stop/split signal. #917's route/service paths overlap historically but it is a parked prototype; no concurrent writer is authorized. #1007 changes only Plan conversation UI and its handoff at its current reviewed increment.

## Witness

Prove complete/index-only, overflow, stale/mismatched initial tuple, composite hash sensitivity to any index tuple/version/policy change, unchanged initial dispatch and sufficiency, same-key frozen replay, and no content IO from index alone. Run focused route/service tests, applicable full Python test/lint gates, and exact cumulative base→head diff. Report limits. Push one focused PR to PRIME without merging or live action.

**Implementation evidence:** The real pinned native Graph route and disposable PostgreSQL fixture passed, including a complete index with a noninitial eligible anchor, overflow and mismatched-index pre-dispatch refusal, candidate union, exact composite digest, sensitivity to a source-revision tuple change, unchanged initial insufficient/omitted dispatch, replay, and V2 provider authorization failure. The route/service/direct-source owning suite passed `110 passed`. Changed Python paths passed Ruff; `uv lock --check` and cumulative `git diff --check` passed. The isolated environment installed Core at the exact `5d4e989` Git pin and checked-in patched Hermes source. Repository-wide Ruff still reports 1,434 inherited errors outside this diff. A repository-wide pytest collection attempt stops in `tests/test_graph_authoring_overlay_projection.py` because the inherited `graph_memory.projection.recap_projection` module is absent; no full-suite pass is claimed. The disposable PostgreSQL cluster ran only under `/tmp` on port 54349; no live app-state or Graph database was touched. No provider or runtime request was sent.

**Deviation:** The source-session handle now includes a digest of exact Plan Markdown bytes alongside request and Graph revision. Without this, a changed Plan projection using the same turn ID could reuse stale claims from a prior session; the route test exposed that failure. This remains within bootstrap reconstruction and changes no public wire shape.

**Successor limit:** This PR does not relax APP-STATE V2's completion check for evidence obtained through a successful indexed source read. Until that separate reviewed contract lands, index membership alone cannot produce a newly admitted Graph claim or opened citation. The acceptance token for this slice is `SERVER_BOUNDED_INDEX_BOOTSTRAP_AGGREGATE_ACCEPTED`, subject to PRIME exact-head review.

**Exact implementation code head:** `456c249e74e97da5ffec673516384569e61f76ce`, tree `562c2fd9654e00b9b13629419be603854bf9da62`. Its cumulative diff from exact base `228bbe6c4b41cce9323d71614153b7e69c6f0c2d` changes only the four leased paths. Buddy `origin/main` remained that base when this handoff evidence was recorded. The final PR head is the subsequent handoff-only evidence commit.
