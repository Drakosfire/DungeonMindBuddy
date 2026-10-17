# INGEST: recover exact candidate evidence references

**Status:** ACTIVE — PRIME re-dispatched the existing bounded #1244 slice after #1318 merged.
**Base:** origin/main@157f8d11e39772a7e857bc41e110479daa8d6ef7 (latest observed main after #1317 merged).
**Branch:** codex/ingest-candidate-evidence-ref-recovery.
**Checkout:** Existing isolated Ingest worktree; updates target the existing PR branch under an exact expected-head lease.
**Topology:** serial Ingest implementation; no second PR. PR #1318 passed PRIME review and merged at `1ed861d7c123fd62d7583204eff7f2236a5680e4`; PR #1317 then merged at `157f8d11e39772a7e857bc41e110479daa8d6ef7` with nine disjoint Build/Agent paths. Open #1235 (`codex/ingest-source-observation-review`) owns disjoint Graph Review/source-observation prepare UI and is not a dependency or part of this slice. #1237 (Ingest source navigation), #1251 (candidate readiness), #1256 (local navigation feedback), and #1257 (historical publication coverage) are merged; their paths remain separate from this package/test lease. Build publication-capability PR #1243 and Core description-withdrawal PR #1245 also merged before this base. No new runtime, database, or corpus owner is introduced.

## Objective

A retained Longmont C2 Session 29 candidate has ten unresolved evidence
references across eight shortened span IDs. Their quotes and line ranges match
the pinned normalized recap and canonical source-span index. The old report
warned about all ten but still marked the candidate valid; the manifest marked
it candidate-ready with only 144 of 154 reference occurrences resolvable, while
candidate diagnostics incorrectly said zero warnings and unresolved refs.
Current main promotes unresolved refs to validation errors, so a rerun stops
before readiness. Recover only references that can be proven against the exact
source; otherwise keep validation fail-closed.

## Invariant

- The registered source artifact, normalized recap bytes, and source-span index
  remain authoritative. Never infer an evidence location from an ID suffix alone.
- A legacy reference is repairable only when its source artifact identity is
  the exact source bound to the run, its shortened ID maps to one and only one
  canonical indexed span, and every supplied anchor quote occurs verbatim in
  that span's source text. Missing, ambiguous, cross-source, or mismatched
  evidence remains unresolved and blocks candidate readiness.
- Update all representations of a repaired reference (every span ref, display
  label, and source-anchor ID) consistently in the packaged candidate, while
  leaving the original extraction-run candidate immutable. If both span fields
  are present, every field must resolve to the same canonical span.
- The report records repair counts and source/target IDs so reviewers can see
  why an old candidate became admissible. Candidate and manifest diagnostics
  must agree with actual validation results.
- No model call, new extraction run, publication, persistent graph write, or
  5202/5204 action in this slice.

## Exclusive write set

- Docs/Plans/HANDOFF-INGEST-candidate-evidence-ref-recovery.md
- Docs/Plans/HANDOFF-INGEST-canonical-recap-text-to-category-passes.md (settlement update for merged #1110, included here)
- src/graph_memory/extraction/graph_ingest_packaging.py
- tests/test_graph_memory_category_graph_preview_runner.py

No model prompt/extractor, API, UI, persisted candidate, corpus, run manifest,
or database files are leased.

## Owning proof

- Unit coverage for exact canonical refs; unique shortened refs with matching
  quotes; wrong source, missing or duplicate spans, absent/mismatched quotes,
  malformed IDs, inconsistent secondary span fields, and multiple
  nested/top-level representations.
- Replay the retained Session 29 candidate and source-span index into a fresh
  fresh ignored directory inside this checkout, with `allow_llm=False`.
  Confirm the ten provable refs are canonicalized, the packaged run is ready,
  and the original retained files' hashes do not change.
- Re-run with one corrupted quote and one ambiguous/missing span; confirm the
  candidate remains failed and the report gives the unresolved reason.
- Run focused tests, typecheck/lint as applicable, inspect the cumulative diff,
  commit and push this bounded change, and open/update its PR. No merge without
  separate authority.

## Historical source-text handoff settlement

PR #1110 merged at f1ea2778a03e48ab0cb7be53fe990054b8ff8c87. Its code lease
ended; this implementation updates the stale handoff banner to record the
merge and preserve its original evidence.

## Verification checkpoint — 2026-10-16, rebased on main@494f9646

- The retained `longmont-c2/session-29` candidate has 59 nodes, 33 edges, and
  five beats. A fresh no-model replay of the actual retained candidate, recap,
  and canonical span index repaired 10 references across eight unique legacy
  IDs, produced `candidate_validation_ready`, and resolved 154/154 evidence
  references. The original candidate, recap, and span-index hashes remained
  respectively `8e7bb42d56f29c52d7b8f1b1f432a7888ea1d1355ce602ef8972503ba0ee5889`,
  `4f963656828b553f7919ee00d3304725ddff892a13651b989f99b9b649933796`, and
  `a94114e6aee71606e8d77aee42638657821ed69a7d4dcf6c5ea361a4027207d4`. Output
  was written to a fresh temporary directory; no retained artifact was changed.
- A replay with one quote corrupted left that reference unresolved, repaired
  only the other nine, and returned `failed`. It used a temporary output and
  `allow_llm=False`.
- The ten owning evidence-reference tests pass after rebase (10 passed, 23
  deselected). The full runner test file reports 29 passed and four failed.
  The same four failure signatures were reproduced on the previous clean base
  at `64e659248c9d40681b33df2c29a9a2573dfd6a8`; three old supplied-candidate
  fixtures lack `candidate_graph.campaign_id`, and the canonical-line-only
  fixture reports `party enrichment incomplete for 1 nodes`.
- Ruff on the two leased Python files passes when ignoring the inherited F401
  compatibility re-export `FixtureCategoryGraphPassClient` at
  `graph_ingest_packaging.py:38`. `git diff --check` passes.
- The retained candidate's report still shows 10 unresolved legacy span refs;
  the browser's separate `breadcrumb_required` state also reports canonical,
  normalized, breadcrumbed, and session-memory artifacts missing. This PR's
  replay proves the references are recoverable when repackaged; it does not
  mutate the retained run or complete durable ingestion.

This checkpoint is implementation evidence, not completion of real Ingest UI,
publication, database persistence, or end-to-end rendered acceptance.

## Latest current-main rebase and owning replay — 2026-10-16

Rebased the existing three-commit PR onto fetched
`origin/main@fc1daff4b7fc8f6ba7d35445dd22e9fca15f6d49` after #1250 merged. The
merge-tree check was clean, and the current cumulative change remains limited
to this four-file lease. Ten focused alias-repair tests pass. The owning runner
file reports 29 passed and the same four known failures: three legacy fixtures
omit `candidate_graph.campaign_id`, and the canonical-line-only fixture reports
`party enrichment incomplete for 1 nodes`. Ruff passes with the inherited F401
compatibility export ignored, and `git diff --check` passes.

Replayed the retained Session 29 candidate, normalized recap, and source-span
index with `allow_llm=False` into a fresh temporary artifact root. The current
branch produced `candidate_validation_ready` with ten repairs and zero
unresolved references. A negative control changed one quote only in a
temporary copy of the original candidate; the result stayed `failed`, repaired
the other nine references, and retained one unresolved reference. The original
candidate, recap, and span-index hashes remained unchanged. This proves the
package-time evidence repair and its fail-closed guard; it does not complete
the separate canonical recap, breadcrumb, session-memory, admission, or
rendered end-to-end requirements in the persistent Ingest goal.

## Current-main source-anchor integrity fix — 2026-10-16

Re-anchored the existing PR on `origin/main@85b3949c5cb4fd6419767c7a6037e3002a20750e`, confirmed by GitHub's recent-commit listing; the local main ref matched that commit.

The repair now requires every supplied `source_anchor_id` to match either the proven canonical span or the exact legacy span being repaired. A foreign, malformed, or inconsistent anchor leaves the reference unresolved instead of recording a successful repair while carrying the unrelated anchor forward. The regression test fails on the prior implementation and passes with this guard.

- Exact alias/canonical regression selection: 10 passed.
- Full `test_graph_memory_category_graph_preview_runner.py`: 30 passed, four known unrelated failures. Three old supplied-candidate fixtures omit `candidate_graph.campaign_id`; the canonical-line-only fixture reports `party enrichment incomplete for 1 nodes`.
- Ruff passes on both leased Python files with the inherited F401 compatibility re-export ignored. `git diff --check` passes.
- A fresh retained-candidate replay was not repeated for this narrow guard. Earlier replay evidence above remains valid for the candidate's proven anchors; the new foreign-anchor failure mode is covered by the owning runner regression.

This fix only tightens package-time repair proof. It does not complete the
breadcrumb/session-memory pipeline, Graph admission, publication, or real
rendered Ingest acceptance.

## Current-main rebase and owning suite — 2026-10-17

Rebased the existing PR onto fetched `origin/main@6c8d7b05a0e274d20325e953a66a7c8805e8fbfd` after #1287 merged. The merge-tree was clean. Main changed the owning runner test fixtures to require campaign/session/source identity; the legacy-alias fixture also needed to keep modeling the historical non-World-scoped artifact ID explicitly. It now constructs that legacy ID and its canonical span index directly, so the test continues to exercise the old shortened-ID case instead of asking the new World-scoped source factory to generate a legacy identity.

- Exact evidence-alias regression selection: 10 passed.
- Full owning runner file: 33 passed and one known canonical-line-only extraction fixture failure. That remaining failure is the existing `party enrichment incomplete for 1 nodes` validator result from fixture category output, recorded in earlier checkpoints; the alias-repair path does not run on this allow-LLM extraction test. No extraction behavior was changed in this package-time repair slice.
- Scoped Ruff checks, Python compileall, and `git diff --check` passed; the owning tests ran in the isolated checkout.
- The retained Session 29 candidate replay is not repeated after this rebase. The package implementation is unchanged from the previously recorded replay; only the owning tests and handoff changed across this rebase.

PR #1287 merged at `6c8d7b05a0e274d20325e953a66a7c8805e8fbfd`. That selected-World exact-run projection remains a separate capability; this PR still does not write or publish to the World Graph, repair retained run state, or complete the persistent ingestion-first goal.

## Latest main re-anchor and retained-candidate proof — 2026-10-17

PRIME re-dispatched this existing bounded slice after #1318 merged and directed
that the recorded Session 29 candidate be replayed in no-model mode, with the
ten unproven refs left unresolved and no retained-candidate or Graph mutation.
Main subsequently advanced through #1317 to
`157f8d11e39772a7e857bc41e110479daa8d6ef7`; GitHub confirms #1317's nine changed
paths are disjoint from this PR's four-path write set. This update preserves
that exact base and the existing PR topology. No retained artifact write, Graph
publication, or serving change is part of this lane.

- The exact legacy evidence-reference regression selection passes: 10 passed,
  24 deselected. The full owning runner file reports 33 passed and one existing
  failure in `test_runner_canonical_line_only_index_reaches_category_prompt`; the
  fixture fails candidate validation with `party enrichment incomplete for 1
  nodes`. It does not exercise package-time legacy-reference repair.
- Scoped Ruff (ignoring the inherited `F401` compatibility re-export), Python
  compileall, and `git diff --check` pass.
- A fresh `allow_llm=False` replay of the retained candidate produced
  `candidate_validation_ready`, repaired 10 refs across eight shortened IDs,
  and resolved 154/154 refs. Positive output hashes: packaged candidate
  `fb8ae42c8af061c741959e9f051a72dc7bae7e8e33c96f4315e24240f0f94065`, report
  `e3b3f150778ccc0f8c06ec105d09359d8ea7b046bb0fcaaf7856f5c6d78e20e1`, manifest
  `623845a46c39e12eb69bfbea9b16802e32c2f595fea58481ec15b792df231f18`.
- A negative replay with one deliberately corrupted quote failed closed, repaired
  only nine refs, and retained one unresolved ref. Negative output hashes:
  candidate `d4b952f16eaf1dd5ea1c44a0b848e7289f3ad8723c694b8557568200ded1f36a`,
  report `e705b532ad090e32470d884226d7e8b6c1c39b0963ce3cf06bdd102e29db2dd2`,
  manifest `3f9b9a265da066727f34946be8b89d5d5f9c9536683a854ac28f6d6811313796`.
- The original retained candidate, normalized recap, and span-index hashes were
  unchanged before and after replay: `8e7bb42d56f29c52d7b8f1b1f432a7888ea1d1355ce602ef8972503ba0ee5889`,
  `4f963656828b553f7919ee00d3304725ddff892a13651b989f99b9b649933796`, and
  `a94114e6aee71606e8d77aee42638657821ed69a7d4dcf6c5ea361a4027207d4`.

This proves package-time recovery of provable aliases and fail-closed handling
of a corrupted quote. It does not prove richer extraction, breadcrumb/session
memory generation, retained-run mutation, Graph admission/publication, actual
recap ingestion end-to-end, or rendered UI acceptance. The current tests ran in
the implementation tree at the previously fetched #1318 base; the only
newer main commit, #1317, changes disjoint files.


## PRIME review follow-up — conflicting valid span selectors — 2026-10-17

PRIME's independent review of head `1c855e2145272de0d46a8688affe1cdb4df12c7a` found that a reference could carry two different canonical span IDs, each independently present in the source index, and still be counted as resolvable. Candidate readiness now requires all non-empty supplied span selectors to agree on one ID; conflicting references remain unresolved in both top-level and nested copies and block readiness. Proven shortened aliases are still canonicalized before this consistency check. The regression exercises two valid spans and verifies the input candidate remains unchanged.

- The exact conflict regression passed: 1 passed.
- The complete owning runner file reports 35 passed and one existing failure in `test_runner_canonical_line_only_index_reaches_category_prompt`, which still fails with the unrelated fixture validation error `party enrichment incomplete for 1 nodes`.
- Scoped Ruff, Python compileall, and `git diff --check` passed.
- Testing used the already-present app runtime; no environment was created. No retained candidate, source, Graph, database, or server state was changed.


## PRIME review follow-up — malformed secondary selectors — 2026-10-17

PRIME independently confirmed the canonical-selector fix on the exact prior head and found that _evidence_span_ids still filtered non-string values. A valid primary ID paired with a present malformed secondary selector could therefore be treated as resolved or repaired. Selector parsing now treats absent and explicit null fields as optional, but rejects any present non-null field that is not a non-empty string; the same check runs before alias repair mutates the candidate. Regressions cover malformed integer/list/object/blank values and preserve valid alias repair when the optional secondary selector is absent or null.

- The bounded selector regressions passed: 7 passed (conflicting canonical IDs, four malformed selector values, absent/null optional field cases).
- The complete owning runner file reports 41 passed and one known unrelated failure in test_runner_canonical_line_only_index_reaches_category_prompt, where fixture category output fails with party enrichment incomplete for 1 nodes.
- Scoped Ruff, Python compileall, and git diff --check passed. Tests use the already-present app runtime; no environment was created.
- No retained candidate, source, Graph, database, or server state was changed.
