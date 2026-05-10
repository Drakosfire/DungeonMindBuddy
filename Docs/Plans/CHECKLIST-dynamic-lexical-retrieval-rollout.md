# Checklist — Dynamic Lexical Retrieval Rollout

**Purpose:** Operational tracker for moving from current ingestion state to dynamic lexical retrieval from ingestion artifacts.
**Decision anchor:** `Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md` (Roadmap section).
**Super plan (canonical, versioned):** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — YAML frontmatter, changelog, and milestone M1–M4; update that file when the execution narrative shifts.
**Phase 1 + early Phase 2 PR:** [DungeonMindBuddy#2](https://github.com/Drakosfire/DungeonMindBuddy/pull/2) — **MERGED** to `main` 2026-05-10T02:59Z (merge commit `545cf37`). [PR #1](https://github.com/Drakosfire/DungeonMindBuddy/pull/1) is **closed** (superseded). Canonical `judgment_record` for both is in the super-plan YAML `external_pull_requests`.
**Status model:** keep exactly one phase marked as active at a time.

---

## Reanchor Block (fill first each session)

- [x] **Active phase:** `B`
- [x] **Last green artifact (path):** `uv run python scripts/audit_world_campaign_alignment.py` -> `World/Campaign alignment audit: PASS` (1 manifest + 5 breadcrumb natural gold files; 2026-05-10).
- [x] **Current blocking red gate:** none (Phase A structural gates green; Phase B determinism + canonical artifact path is the next gate).
- [x] **Blocker type:** `n/a`
- [x] **Next command to run:** `uv run pytest tests/lexicon_phase_b/ -q` plus the new byte-stable manifest regression once it lands (see active Phase B handoff).

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
- Tests (4 files, 8 cases): `tests/lexicon_phase_b/test_route_equivalence_manifest.py`, `test_route_id_path_shapes.py`, `test_route_equivalence_record_defaults.py`, `test_route_equivalence_entity_kind_inference.py`.
- Pre-merge gate: `uv run pytest tests/lexicon_phase_b/ tests/test_token_resolution_resolver.py tests/test_token_resolution_contracts.py tests/test_benchmark_lexicon_seeds.py -q` -> 28 passed (2026-05-10).
- Determinism check command + result: pending — needs cohort-level byte-stable test against committed registries for both `Longmont Campaign/Campaign 1/_npc_registry.json` and `Campaign 2/_npc_registry.json`.

---

## Phase C — Retriever wiring (existing retriever, dynamic source)

**Goal:** retriever uses generated lexical artifact as primary source.

- [ ] Existing lexical retriever wired to generated artifact.
- [ ] Static/hand-seeded lexical source moved to fallback mode only.
- [ ] Deterministic test proves retrieval runs with generated-only lexical source.
- [ ] Failure mode diagnostics distinguish "missing lexical handle" vs retriever bug.

**Evidence**

- Wiring PR/files: `...`
- Test command + result: `...`

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

### 2026-05-10 (UTC) — third entry, route-equivalence artifacts

- Phase moved: **`stayed B`**.
- What turned green: canonical Phase B route-equivalence outputs now committed at `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl` and `route_equivalence_longmont_c2_v1.jsonl`; deterministic regression landed at `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`.
- Evidence command excerpts: `uv run python scripts/build_route_equivalence_manifests.py --check` -> `OK ...c1...` / `OK ...c2...`; `uv run pytest tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py -q` -> `6 passed`.
- Next single action: begin Phase C retriever wiring against generated artifacts while keeping benchmark seeds as fallback.

### 2026-05-10 (UTC) — second entry, late

- Phase moved: **`A -> B`**.
- What turned green: re-verified `uv run python scripts/audit_world_campaign_alignment.py` -> `PASS` on current `main`. The three C1S13 location-context scenarios (`stormspire_activity_arrival`, `meat_storage_strongholds_locations`, `mossglade_residency_vs_association`) already carry non-empty `location_hierarchy_equivalences`; the prior session log claim that they were missing was stale. Phase A structural gates are all green.
- What stayed red: nothing on Phase A. Flagged as content-quality follow-up (not a phase blocker): two of the three C1S13 scenarios have hierarchy children that look copy-pasted from a different parent. Captured in `Backlog.md`.
- Next single action: stand up Phase B canonical artifact output + byte-stable regression test for `build_route_equivalence_manifest` against committed Campaign 1 / Campaign 2 `_npc_registry.json` files (see active handoff: `Docs/Plans/HANDOFF-phase-b-route-equivalence-artifact-output.md`).

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

