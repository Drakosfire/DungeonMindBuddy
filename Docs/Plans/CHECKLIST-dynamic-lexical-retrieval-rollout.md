# Checklist — Dynamic Lexical Retrieval Rollout

**Purpose:** Operational tracker for moving from current ingestion state to dynamic lexical retrieval from ingestion artifacts.
**Decision anchor:** `Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md` (Roadmap section).
**Super plan (canonical, versioned):** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — YAML frontmatter, changelog, and milestone M1–M4; update that file when the execution narrative shifts.
**Phase 1 + early Phase 2 PR:** [DungeonMindBuddy#2](https://github.com/Drakosfire/DungeonMindBuddy/pull/2) — **MERGED** to `main` 2026-05-10T02:59Z (merge commit `545cf37`). [PR #1](https://github.com/Drakosfire/DungeonMindBuddy/pull/1) is **closed** (superseded). Canonical `judgment_record` for both is in the super-plan YAML `external_pull_requests`.
**Phase B route-equivalence artifacts PR:** [DungeonMindBuddy#3](https://github.com/Drakosfire/DungeonMindBuddy/pull/3) — **MERGED** to `main` 2026-05-10T05:06Z (merge commit `98c09aaf0fead2aaaf4b3a7c90afcb09bae8026f`): committed JSONL under `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/`, `scripts/build_route_equivalence_manifests.py` (`--write` / `--check`), byte-stable regression `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`, and `_is_campaign_path` fix for relative `Longmont Campaign/...` registry paths.
**Phase C entry shadow consumer PR:** [DungeonMindBuddy#4](https://github.com/Drakosfire/DungeonMindBuddy/pull/4) — **MERGED** to `main` 2026-05-10T16:22Z (merge commit `21e84392da03095377b4de36defb82edfc37c741`): adds `src/lexicon_phase_b/route_equivalence_loader.py`, `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py`, and `--route-equivalence-jsonl` (repeatable) CLI flag on `breadcrumb_query_run`. `shadow_route_equivalences` (`dmb_route_equivalence_shadow_v1`) is emitted only when the flag is set; legacy retrieval, grading, and `shadow_token_resolution` are unchanged. Round 2 added harness-boundary safety tests in `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py`.
**Status model:** keep exactly one phase marked as active at a time.

---

## Reanchor Block (fill first each session)

- [x] **Active phase:** `B` (with **Phase C entry** shadow consumer landed via PR #4; retriever wiring still gated for Phase C exit / promotion gate)
- [x] **Last green artifact (path):** `uv run python scripts/build_route_equivalence_manifests.py --check` -> `OK` for both `route_equivalence_longmont_c1_v1.jsonl` and `route_equivalence_longmont_c2_v1.jsonl` (2026-05-10); `uv run pytest tests/lexicon_phase_b/ -q` -> `17 passed` on post-PR #4 `main`; `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q` -> `10 passed` (round 2 harness-boundary tests included).
- [x] **Current blocking red gate:** none for shadow consumer lane. **Follow-up:** `uv run python scripts/audit_world_campaign_alignment.py` still fails in a clean checkout without `out/evals/corpus_remote/normalization_manifest.json` (pre-existing gate contract; track separately).
- [x] **Blocker type:** `n/a`
- [x] **Next command to run:** `uv run python scripts/build_route_equivalence_manifests.py --check && uv run pytest tests/lexicon_phase_b/ -q && uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q` (sanity gate). Then run `breadcrumb_query_run` against C1S1–C1S3 records with `--route-equivalence-jsonl evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl --route-equivalence-jsonl evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl` to capture the cohort `shadow_route_equivalences` baseline (Phase 4 diagnostics expansion / promotion-gate input). Broader Phase B remainder (manifest hash / provenance, entity-candidate + lexical-handle artifacts) remains open in parallel.

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

- [x] Lexical artifact schema defined and documented (`src/lexicon_phase_b/schemas.py::RouteEquivalenceRecord`, schema_version `0.2.0`, landed via PR #2).
- [x] Generator consumes ingestion outputs with route/provenance fields (`src/lexicon_phase_b/route_equivalence_manifest.py::build_route_equivalence_manifest` reads `_npc_registry.json` via `src/contracts/npc_registry.py`).
- [x] Generation is deterministic for fixed inputs (byte-stable output) — `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`; command: `uv run pytest tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py -q` -> `6 passed` (2026-05-10).
- [x] Artifact output path standardized and documented — canonical dir `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/`; documented in `evals/sentence_routing_retrieval_falsification/README.md` under `Route equivalence manifests (Phase B)`.

**Evidence**

- Schema + builder: `src/lexicon_phase_b/schemas.py`, `src/lexicon_phase_b/route_equivalence_manifest.py`.
- Committed artifacts: `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl`, `route_equivalence_longmont_c2_v1.jsonl` (PR #3).
- CLI: `scripts/build_route_equivalence_manifests.py` (`--write`, `--check`, `--out-dir`).
- Tests: `tests/lexicon_phase_b/test_route_equivalence_manifest.py`, `test_route_id_path_shapes.py`, `test_route_equivalence_record_defaults.py`, `test_route_equivalence_entity_kind_inference.py`, `test_route_equivalence_artifacts_byte_stable.py` (byte match + real-registry path-shape assertions).
- Lexicon suite: `uv run pytest tests/lexicon_phase_b/ -q` -> `16 passed` (post-PR #3 `main`).
- Token-resolution regression guard: `uv run pytest tests/test_token_resolution_resolver.py tests/test_token_resolution_contracts.py tests/test_benchmark_lexicon_seeds.py -q` -> `28 passed` (unchanged surface).
- Determinism check: `uv run python scripts/build_route_equivalence_manifests.py --check` -> `OK` both artifacts (2026-05-10).

---

## Phase C — Retriever wiring (existing retriever, dynamic source)

**Goal:** retriever uses generated lexical artifact as primary source.

**Status:** **entry landed** (PR #4 — shadow consumer behind `--route-equivalence-jsonl`, no retrieval/grading change). **Exit not started** (legacy lexical seeds remain authoritative; no promotion gate yet).

- [x] **Entry:** harness consumes generated artifact behind explicit flag, shadow-only; per-scenario `shadow_route_equivalences` (`dmb_route_equivalence_shadow_v1`) emitted alongside `shadow_token_resolution` (PR #4).
- [x] **Entry safety:** byte-identity-when-flag-unset and load-failure-emits-error tested at the harness boundary, not just the loader (PR #4 round 2; the round-1 gap that became the rubric bullet "test the boundary that owns the rubric").
- [ ] Existing lexical retriever wired to generated artifact (Phase C **exit**).
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

