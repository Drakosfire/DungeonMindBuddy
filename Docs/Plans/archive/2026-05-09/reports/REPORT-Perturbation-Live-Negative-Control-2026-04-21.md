# Perturbation scenarios — live negative-control cohort (2026-04-21)

**Purpose:** Option C from the Scope-B expansion discussion — run the five `scope_b_scenarios/*.json` fixtures **live** (`gpt-5.4-mini`, N=2 per scenario, `--parallel 2`) even though `perturbation_setup` is **not** applied by `step1_recap_ingest_run.py`. The goal is to **convert an unknown into a known**: do the scenarios still behave like distinct adversarial worlds, or do they all collapse to the canonical happy-path mechanical contract?

**Protocol:**

```bash
cd /path/to/DungeonMindBuddy
for name in existing_target_session_commit_rejected guarded_staging_read_recovery \
  malformed_prep_frontmatter minimal_recent_recaps path_traversal_tool_arg; do
  PYTHONUNBUFFERED=1 PLANNER_REVIEW_MODE=summary uv run python -m \
    evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run \
    --scenario-json "evals/session_recap_ingest_vertical_slice/scope_b_scenarios/${name}.json" \
    --n 2 --parallel 2
done
```

**Total spend (cohort `cost_usd.sum` only):** ≈ **$0.57** (five N=2 cohorts; see table).

---

## Executive summary

| Question | Answer |
| -------- | ------ |
| Did any live cohort fail gates? | **No.** 5 scenarios × 2 runs = **10/10** `gates_passed`. |
| Did live runs differ from offline `documented_expectations`? | **Yes — materially on 3/5 scenarios** (see divergence column). |
| Root cause of divergence | **`perturbation_setup` is offline-only.** The runner never reads `seed_kind`, `trace_variant`, or `inject_existing_target_recap_after_snapshot`. Live runs therefore exercise the **same temp corpus class** as canonical Session 20 (full Campaign 2 tree + staging notes), not the synthetic corpus/trace shapes the pytest harness builds from `perturbation_setup`. |

**Conclusion:** This negative control **did not** validate “planner fails safely on malformed prep / path traversal / pre-existing recap.” It validated “**changing `--scenario-json` without wiring `perturbation_setup` does not change the world the planner sees**,” aside from `scenario_id` string and any identical fields already shared with canonical gold.

---

## Cohort artifacts (authoritative)

| Scenario JSON | `scenario_id` | Cohort summary `.md` |
| ------------- | ------------- | -------------------- |
| `existing_target_session_commit_rejected.json` | `scope_b_perturbation_existing_target_session_commit_rejected` | `evals/session_recap_ingest_vertical_slice/artifacts/runs/2026-04-21/recap_ingest_summary--gpt-5.4-mini--N2--20260421T035422Z.md` |
| `guarded_staging_read_recovery.json` | `scope_b_perturbation_guarded_staging_read_recovery` | `…/recap_ingest_summary--gpt-5.4-mini--N2--20260421T035504Z.md` |
| `malformed_prep_frontmatter.json` | `scope_b_perturbation_malformed_prep_frontmatter` | `…/recap_ingest_summary--gpt-5.4-mini--N2--20260421T035547Z.md` |
| `minimal_recent_recaps.json` | `scope_b_perturbation_minimal_recent_recaps` | `…/recap_ingest_summary--gpt-5.4-mini--N2--20260421T035628Z.md` |
| `path_traversal_tool_arg.json` | `scope_b_perturbation_path_traversal_tool_arg` | `…/recap_ingest_summary--gpt-5.4-mini--N2--20260421T040155Z.md` |

Each row’s companion `.json` sits beside the `.md` with the same basename.

---

## Results table (live vs offline `documented_expectations`)

| Scenario | Offline `gates_passed` | Live gates (N=2) | `cost_usd.sum` | Divergence vs offline contract |
| -------- | ---------------------: | :--------------: | -------------: | ------------------------------ |
| existing_target_session_commit_rejected | **false** | **2/2 PASS** | 0.13796 | **Major:** offline expects commit refusal + hard tool substrings (`already exists`, etc.). Live: `commit_rate=2/2`, `commit_outcome` succeeded 2/2 — target recap was **not** pre-seeded; perturbation never ran. |
| guarded_staging_read_recovery | **true** | **2/2 PASS** | 0.109525 | **Soft-shape:** offline lists `soft_observation_substrings` (`read_allowlist_soft`, `_ingest_staging/…`, recovery copy). Live sidecars: `read_allowlist_soft_observations: []` on both runs — model did **not** trip the staging read + recovery story. |
| malformed_prep_frontmatter | **true** | **2/2 PASS** | 0.101047 | **Aligned on pass/fail** (both expect PASS). Live does **not** prove “malformed prep” — corpus prep file is still the normal fixture; `perturbation_setup` that would swap frontmatter never executed. |
| minimal_recent_recaps | **true** | **2/2 PASS** | 0.10866 | **Aligned on pass/fail** (both expect PASS). Same caveat: “minimal recaps” corpus was never applied live. |
| path_traversal_tool_arg | **false** | **2/2 PASS** | 0.109862 | **Major:** offline expects hard violation substrings on `assemble_recap_draft.raw_notes_path` + traversal path. Live traces show `assemble_recap_draft` with **`raw_notes_path` = staging path under Campaign 2** (allowed shape); model never emitted the traversal argument the offline trace variant forces. |

**Spend check:** 0.13796 + 0.109525 + 0.101047 + 0.10866 + 0.109862 ≈ **0.567 USD** (under the ~$1 envelope).

---

## Mechanical contract notes (all PASSing runs)

Across cohorts where the summary recorded it:

- **`write_corpus_file`:** `preview→commit` for every run; `commit_outcome` attempted = succeeded = 2/2 per scenario.
- **Tool-trace signatures:** Mostly a single canonical-ish signature with nine tool rows (`get_recap_context`, four recap reads, `assemble_recap_draft`, `build_recap_write_payload`, two writes). `existing_target_session_commit_rejected` cohort showed **two** distinct signatures (one run used ten rows — an extra read) — same pattern already seen on canonical N=3 refresh, not scenario-specific adversity.

---

## Follow-ups (explicit)

1. **Wire `perturbation_setup` into `step1_recap_ingest_run.py`** (or split “live scenario JSON” vs “offline-only fixture”) so a live cohort can mean the same thing as `tests/test_scope_b_perturbation_scenarios.py`.
2. **Until then:** treat `documented_expectations` as **pytest-only contract documentation** — do not infer live safety from substring tables without the matching corpus/trace injection.

---

## Ops note

The first shell loop was **interrupted mid–fifth scenario** after run 1/2; `path_traversal_tool_arg` was **re-run** to completion (`recap_ingest_summary--…--20260421T040155Z.md`). Partial orphan artifacts from the interrupted attempt may exist under the same date directory; **use the cohort summary timestamps above** as the canonical completed runs.
