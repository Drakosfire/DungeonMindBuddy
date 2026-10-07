# HANDOFF — SERVER: recap candidate edge tuple correction

**Status:** ACTIVE — PRIME authorized this relation-only implementation after the APP-STATE basis contract and ARCHITECTURE relation review.  
**Base:** `main@78760713f0b1bd80fe4b114362f83c4302896a37`  
**Branch:** `codex/demo-recap-relation-correction`  
**Checkout:** `/tmp/dmb-demo-relation`  
**Topology:** Serial. RAKE's source-authority repair is the predecessor sharing `apps/live_control_server/services/extract_promote.py`; re-anchor after it merges and PRIME returns that file. One implementation PR for this slice. PRIME owns review and merge.

## Primary question

Can the GM-only recap-candidate correction endpoint repair a small set of known relationship tuples while proving exact preimages, endpoint identity, candidate predicate validity and current native admission, then keep the derived child held for whole-child semantic review?

## Accepted contract

- Add request schema `dmb_recap_candidate_correction_request_v3` to the existing endpoint. Each `edge_tuple_replacements` entry names one `edge_id`, its exact four-field `expected_tuple`, and a different four-field `replacement_tuple`: `from_node_id`, `relationship_type`, `to_node_id`, and `label`.
- Preserve the edge ID, evidence references, and every other candidate field. Endpoints must resolve uniquely to existing candidate nodes. The preimage must match the frozen candidate exactly.
- Validate the whole batch before child creation. Any invalid, stale, ambiguous, duplicate, unknown, unmapped or inadmissible entry rejects the batch with per-entry diagnostics and creates no child. The request ceiling of seven entries is a structural limit; it does not establish eligibility.
- Both `validate_edge_predicate` and the current native vocabulary and endpoint-kind admission mapping must accept every replacement. No automatic reversal, arbitrary JSON patch, or edge omission is included.
- The derived candidate uses a V3 manifest and V4 semantic basis, replay-verifies against the frozen parent and preserves source/span pins. It remains held until explicit whole-child semantic review. AppState records the decision through its existing CAS; no database migration or native World write is added.

## Write lease and exclusions

DEMO's current write set is this handoff plus:

~~~text
apps/live_control_server/models/extract_promote.py
apps/live_control_server/routes/extract_promote.py
apps/live_control_server/services/recap_semantic_candidate_correction.py
apps/live_control_server/services/recap_semantic_disposition.py
src/application_state/ingest/service.py
tests/application_state/test_ingest_run_postgres.py
tests/test_recap_semantic_candidate_correction.py
~~~

`apps/live_control_server/services/extract_promote.py` is temporarily excluded from DEMO's write set and exclusively leased to RAKE for frozen-source/span and review-package metadata resolution. DEMO's four-line V4 basis/CAS dispatch hunk is preserved in `/tmp/dmb-demo-extract-promote-dispatch.patch`; edit or apply it only after PRIME returns the file lease. RAKE also owns `apps/live_control_server/services/promotable_ingest_run.py` and its focused tests.

This slice does not change source artifacts, corpus content, provider behavior, runtime configuration, persistent runtime state, native Graph data, database schema or migrations. Synthetic test fixtures use temporary directories.

## Pinned source evidence

RAKE audit packet SHA-256: `ef89c92286b2407ce76f09b900b685c4bfecf133fb65a191a043a71cd116b1f3`.

- Session 26 run `aa9d8284-b603-493c-ad79-b7f997e39fc3`; candidate `ec3c4e670d89bda5658a5a93e647b851dcbf2869dac72ba7dd34ec97482bb77b`; span index `bc93e543e0c80a36f8d2368bcaa7e7587469240ef70993b4a5be453ff246166e`; source `6ce8492d3f7168c6fa75fc6a3a2962fdcaa3dd4bcc165a9667555f252a2ef8e7`.
- Session 27 run `084b3237-1fce-4a40-b8eb-eed7846a5bc4`; candidate `f323a7464b301b507529923833d959ee044a8c9ca042ce38a082cc6769234d37`; span index `e4019b7492d00818f9b0ef24a7cfb782218cf7c638bc7cefb6d658556c14e0b7`; source `740dcd285ee5e630ad84e3b5617374b99126be1784e003dd02e7878fa013b4ad`.
- The seven Session 26 `part_of_group` edges are not currently admissible because the native mapping marks that predicate unresolved; only three have direct membership wording. Session 27 audit targets include `edge-001` (`leads_to`) and `edge-028` (`possesses`) subject to current admission checks. The proposed omission of `edge-005` is outside this slice.

These hashes identify immutable audit inputs; no candidate or source artifact was altered.

## Deferred Session 13 intake

After the Session 26/27 correction mechanism settles, preserve and resume the separate read-only audit packet at `/tmp/prime-c1-session13-audit.json` (SHA-256 `be186044b63aa31a1529ae86924118f37c23182b4590856500e6acbb3d11cec5`). Its normalized-source identifier begins `ca6e` and differs from registered `55b65`; do not silently substitute it. The packet reports 15 quote failures and identity/semantic holds, with exact matches to native PCs, Thalia, Wolf, Tealeaf, academy and guards still requiring resolution. Its native projection is `/tmp/prime-current-native-projection.json` (SHA-256 `0fd0fa64c223b3ed5e79f4d5d639cd5dcfac39d3382cc0c1c6b794ac1cd50e37`, head `680c2460`). This is queued evidence only; it does not change this slice's write lease.

## Acceptance and verification

Before opening the PR:

1. Re-anchor to current `main` after the serialized RAKE repair and obtain PRIME's return of `extract_promote.py`; reapply and inspect the preserved CAS-dispatch hunk.
2. Pass the relation replay, all-or-nothing rejection, endpoint/catalog/native-admission, held-child and exact-basis dispatch tests. The AppState V4 CAS test must pass against its authorized disposable PostgreSQL boundary.
3. Run scoped Ruff and `git diff --check`; inspect the exact cumulative base-to-head diff and AppState basis boundary. PRIME routes the independent AppState review on the exact head.
4. Open one PR after the serialized predecessor settles. Do not merge from this lane.

Evidence at `78760713` so far: relation-correction tests pass **17**, with only the temporarily leased V4 dispatch test deselected; semantic-disposition tests pass **19**; the AppState V4 CAS/manifest allowlist test passes **1** against the existing disposable `127.0.0.1:54329` target with host access; scoped Ruff and `git diff --check` pass. Both Python suites use the pinned DungeonMind source archive at commit `7c69e447f6d4acc963ac09c6fb9cb48cc1c5b9cc`, verified against its Git blob. The direct AppState basis validator positive, malformed-manifest and overlong-manifest checks pass in the relation suite. Remaining implementation verification is the V4 dispatch test after file return, followed by final cumulative diff review and PRIME/AppState review; these are not acceptance claims.
