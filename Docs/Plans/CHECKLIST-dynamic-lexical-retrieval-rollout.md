# Checklist — Dynamic Lexical Retrieval Rollout

**Purpose:** Operational tracker for moving from current ingestion state to dynamic lexical retrieval from ingestion artifacts.
**Decision anchor:** `Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md` (Roadmap section).
**Super plan (canonical, versioned):** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — YAML frontmatter, changelog, and milestone M1–M4; update that file when the execution narrative shifts.
**Phase 1 + early Phase 2 PR:** [DungeonMindBuddy#2](https://github.com/Drakosfire/DungeonMindBuddy/pull/2) — **MERGED** to `main` 2026-05-10T02:59Z (merge commit `545cf37`). [PR #1](https://github.com/Drakosfire/DungeonMindBuddy/pull/1) is **closed** (superseded). Canonical `judgment_record` for both is in the super-plan YAML `external_pull_requests`.
**Phase B route-equivalence artifacts PR:** [DungeonMindBuddy#3](https://github.com/Drakosfire/DungeonMindBuddy/pull/3) — **MERGED** to `main` 2026-05-10T05:06Z (merge commit `98c09aaf0fead2aaaf4b3a7c90afcb09bae8026f`): committed JSONL under `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/`, `scripts/build_route_equivalence_manifests.py` (`--write` / `--check`), byte-stable regression `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`, and `_is_campaign_path` fix for relative `Longmont Campaign/...` registry paths.
**Phase C entry shadow consumer PR:** [DungeonMindBuddy#4](https://github.com/Drakosfire/DungeonMindBuddy/pull/4) — **MERGED** to `main` 2026-05-10T16:22Z (merge commit `21e84392da03095377b4de36defb82edfc37c741`): adds `src/lexicon_phase_b/route_equivalence_loader.py`, `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py`, and `--route-equivalence-jsonl` (repeatable) CLI flag on `breadcrumb_query_run`. `shadow_route_equivalences` (`dmb_route_equivalence_shadow_v1`) is emitted only when the flag is set; legacy retrieval, grading, and `shadow_token_resolution` are unchanged. Round 2 added harness-boundary safety tests in `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py`.
**Phase C entry provenance hardening PR:** [DungeonMindBuddy#5](https://github.com/Drakosfire/DungeonMindBuddy/pull/5) — **MERGED** to `main` 2026-05-10T21:09Z (merge commit `40be747a87d0eecb4dc1c865f236f3728cf1d4d4`): makes `shadow_route_equivalences.source_paths` workspace-relative POSIX strings rendered at the harness boundary so the field is byte-identical regardless of operator CWD or absolute install path. Adds `_workspace_relative_posix(path, workspace_root)` helper to `route_equivalence_shadow.py`; required `workspace_root: Path` kwarg on `build_route_equivalence_shadow_payload`; harness wires `_HARNESS_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]`. New harness-boundary test `test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant` asserts full-payload byte-identity across two operator CWDs. Closes the PR #4 known follow-up; unblocks a byte-stable cohort `shadow_route_equivalences` baseline.
**A/B sprint L2 recall PR:** [DungeonMindBuddy#7](https://github.com/Drakosfire/DungeonMindBuddy/pull/7) — **MERGED** to `main` 2026-05-11T02:59Z (merge commit `0036df30e5f53abd7ba76ab510483a9e1df0d3fa`): additive `breadcrumb_query_run.py` row field `expected_route_substring_breakdown`; `cohort_baseline_run.py` gains `recall_via_equivalence` / aggregate; frozen baseline `artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` (`dmb_breadcrumb_query_cohort_summary_v2`; v1 removed). `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` 12 tests; `tests/test_cohort_baseline_run.py` 13 tests. No retrieval flip. Cost $0.
**Phase C exit / A/B L3 PR:** [DungeonMindBuddy#9](https://github.com/Drakosfire/DungeonMindBuddy/pull/9) — **MERGED** to `main` 2026-05-11T04:13Z (merge commit `976512e94df62e42a27d1a41aa876a2561a0cb70`): `breadcrumb_query_run` `--use-route-equivalence-for-ranking` + `ranking_augmented_by_equivalences`; `cohort_baseline_run` `--mode both`, `--write-delta` / `--check-delta`, committed `artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json` (`dmb_breadcrumb_query_cohort_l3_delta_v1`); canvas `--skip-<scenario_id>-canvas-refresh` derived from manifest. Default cohort `--check` still v2 baseline byte-stable. **Tight-cohort delta:** baseline `all_ok` 3/3 vs with-equivalence 1/3 (c1s1 + c1s3 regress). Lexicon **25**; breadcrumb harness **12**; cohort **15**. Cost $0.
**L3 per-question deep-dive diagnostics PR:** [DungeonMindBuddy#10](https://github.com/Drakosfire/DungeonMindBuddy/pull/10) — **MERGED** to `main` 2026-05-11T14:54Z (merge commit `c75c3f6b622b35658eafd0a5b1641421b791357e`): `cohort_baseline_run` adds `--write-question-delta` / `--check-question-delta`, committed `artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json` (`dmb_breadcrumb_query_cohort_l3_question_delta_v1`, `question_count: 44`, summary `regressed:2 improved:0 unchanged_pass:42 unchanged_fail:0`); deterministic emitter `cohort_l3_question_deep_dive_canvas_emit.py` writes `canvases/cohort-l3-ab-question-deep-dive.canvas.tsx` with generated markers. Diagnostics-only (no retrieval flip). Lexicon **25**; cohort **17**; emitter **2**. Cost $0.
**Wider-cohort A/B baseline PR:** [DungeonMindBuddy#11](https://github.com/Drakosfire/DungeonMindBuddy/pull/11) — **MERGED** to `main` 2026-05-11T19:39Z (merge commit `eec38807ea1866e63b5997e21558968d7559ea16`): committed `cohorts/natural_v1.json`, `cohort_baseline_natural_v1.json`, `cohort_l3_ab_delta_natural_v1.json`, `cohort_l3_ab_question_delta_natural_v1.json`, and `cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx`; `cohort_baseline_run` check reruns now forward `--manifest`, and question-delta metadata references the active delta lane path. Wider-cohort summary: `question_count:12`, `regressed:0 improved:1 unchanged_pass:7 unchanged_fail:4`. Lexicon **25**; cohort **19**; emitter **3**. Cost $0.
**Phase B producer provenance PR:** [DungeonMindBuddy#8](https://github.com/Drakosfire/DungeonMindBuddy/pull/8) — **MERGED** to `main` 2026-05-11T03:45Z (merge commit `adeb060911be35f4f477cb15eaf701ab7d409fbf`): committed `route_equivalence_longmont_c*_v1.jsonl` at **`schema_version` `0.3.0`** with **`route_equivalence_manifest_hash`**, **`producer_registry_path`** (workspace-relative POSIX), **`producer_registry_sha256`**; `build_route_equivalence_manifest` preimage per PLAN §6.2; loader + lexicon tests extended. No harness, cohort runner, shadow, gold, or baseline edits. Cost $0.
**A/B sprint L1 cohort baseline PR:** [DungeonMindBuddy#6](https://github.com/Drakosfire/DungeonMindBuddy/pull/6) — **MERGED** to `main` 2026-05-11T01:49Z (merge commit `9af4741a635125d3403d66a9f266564f25bad746`): `cohort_baseline_run.py`, manifest `cohorts/c1s1_to_c1s3_v1.json`, frozen curated baseline at ship time `artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json` (superseded as `--check` anchor by PR #7 v2), `tests/test_cohort_baseline_run.py`. L1 had no harness/shadow/producer/gold edits; PR #7 additively extended `breadcrumb_query_run.py` for L2 only.
**Status model:** keep exactly one phase marked as active at a time.

---

## Reanchor Block (fill first each session)

- [x] **Active phase:** `B` (Phase C **entry** PR #4–#5; **exit** L3 harness landed PR #9 — gated ranking flag + delta runner; **promotion** to default retrieval still open)
- [x] **Last green artifact (path):** `uv run python scripts/build_route_equivalence_manifests.py --check` -> `OK` both JSONL (**`0.3.0`**, PR #8); `uv run pytest tests/lexicon_phase_b/ -q` -> `25 passed`; `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q` -> `12 passed`; `uv run pytest tests/test_cohort_baseline_run.py -q` -> `19 passed`; `uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py -q` -> `3 passed`; `uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check` -> `OK …/cohort_baseline_c1s1_to_c1s3_v2.json`; `uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-delta` -> `OK …/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json`; `uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-question-delta` -> `OK …/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json`; `uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json --check` -> `OK`; `... --delta ...cohort_l3_ab_delta_natural_v1.json --check-delta` -> `OK`; `... --check-question-delta ...cohort_l3_ab_question_delta_natural_v1.json` -> `OK`; `uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit --input ...natural_v1.json --output canvases/cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx` + marker check -> `canvas_exists True`, `has_generated_markers True` (post-PR #11 `main` at `eec38807ea`, 2026-05-11).
- [x] **Current blocking red gate:** none for harness lanes. **Load-bearing readout:** tight-cohort L3 delta still shows **2/3 scenarios regress** when `--use-route-equivalence-for-ranking` is on (`with_equivalence_all_ok_count` **1** vs baseline **3**); wider-cohort `natural_v1` question-level summary is `regressed:0 improved:1 unchanged_pass:7 unchanged_fail:4` (`question_count:12`). Promotion to default remains blocked pending alias-saturation analysis and explicit promotion criteria decision. **Follow-up:** `audit_world_campaign_alignment.py` clean-checkout manifest gap (pre-existing).
- [x] **Blocker type:** `n/a`
- [x] **Next command to run:** Full regression bundle: `uv run python scripts/build_route_equivalence_manifests.py --check && uv run pytest tests/lexicon_phase_b/ -q && uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q && uv run pytest tests/test_cohort_baseline_run.py -q && uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py -q && uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check && uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-delta && uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-question-delta && uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json --check && uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json --delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_natural_v1.json --check-delta && uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json && uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit && uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json --output canvases/cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx`. **Next slice:** alias-saturation investigation and promotion-gate decisioning before any default retrieval flip.

---

## Phase A — Deterministic guardrails

**Goal:** structural drift fails before LLM tuning.

- [x] Registry authority split gate green (`hub_path` campaign authority, `setting_hub_path` world fallback).
- [x] Remote manifest campaign IDs normalized (`longmont-cN` for campaign rows).
- [x] Location hierarchy contract encoded in relevant gold scenarios (structural).
- [x] Alignment audit target green:
  - `uv run python scripts/audit_world_campaign_alignment.py` -> `World/Campaign alignment audit: PASS` (2026-05-10).

**Evidence**

- Last green audit log: `World/Campaign alignment audit: PASS\nChecked 1 manifest(s) and 5 breadcrumb natural gold file(s).` (`uv run python scripts/audit_world_campaign_alignment.py`, 2026-05-10).
- Remaining A-phase violations: none for the audit's structural contract.

**Flagged follow-up (not a Phase A blocker):**

- Content quality of `location_hierarchy_equivalences` in `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json` looks copy-pasted across scenarios (e.g. `Wolf` and `Mossglade` parents map to `stormspire_academy/`-family children). The audit only checks structure (non-empty, key intersect with expected routes); it cannot detect semantic mis-mapping. Tracked in `Backlog.md` under "C1S13 hierarchy content audit". Do not block Phase B on this.

---

## Phase B — Dynamic lexical artifact generation

**Goal:** lexical match inventory derives from ingestion outputs.

- [x] Lexical artifact schema defined and documented (`src/lexicon_phase_b/schemas.py::RouteEquivalenceRecord`, **`schema_version` `0.3.0`** on committed JSONL after PR #8; `0.2.0` lineage via PR #2).
- [x] Generator consumes ingestion outputs with route/provenance fields (`src/lexicon_phase_b/route_equivalence_manifest.py::build_route_equivalence_manifest` reads `_npc_registry.json` via `src/contracts/npc_registry.py`).
- [x] Generation is deterministic for fixed inputs (byte-stable output) — `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`; command: `uv run pytest tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py -q` -> `10 passed` (post-PR #8 `main`, 2026-05-11).
- [x] Artifact output path standardized and documented — canonical dir `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/`; documented in `evals/sentence_routing_retrieval_falsification/README.md` under `Route equivalence manifests (Phase B)`.

**Evidence**

- Schema + builder: `src/lexicon_phase_b/schemas.py`, `src/lexicon_phase_b/route_equivalence_manifest.py`.
- Committed artifacts: `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl`, `route_equivalence_longmont_c2_v1.jsonl` (PR #3).
- CLI: `scripts/build_route_equivalence_manifests.py` (`--write`, `--check`, `--out-dir`).
- Tests: `tests/lexicon_phase_b/test_route_equivalence_manifest.py`, `test_route_id_path_shapes.py`, `test_route_equivalence_record_defaults.py`, `test_route_equivalence_entity_kind_inference.py`, `test_route_equivalence_artifacts_byte_stable.py` (byte match + real-registry path-shape assertions).
- Lexicon suite: `uv run pytest tests/lexicon_phase_b/ -q` -> `25 passed` (post-PR #8 `main` at `adeb060`, 2026-05-11).
- Token-resolution regression guard: `uv run pytest tests/test_token_resolution_resolver.py tests/test_token_resolution_contracts.py tests/test_benchmark_lexicon_seeds.py -q` -> `28 passed` (unchanged surface).
- Determinism check: `uv run python scripts/build_route_equivalence_manifests.py --check` -> `OK` both artifacts (2026-05-10).

**Evidence (producer provenance — PR #8, merge commit `adeb060911be35f4f477cb15eaf701ab7d409fbf`)**

- Schema + builder: `src/lexicon_phase_b/schemas.py` (`RouteEquivalenceRecord` defaults `0.3.0`; required `producer_registry_path`, `producer_registry_sha256`, `route_equivalence_manifest_hash`); `src/lexicon_phase_b/route_equivalence_manifest.py` (`_manifest_hash_preimage`, `build_route_equivalence_manifest` assigns same manifest hash to every edge after registry path/sha256 materialization); `src/lexicon_phase_b/route_equivalence_loader.py` admits `0.3.0`.
- Committed artifacts: `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl`, `route_equivalence_longmont_c2_v1.jsonl` — one distinct `route_equivalence_manifest_hash` per file; workspace-relative `producer_registry_path`; lowercase hex64 `producer_registry_sha256`.
- Tests: `tests/lexicon_phase_b/test_route_equivalence_manifest.py` gains `test_manifest_hash_preimage_changes_on_semantic_mutation`; `test_route_equivalence_artifacts_byte_stable.py` extended (per-file hash constancy + byte match); loader + record-defaults updated.
- Parent §7 on PR head `91fb12ee`: lexicon **25**; byte-stable **10**; loader **6**; manifest **4**; record defaults **1**; `build_route_equivalence_manifests.py --check` OK both; breadcrumb harness **12**; cohort **13**; `cohort_baseline_run --check` OK v2; JSONL probes: `manifest_hashes 1`, `schema 0.3.0`, `c1_registry_sha256_distinct 1`, `producer_registry_path corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json`.
- Review: APPROVE -> COMMENTED self-review (`4260634217`). Non-blocking follow-up: tighten preimage-sensitivity test to hold registry bytes constant (PR inline comment).

---

## Phase C — Retriever wiring (existing retriever, dynamic source)

**Goal:** retriever uses generated lexical artifact as primary source.

**Status:** **entry landed** (PR #4). **Exit — gated wiring landed** (PR #9): `--use-route-equivalence-for-ranking` augments ranking from loaded equivalence records; **default** path unchanged (v2 baseline byte-stable). **Promotion** (default flip, static seeds fallback-only) **not** landed — delta shows tight-cohort regressions under the flag.

- [x] **Entry:** harness consumes generated artifact behind explicit flag, shadow-only; per-scenario `shadow_route_equivalences` (`dmb_route_equivalence_shadow_v1`) emitted alongside `shadow_token_resolution` (PR #4).
- [x] **Entry safety:** byte-identity-when-flag-unset and load-failure-emits-error tested at the harness boundary, not just the loader (PR #4 round 2; the round-1 gap that became the rubric bullet "test the boundary that owns the rubric").
- [x] **Exit (gated):** harness wires equivalence-derived `query_token_aliases` into retrieval when `--use-route-equivalence-for-ranking` is set (**PR #9**); cohort `--mode both` + committed L3 delta JSON; canvas skip argv derived from `scenario_id`.
- [ ] Static/hand-seeded lexical source moved to fallback mode only.
- [ ] Deterministic test proves retrieval runs with generated-only lexical source.
- [ ] Failure mode diagnostics distinguish "missing lexical handle" vs retriever bug.

**Evidence (entry — PR #4, merge commit `21e84392`)**

- New code: `src/lexicon_phase_b/route_equivalence_loader.py` (pure JSONL → `RouteEquivalenceRecord` loader, exported via `src/lexicon_phase_b/__init__.py`); `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py` (per-scenario `dmb_route_equivalence_shadow_v1` payload builder); `--route-equivalence-jsonl` (repeatable) CLI flag on `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`.
- Loader tests: `tests/lexicon_phase_b/test_route_equivalence_loader.py`. `uv run pytest tests/lexicon_phase_b/ -q` -> `17 passed` on post-PR #4 `main`.
- Harness-boundary tests added round 2 in `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py`:
  - `test_route_equivalence_flag_is_additive_only_at_harness_boundary` — runs `breadcrumb_query_run` twice (with and without the flag) via subprocess and asserts byte-identity for all non-`shadow_route_equivalences` fields.
  - `test_route_equivalence_load_failure_emits_error_payload_and_run_survives` — points the flag at a missing path, asserts a structured `error_payload` is emitted on every scenario row and the run does not raise.
- `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q` -> `10 passed` on post-PR #4 `main`.
- Determinism check unchanged: `uv run python scripts/build_route_equivalence_manifests.py --check` -> `OK` for both manifests.

**Evidence (provenance hardening — PR #5, merge commit `40be747a`)**

- New helper: `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py::_workspace_relative_posix(path, workspace_root)` — renders `path.resolve().relative_to(workspace_root.resolve()).as_posix()` with a defensive `ValueError -> path.name` fallback.
- API change: `build_route_equivalence_shadow_payload` now requires a `workspace_root: Path` kwarg (no default). Caller audit: only two code call sites (the harness and the four updated unit tests); both passed in-PR.
- Harness wiring: `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` defines `_HARNESS_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]` and forwards it to the payload builder.
- New harness-boundary test in `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py`: `test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant` spawns `breadcrumb_query_run` from `_REPO_ROOT` and from `_REPO_ROOT / "tests"` via `uv run --directory _REPO_ROOT …`, asserts both runs return exit 0, and compares the **full** `shadow_route_equivalences` payload (not just `source_paths`) for byte-identity. Smoke step in §7 also prints the expected workspace-relative POSIX list.
- `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q` -> `11 passed` on post-PR #5 `main` (10 -> 11 from the new test).
- `uv run pytest tests/lexicon_phase_b/ -q` -> `22 passed` (unchanged from main; PR #5 did not touch producer-side).
- Determinism check unchanged: `uv run python scripts/build_route_equivalence_manifests.py --check` -> `OK` for both manifests.

**Evidence (A/B sprint L1 — PR #6, merge commit `9af4741a`)**

- New harness: `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` — `--write` / `--check`, drives `breadcrumb_query_run --retrieval-only` with `--skip-*-canvas-refresh` and repeatable `--route-equivalence-jsonl` from the cohort manifest.
- Manifest: `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` (`dmb_breadcrumb_query_cohort_manifest_v1`; scenarios `c1s1`, `c1s2`, `c1s3`).
- Frozen baseline: `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json` (`dmb_breadcrumb_query_cohort_summary_v1`).
- Tests: `tests/test_cohort_baseline_run.py` -> `9 passed` on post-PR #6 `main`; includes `test_cohort_baseline_run_write_is_byte_identical_across_cwds` (subprocess CWD harness on full curated JSON).
- `uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check` -> `OK` committed baseline path.
- Parent §7 on PR head `06280c87`: fresh `--write` to `/tmp/...` was **BYTE-IDENTICAL** to committed baseline via `diff -u`; `git status --short canvases/` empty.

**Evidence (A/B sprint L2 — PR #7, merge commit `0036df30`)**

- Harness: additive `expected_route_substring_breakdown` on each natural-benchmark row in `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` (reuses `hits_cover_expected_routes`); new harness test `test_expected_route_substring_breakdown_is_consistent_with_violations`.
- Cohort runner: `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` — `_normalize_substring_to_slug`, `_equivalence_can_rescue`, `_compute_recall_via_equivalence`, `_aggregate_question_breakdowns`; schema `dmb_breadcrumb_query_cohort_summary_v2`; default baseline `artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` (v1 removed).
- Tests: `uv run pytest tests/test_cohort_baseline_run.py -q` -> `13 passed`; combined with lexicon + breadcrumb harness -> `47 passed`; `cohort_baseline_run --check` -> `OK` v2 path; tight cohort smoke: all `recall_via_equivalence: null`, aggregate `min/mean/max: null`.
- `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q` -> `12 passed` on post-PR #7 `main`.

**Evidence (Phase C exit / A/B L3 — PR #9, merge commit `976512e94d`)**

- Harness: `breadcrumb_query_run.py` — `--use-route-equivalence-for-ranking`; when set with loaded records, deep-copies scenario and appends equivalence-derived strings to `query_spec.query_token_aliases` before `natural_retrieval_bundle`; row field `ranking_augmented_by_equivalences`.
- Cohort: `cohort_baseline_run.py` — `--mode baseline|with-equivalence|both`; `--write-delta` / `--check-delta`; `run_one_scenario` emits `--skip-<scenario_id>-canvas-refresh` from manifest row (no hardcoded c1s1/c1s2/c1s3 triple).
- Committed delta: `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json` — `schema_id` `dmb_breadcrumb_query_cohort_l3_delta_v1`; per-scenario `baseline_all_ok` vs `with_equivalence_all_ok`; `delta_summary` includes `scenarios_regressed: 2`, `with_equivalence_all_ok_count: 1`, `baseline_all_ok_count: 3` (tight cohort).
- Tests: `test_use_route_equivalence_for_ranking_flag_is_additive_only_at_harness_boundary`; `test_run_one_scenario_skip_flag_is_derived_from_scenario_id`; `test_mode_both_write_delta_schema`; `uv run pytest tests/test_cohort_baseline_run.py -q` -> `15 passed`; combined lexicon + both harness files -> `52 passed` arithmetic check on post-PR #9 `main`.
- Regression: `cohort_baseline_run --check` OK v2; `cohort_baseline_run --check-delta` OK committed delta; byte-identity default `--write --baseline` vs `cohort_baseline_c1s1_to_c1s3_v2.json` (use boolean `--write` + `--baseline <path>`, not `--write <path>`).
- Review: APPROVE -> COMMENTED self-review (`4260705957`). Cost $0.
- **Evidence (L3 per-question deep-dive diagnostics — PR #10, merge commit `c75c3f6b62`)**
- Harness/cohort: `cohort_baseline_run.py` adds deterministic per-question contract `--write-question-delta` / `--check-question-delta`; committed artifact `artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json` (`schema_id` `dmb_breadcrumb_query_cohort_l3_question_delta_v1`) with `question_count: 44` and summary buckets (`regressed:2`, `improved:0`, `unchanged_pass:42`, `unchanged_fail:0`).
- Canvas emitter: new `cohort_l3_question_deep_dive_canvas_emit.py` writes `canvases/cohort-l3-ab-question-deep-dive.canvas.tsx`; marker smoke confirms `BEGIN GENERATED` / `END GENERATED`.
- Tests: `uv run pytest tests/test_cohort_baseline_run.py -q` -> `17 passed`; `uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py -q` -> `2 passed`; plus lexicon 25 and breadcrumb harness 12 as unchanged lanes.
- Review: single round; APPROVE -> COMMENTED self-review (`4264759583`). Cost $0 (retrieval-only + pytest).

---

## Phase D — Holdout validation

**Goal:** prove new-session retrieval works without session-specific tuning.

- [ ] Holdout recap/session selected (not used to tune lexical rules).
- [ ] Full chain run: ingest -> lexical artifact generation -> retrieval benchmark.
- [ ] Required route/context gates pass on holdout.
- [ ] No session-specific prompt/gold hardcoding added for holdout.

**Evidence**

- Holdout run artifact(s): `...`
- Pass/fail summary: `...`
- One failure sample + one success sample noted: `...`

---

## Phase E — All-sessions operational run

**Goal:** campaign-wide ingest + retrieval validation is repeatable.

- [ ] Backfill run plan defined for Campaign 1 and Campaign 2 session sets.
- [ ] Cohort summaries emitted with gate and cost telemetry.
- [ ] CI/manual gate command documented and runnable.
- [ ] "How to run from scratch" section documented in one canonical place.

**Evidence**

- Cohort summary artifact path(s): `...`
- Operational run command(s): `...`
- Final readiness verdict: `...`

---

## Cost & Drift Notes (update each cohort)

- Previous cohort cost baseline: `...`
- Current cohort cost: `...`
- Regression flag (`>=1.5x`): `yes | no`
- Notable drift notes: `No new cost-bearing cohort run in this checklist update; this was a structural audit + registry-hardening pass.`

---

## Session Log (append newest first)

### 2026-05-11 (UTC) — twelfth entry, PR #11 merged + atomic doc-sync (wider cohort natural_v1)

- Phase moved: **`stayed B`**. `milestone_progress` unchanged (`M2: in_progress`, `M3: complete`).
- What turned green: [PR #11](https://github.com/Drakosfire/DungeonMindBuddy/pull/11) **MERGED** to `main` (merge commit `eec38807ea1866e63b5997e21558968d7559ea16`, 2026-05-11T19:39:14Z). Adds committed wider-cohort manifest + artifacts: `cohorts/natural_v1.json`, `cohort_baseline_natural_v1.json`, `cohort_l3_ab_delta_natural_v1.json`, `cohort_l3_ab_question_delta_natural_v1.json`, and `cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx`.
- Boundary contract tightened: `cohort_baseline_run.py` check reruns now forward non-default `--manifest` for `--check-delta` and `--check-question-delta`; question-delta metadata `scenario_level_delta_path` now reflects active lane path.
- **Load-bearing readout:** natural-v1 per-question summary `question_count:12`, `regressed:0`, `improved:1`, `unchanged_pass:7`, `unchanged_fail:4`; retrieval-only lane confirmed (`llm_enabled False`, `retrieval_only True`). Tight-cohort regression signal remains (2/3 scenarios regressed with flag on).
- **Cost:** `$0` (retrieval-only + pytest; no LLM calls).
- PLAN v18: `github-pr-11` added with rubric bullets for manifest-aware boundary checks + wider-cohort deterministic anchors. Handoff `HANDOFF-pr11-wider-cohort-natural-v1-ab-baseline-and-question-delta.md` archived under `Docs/Plans/archive/2026-05-11/handoffs/`.
- Next single action: run alias-saturation analysis and define explicit promotion criteria for default-flip decision.

### 2026-05-11 (UTC) — eleventh entry, PR #10 merged + atomic doc-sync (L3 question deep-dive diagnostics)

- Phase moved: **`stayed B`**. `milestone_progress` unchanged (M3 remains **`complete`**; promotion gate still open).
- What turned green: [PR #10](https://github.com/Drakosfire/DungeonMindBuddy/pull/10) **MERGED** to `main` (merge commit `c75c3f6b622b35658eafd0a5b1641421b791357e`, 2026-05-11T14:54:48Z). Adds deterministic per-question artifact `cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json` (`dmb_breadcrumb_query_cohort_l3_question_delta_v1`, `question_count: 44`) plus emitter `cohort_l3_question_deep_dive_canvas_emit.py` -> `canvases/cohort-l3-ab-question-deep-dive.canvas.tsx`.
- **Load-bearing readout:** per-question summary in committed artifact is `regressed: 2`, `improved: 0`, `unchanged_pass: 42`, `unchanged_fail: 0`; this makes route-vs-support regressions inspectable without changing scoring behavior.
- **Cost:** `$0` (pytest + retrieval-only checks + emitter run; no new LLM calls).
- PLAN v17: `github-pr-10` added with rubric bullets; `next_gate_command` includes emitter tests + `--check-question-delta`; current-state snapshot + PR table + primary files + workstream checklist updated.
- Handoff `HANDOFF-pr10-l3-question-deep-dive-canvas.md` archived under `Docs/Plans/archive/2026-05-11/handoffs/` with completion banner.
- Next single action: run wider-cohort (`c1s13_v1` / `natural_v1`) baseline + per-question delta to test whether tight-cohort L3 regression pattern generalizes before any default promotion discussion.

### 2026-05-11 (UTC) — tenth entry, PR #9 merged + atomic doc-sync (Phase C exit L3 + v16 PLAN)

- Phase moved: **`stayed B`**. `milestone_progress.M3` -> **`complete`** on super-plan (Phase C exit harness landed; promotion items still open in CHECKLIST).
- What turned green: [PR #9](https://github.com/Drakosfire/DungeonMindBuddy/pull/9) **MERGED** to `main` (merge commit `976512e94df62e42a27d1a41aa876a2561a0cb70`, 2026-05-11T04:13:54Z). L3: ranking flag, cohort delta modes, derived canvas skip argv, committed `cohort_l3_ab_delta_c1s1_to_c1s3_v1.json`. **Cherry-pick:** local PR #8-only doc-sync commit `02bbcc0` replayed as `458b53e` onto `origin/main` before this v16 batch so GitHub `main` and PLAN narrative align.
- **Load-bearing readout:** tight cohort A/B shows **baseline 3/3** `all_ok` vs **with-equivalence 1/3** — c1s1 + c1s3 regress (`context_support_below_threshold`, `semantic_verdict:fail_incomplete`). Do not default the flag without wider cohort / alias work.
- **Cost:** `$0` (pytest + retrieval-only cohort + delta `--check`).
- PLAN v16: `github-pr-9` + four NEW `rubric_when_we_judge` bullets; `next_gate_command` adds `--check-delta`; A/B sprint + Phase 5 narrative updated; L3 checklist row `[x]`. Handoff `HANDOFF-pr9-phase-c-exit-l3-true-ab-cohort.md` archived under `archive/2026-05-11/handoffs/`. Checklist Reanchor + Phase C + session log synced.
- Next single action: **wider cohort** manifest/baseline for `c1s13_v1` / `natural_v1` and/or **alias-saturation** analysis; optional harness tests (multi-`scenario_id` skip; delta two-CWD).

### 2026-05-11 (UTC) — ninth entry, PR #8 merged + doc sync (producer JSONL 0.3.0 provenance)

- Phase moved: **`stayed B`**. `milestone_progress` unchanged (M2/M3 still `in_progress`).
- What turned green: [PR #8](https://github.com/Drakosfire/DungeonMindBuddy/pull/8) **MERGED** to `main` (merge commit `adeb060911be35f4f477cb15eaf701ab7d409fbf`, 2026-05-11T03:45:24Z). Producer lane: committed route-equivalence JSONL at **`schema_version` `0.3.0`** with **`route_equivalence_manifest_hash`**, **`producer_registry_path`**, **`producer_registry_sha256`**; preimage algorithm matches PLAN §6.2; no edits to `breadcrumb_query_run.py`, `cohort_baseline_run.py`, `route_equivalence_shadow.py`, gold, or cohort baselines.
- Review: §7 all green on PR head `91fb12ee1b09e03b6653148124e5a2f8816dbcdc`; APPROVE -> COMMENTED self-review (`4260634217`). `merge 8` fast-forward clean.
- **Cost:** `$0` (pytest + producer CLI + probes only).
- PLAN v15: `github-pr-8` + five `rubric_when_we_judge` bullets (canvas skip carry-forward; §6.2 preimage; per-file constancy; path+sha256 tie; sensitivity-test preimage-input discipline). Handoff `HANDOFF-pr8-producer-route-equivalence-manifest-hash.md` archived under `Docs/Plans/archive/2026-05-11/handoffs/`.
- Next single action: **wider cohort** manifest work and/or **derive canvas `--skip-*` from scenario_id** before expanding the cohort manifest (rubric carry-forward).

### 2026-05-11 (UTC) — eighth entry, PR #7 merged + doc sync (A/B sprint L2 recall)

- Phase moved: **`stayed B`**. `milestone_progress` unchanged.
- What turned green: [PR #7](https://github.com/Drakosfire/DungeonMindBuddy/pull/7) **MERGED** to `main` (merge commit `0036df30e5f53abd7ba76ab510483a9e1df0d3fa`, 2026-05-11T02:59:47Z). L2: `dmb_breadcrumb_query_cohort_summary_v2`, baseline `cohort_baseline_c1s1_to_c1s3_v2.json`, per-row breakdown + recall fields; no retrieval flip.
- Review: §7 green on PR head `2bc6ad9e`; APPROVE -> COMMENTED self-review (`4260504200`). `merge 7` fast-forward clean.
- **Cost:** `$0` (retrieval-only).
- PLAN v14: `github-pr-7` + four rubric bullets; narrative PR 6.5 -> PR #7; producer lane -> **PR #8**. Handoff `HANDOFF-pr7-shadow-recall-via-equivalence-c1s1-to-c1s3.md` archived under `Docs/Plans/archive/2026-05-11/handoffs/`.

### 2026-05-11 (UTC) — seventh entry, PR #6 merged + doc sync (A/B sprint L1 cohort baseline)

- Phase moved: **`stayed B`**. `milestone_progress` unchanged (M2/M3 still `in_progress`).
- What turned green: [PR #6](https://github.com/Drakosfire/DungeonMindBuddy/pull/6) **MERGED** to `main` (merge commit `9af4741a635125d3403d66a9f266564f25bad746`, 2026-05-11T01:49:53Z). A/B Benchmarking Sprint **L1**: `cohort_baseline_run.py`, cohort manifest `cohorts/c1s1_to_c1s3_v1.json`, frozen curated baseline `artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json`, `tests/test_cohort_baseline_run.py`. No edits to `breadcrumb_query_run.py`, `route_equivalence_shadow.py`, producer JSONL, gold, or grader.
- Review-loop tooling notes: single round; `fetch 6 --extract-rubric` allowlist/denylist both `pass` (exactly four §4 paths). `verify 6 --parse-counts` at head `06280c87`: lexicon 22, breadcrumb harness 11, manifest `--check` OK, cohort 9 + CWD harness 1, cohort `--check` OK, `--write` smoke BYTE-IDENTICAL vs committed baseline, `canvases/` clean. APPROVE demoted to COMMENTED (self-review fallback, review id `4260316552`). `merge 6` -> `ff_pull_ok: true`, no stash.
- Pre-merge verification (verbatim): same as verify JSON tails — aggregate on smoke output `total_questions: 44`, `all_scenarios_all_ok: True`.
- **Cost:** `$0` cohort slice (retrieval-only; no LLM).
- What stayed open: L2 recall metric (PR 6.5); PR #7 producer `manifest_hash`; Phase C **exit** retriever wiring; broader Phase B entity-candidate / lexical-handle artifacts.
- Next single action: author **PR 6.5 / L2** handoff *or* dispatch **PR #7** producer lane in parallel per PLAN queue.
- Handoff `Docs/Plans/HANDOFF-pr6-cohort-baseline-runner-c1s1-to-c1s3.md` archived to `Docs/Plans/archive/2026-05-11/handoffs/` with completion banner.

### 2026-05-10 (UTC) — sixth entry, PR #5 merged + doc sync (workspace-relative `source_paths`)

- Phase moved: **`stayed B, with Phase C entry hardening landed`**. No `milestone_progress` change in the super-plan (M3 stays `in_progress`); the slice closes the PR #4 follow-up and is the precondition for the cohort-baseline slice.
- What turned green: [PR #5](https://github.com/Drakosfire/DungeonMindBuddy/pull/5) **MERGED** to `main` (merge commit `40be747a87d0eecb4dc1c865f236f3728cf1d4d4`, 2026-05-10T21:09Z). `shadow_route_equivalences.source_paths` is now workspace-relative POSIX strings rendered at the harness boundary, so the field is byte-identical regardless of operator CWD or absolute install path. New helper `_workspace_relative_posix(path, workspace_root)` in `route_equivalence_shadow.py`; required `workspace_root: Path` kwarg on `build_route_equivalence_shadow_payload`; harness wires `_HARNESS_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]`. New harness-boundary test `test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant` spawns the harness from two operator CWDs via subprocess and asserts full-payload byte-identity (not just `source_paths` equality).
- Review-loop tooling notes: single round of review (commit `ec1f55fa`). Diff exactly matched §4 allowlist (3 files, 87 +/4 -); §5 denylist clean (no producer-side, prompt, gold, schema, or builder edits). `scripts/review_external_pr.py fetch 5 --extract-rubric` parsed 7 §9 bullets and 6 §7 commands. `scripts/review_external_pr.py verify 5 --parse-counts` ran §7 against PR head with a clean stash + restore (`stashed: false`, no overlap). APPROVE was demoted to a `COMMENTED` verdict banner under the standard self-review fallback (review id `4259919574`). `scripts/review_external_pr.py merge 5` reported `ff_pull_ok: true`, `overlap_files: []`, `stashed: false` — local main fast-forwarded cleanly past the ~50 unrelated dirty files. NEW rubric bullet captured in `external_pull_requests[github-pr-5].rubric_when_we_judge`: provenance fields in shadow diagnostics are rendered at the harness boundary, with CWD-invariance tested by spawning a subprocess from at least two different CWDs and asserting full-payload equality (not just the field under test).
- Pre-merge verification (verbatim, against PR head `ec1f55fa`): `uv run pytest tests/lexicon_phase_b/ -q` -> `22 passed`; `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q` -> `11 passed`; `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py::test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant -q` -> `1 passed`; `uv run python scripts/build_route_equivalence_manifests.py --check` -> `OK` both manifests; smoke run + `python -c "import json; …; print(r[0]['shadow_route_equivalences']['source_paths'])"` printed the expected workspace-relative POSIX list verbatim.
- Known follow-up (not blocking merge): the original handoff §9 bullet #6 quoted "17 passed" for `tests/lexicon_phase_b/`; actual count at both `main` and PR head is `22 passed`. Stale rubric copy from when the handoff was authored — the substantive claim ("producer-side untouched") is true (no diff in those paths). Surfaced in the verdict body, not gated.
- What stayed open: Phase C **exit** (retriever rewiring + promotion gate); broader Phase B remainder (entity-candidate + lexical-handle artifacts); sibling lane — producer-side `manifest_hash` + provenance fields on `route_equivalence_longmont_c*_v1.jsonl` (could ship in parallel with the cohort-baseline lane since file scopes don't overlap).
- Next single action: dispatch the **cohort `shadow_route_equivalences` baseline** for C1S1-C1S3 — now byte-stable-able after PR #5; would establish a regression contract identical to the one PR #3 holds for source artifacts.

### 2026-05-10 (UTC) — fifth entry, PR #4 merged + doc sync (Phase C entry)

- Phase moved: **`B → still B, with Phase C entry landed`**. `milestone_progress.M3: not_started -> in_progress` in the super-plan; retriever wiring (Phase C **exit**) remains gated.
- What turned green: [PR #4](https://github.com/Drakosfire/DungeonMindBuddy/pull/4) **MERGED** to `main` (merge commit `21e84392da03095377b4de36defb82edfc37c741`, 2026-05-10T16:22Z). Shadow consumer wired into `breadcrumb_query_run` behind `--route-equivalence-jsonl`, emitting `shadow_route_equivalences` (`dmb_route_equivalence_shadow_v1`) alongside the existing `shadow_token_resolution` lane. Loader at `src/lexicon_phase_b/route_equivalence_loader.py`; shadow module at `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py`. Two harness-boundary safety tests landed in round 2 (`test_route_equivalence_flag_is_additive_only_at_harness_boundary`, `test_route_equivalence_load_failure_emits_error_payload_and_run_survives`).
- Review-loop tooling notes: round 1 (commit `e36b5a1`) had loader-level tests but no harness-boundary tests for the safety contract, and was REQUEST_CHANGES'd via `scripts/review_external_pr.py post --review-md ...` (demoted to COMMENT due to GitHub self-review policy; verdict surfaced in the body banner). Round 2 (commit `a5f3c1c`) closed the gap; APPROVE was likewise demoted to COMMENT. The new rubric bullet "test the boundary that owns the rubric" was added to `.cursor/rules/external-agent-pr-loop.mdc` and to `external_pull_requests[github-pr-4].rubric_when_we_judge`.
- Pre-merge verification: `uv run pytest tests/lexicon_phase_b/ -q` -> `17 passed`; `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q` -> `10 passed`; `uv run python scripts/build_route_equivalence_manifests.py --check` -> `OK` both manifests.
- Known follow-up (not blocking merge): `shadow_route_equivalences.source_paths` stores `Path.__str__` of the resolved input, which is machine-dependent (absolute vs corpus-relative depends on operator CWD). Capture as part of the manifest-hash / provenance lane.
- What stayed open: Phase C exit (retriever rewiring + promotion gate); broader Phase B remainder (manifest hash / provenance fields, entity-candidate + lexical-handle artifacts).
- Next single action: run `breadcrumb_query_run --route-equivalence-jsonl ...` against C1S1–C1S3 records to capture cohort `shadow_route_equivalences` baseline (Phase 4 diagnostics expansion).

### 2026-05-10 (UTC) — fourth entry, PR #3 merged + doc sync

- Phase moved: **`stayed B`**.
- What turned green: [PR #3](https://github.com/Drakosfire/DungeonMindBuddy/pull/3) **MERGED** to `main` (merge commit `98c09aaf0fead2aaaf4b3a7c90afcb09bae8026f`, 2026-05-10T05:06Z). Checklist Evidence/Reanchor lines synced to post-merge reality (remove stale “determinism pending”; add `--check` + full `tests/lexicon_phase_b/` counts).
- What stayed open: broader Phase B beyond route-equivalence JSONL (manifest hash / provenance lane, entity-candidate + lexical-handle artifacts per super-plan). Phase C retriever wiring not started.
- Next single action: wire breadcrumb / token-resolution harness to consume `route_equivalence_longmont_c*_v1.jsonl` behind an explicit flag, with deterministic tests (checklist Phase C).

### 2026-05-10 (UTC) — third entry, route-equivalence artifacts

- Phase moved: **`stayed B`**.
- What turned green: canonical Phase B route-equivalence outputs now committed at `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl` and `route_equivalence_longmont_c2_v1.jsonl`; deterministic regression landed at `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`.
- Evidence command excerpts: `uv run python scripts/build_route_equivalence_manifests.py --check` -> `OK ...c1...` / `OK ...c2...`; `uv run pytest tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py -q` -> `6 passed`.
- Next single action: begin Phase C retriever wiring against generated artifacts while keeping benchmark seeds as fallback.

### 2026-05-10 (UTC) — second entry, late

- Phase moved: **`A -> B`**.
- What turned green: re-verified `uv run python scripts/audit_world_campaign_alignment.py` -> `PASS` on current `main`. The three C1S13 location-context scenarios (`stormspire_activity_arrival`, `meat_storage_strongholds_locations`, `mossglade_residency_vs_association`) already carry non-empty `location_hierarchy_equivalences`; the prior session log claim that they were missing was stale. Phase A structural gates are all green.
- What stayed red: nothing on Phase A. Flagged as content-quality follow-up (not a phase blocker): two of the three C1S13 scenarios have hierarchy children that look copy-pasted from a different parent. Captured in `Backlog.md`.
- Next single action: stand up Phase B canonical artifact output + byte-stable regression test for `build_route_equivalence_manifest` against committed Campaign 1 / Campaign 2 `_npc_registry.json` files (archived handoff contract: `Docs/Plans/archive/2026-05-10/handoffs/HANDOFF-phase-b-route-equivalence-artifact-output.md`; shipped PR #3).

### 2026-05-10 (UTC) — first entry, early

- Phase moved: `stayed A`
- What turned green: PR #2 **MERGED** to `main` (merge commit `545cf37`, 2026-05-10T02:59Z); PR #1 closed as superseded. Phase 1 contract (`RouteEquivalenceRecord`) and early Phase 2 builder (`build_route_equivalence_manifest`) land with collision-safe `tests/lexicon_phase_b/` layout, `entity_kind == "unknown"` filter, `source_type` lineage docstring, and tested directory- vs file-shaped `hub_path` slug derivation.
- Pre-merge verification: `uv run pytest tests/lexicon_phase_b/ tests/test_token_resolution_resolver.py tests/test_token_resolution_contracts.py tests/test_benchmark_lexicon_seeds.py -q` -> 28 passed; `uv run python scripts/audit_world_campaign_alignment.py` -> PASS.
- What stayed red (corrected in next entry): the prior log re-stated the C1S13 hierarchy gate as red; live re-verification shows it is structurally green. Correction logged above.
- Next single action: archive the Phase A handoff and write a narrow Phase B handoff for canonical artifact output + byte-stable regression.

### 2026-05-09

- Phase moved: `stayed A`
- What turned green: `doc state sync after integration` (PR #1 status moved from parked to `integrated_on_main_pr_open` in the canonical super-plan + this checklist).
- What stayed red: `location hierarchy contract encoding` in C1S13 natural gold, and pending follow-up to validate/fix directory-style `hub_path` route-id derivation.
- Next single action: `close remaining Phase A hierarchy gate, then run targeted manifest route-id validation against live _npc_registry.json path shapes.`

### 2026-05-08

- Phase moved: `stayed A`
- What turned green: `registry authority split` and `manifest campaign-id normalization` checks.
- What stayed red: `location hierarchy contract encoding` in C1S13 natural gold (`location_hierarchy_equivalences` missing in three scenarios).
- Next single action: `patch C1S13 natural gold with explicit hierarchy equivalence mappings, then rerun uv run python scripts/audit_world_campaign_alignment.py`.

