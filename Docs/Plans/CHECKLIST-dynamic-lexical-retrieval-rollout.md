# Checklist — Dynamic Lexical Retrieval Rollout

**Purpose:** Operational tracker for moving from current ingestion state to dynamic lexical retrieval from ingestion artifacts.
**Decision anchor:** `Docs/Design/DECISION-world-campaign-knowledge-hierarchy.md` (Roadmap section).
**Super plan (canonical, versioned):** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — YAML frontmatter, changelog, and milestone M1–M4; update that file when the execution narrative shifts.
**PR #1 (partial Phase 1):** [DungeonMindBuddy#1](https://github.com/Drakosfire/DungeonMindBuddy/pull/1) — `review_status: parked_until_phase_gate` until Phase 1; rubric and `judgment_record` live in that PLAN’s YAML `external_pull_requests`.
**Status model:** keep exactly one phase marked as active at a time.

---

## Reanchor Block (fill first each session)

- [x] **Active phase:** `A`
- [x] **Last green artifact (path):** `uv run python scripts/lint_npc_registry.py --path "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json"` and same command for Campaign 2 (both green, 2026-05-08)
- [x] **Current blocking red gate:** missing `location_hierarchy_equivalences` in C1S13 location-context scenarios (`stormspire_activity_arrival`, `meat_storage_strongholds_locations`, `mossglade_residency_vs_association`)
- [x] **Blocker type:** `structural`
- [x] **Next command to run:** `uv run python scripts/audit_world_campaign_alignment.py`

---

## Phase A — Deterministic guardrails

**Goal:** structural drift fails before LLM tuning.

- [x] Registry authority split gate green (`hub_path` campaign authority, `setting_hub_path` world fallback).
- [x] Remote manifest campaign IDs normalized (`longmont-cN` for campaign rows).
- [ ] Location hierarchy contract encoded in relevant gold scenarios.
- [ ] Alignment audit target green:
  - `uv run python scripts/audit_world_campaign_alignment.py`

**Evidence**

- Last green audit artifact/log: `uv run python scripts/audit_world_campaign_alignment.py` now fails only on hierarchy omissions (registry + manifest lanes are green), 2026-05-08.
- Remaining A-phase violations (if any): `hierarchy:.../breadcrumb_query_natural_c1s13_v1.json` missing non-empty `location_hierarchy_equivalences` for three location-context scenarios.

---

## Phase B — Dynamic lexical artifact generation

**Goal:** lexical match inventory derives from ingestion outputs.

- [ ] Lexical artifact schema defined and documented.
- [ ] Generator consumes ingestion outputs with route/provenance fields.
- [ ] Generation is deterministic for fixed inputs (byte-stable output).
- [ ] Artifact output path standardized and documented.

**Evidence**

- Artifact example path: `...`
- Determinism check command + result: `...`

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

### 2026-05-08

- Phase moved: `stayed A`
- What turned green: `registry authority split` and `manifest campaign-id normalization` checks.
- What stayed red: `location hierarchy contract encoding` in C1S13 natural gold (`location_hierarchy_equivalences` missing in three scenarios).
- Next single action: `patch C1S13 natural gold with explicit hierarchy equivalence mappings, then rerun uv run python scripts/audit_world_campaign_alignment.py`.

