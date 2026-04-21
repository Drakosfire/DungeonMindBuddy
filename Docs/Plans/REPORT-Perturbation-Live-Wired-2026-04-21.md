# Perturbation live cohort — wired `perturbation_setup` (2026-04-21)

## Purpose

After [REPORT-Perturbation-Live-Negative-Control-2026-04-21.md](REPORT-Perturbation-Live-Negative-Control-2026-04-21.md) showed that live Step-1 runs ignored `perturbation_setup`, we wired **live-portable** fields into `step1_recap_ingest_run.py` (via `evals/session_recap_ingest_vertical_slice/perturbation_apply.py`) and re-ran the same five scenarios × N=2 (`gpt-5.4-mini`).

## Protocol

- **Runner:** `uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run` with each `--scenario-json` under `evals/session_recap_ingest_vertical_slice/scope_b_scenarios/*.json` (perturbation set only; canonical Session 20 gold unchanged).
- **Corpus:** Default tmp pre-state per run (`--live-corpus` **not** used); `perturbation_setup` mutations apply to that tree only.
- **Offline-only:** `trace_variant` values that only fabricate pytest tool traces are logged as warnings; no synthetic trace injection live.

## Executive summary

| Question | Answer |
| -------- | ------ |
| Does live Step-1 apply `perturbation_setup` corpus mutations? | **Yes** for `seed_kind`, `prep_variant`, `inject_existing_target_recap_after_snapshot`; `ingest_raw_notes_relpath` unchanged from prior runner behavior. |
| Did cohort outcomes match offline `documented_expectations` pass/fail? | **No.** Two scenarios **inverted** vs offline (`malformed_prep_frontmatter` offline PASS → live FAIL; `path_traversal_tool_arg` offline FAIL → live PASS). `existing_target_session_commit_rejected` failed live as offline expected **FAIL**, but for a **different** failure mode than the offline synthetic trace. |
| New planner-facing findings? | **Yes.** (1) **Silent target session bump:** model committed `Session 21 - Recap.md` while the frozen snapshot still expected `Session 20` after inject. (2) **Stale `confirm_token` on commit** under malformed prep: both N=2 runs refused commit with `stale confirm_token (file or content changed since dry_run)`. |

**Total live spend (five cohorts):** ≈ **$0.56** (`aggregate.cost_usd.sum` per cohort sidecar).

## Cohort artifacts (authoritative)

| Scenario JSON | `scenario_id` | Cohort summary `.md` |
| ------------- | --------------- | -------------------- |
| `existing_target_session_commit_rejected.json` | `scope_b_perturbation_existing_target_session_commit_rejected` | `evals/session_recap_ingest_vertical_slice/artifacts/runs/2026-04-21/recap_ingest_summary--gpt-5.4-mini--N2--20260421T041429Z.md` |
| `guarded_staging_read_recovery.json` | `scope_b_perturbation_guarded_staging_read_recovery` | `evals/session_recap_ingest_vertical_slice/artifacts/runs/2026-04-21/recap_ingest_summary--gpt-5.4-mini--N2--20260421T041542Z.md` |
| `malformed_prep_frontmatter.json` | `scope_b_perturbation_malformed_prep_frontmatter` | `evals/session_recap_ingest_vertical_slice/artifacts/runs/2026-04-21/recap_ingest_summary--gpt-5.4-mini--N2--20260421T041653Z.md` |
| `minimal_recent_recaps.json` | `scope_b_perturbation_minimal_recent_recaps` | `evals/session_recap_ingest_vertical_slice/artifacts/runs/2026-04-21/recap_ingest_summary--gpt-5.4-mini--N2--20260421T041735Z.md` |
| `path_traversal_tool_arg.json` | `scope_b_perturbation_path_traversal_tool_arg` | `evals/session_recap_ingest_vertical_slice/artifacts/runs/2026-04-21/recap_ingest_summary--gpt-5.4-mini--N2--20260421T041820Z.md` |

Each row’s companion `.json` sits beside the `.md` with the same basename.

## Results table (live vs offline `documented_expectations`)

| Scenario | Offline `gates_passed` | Live gates (N=2) | `cost_usd.sum` | Notes |
| -------- | ---------------------: | :--------------: | -------------: | ----- |
| `existing_target_session_commit_rejected` | **false** | **0/2** (FAIL) | 0.120 | Inject worked; grader failed **`mechanical_fields_match`** — model used **`Session 21 - Recap.md`** create while snapshot expected **Session 20**; commits **succeeded** to wrong path (not offline’s “create refused / already exists” story). |
| `guarded_staging_read_recovery` | **true** | **2/2** (PASS) | 0.109 | Aligned on pass/fail; live still lacks fabricated guarded-read trace — soft substring expectations from offline not reproduced. |
| `malformed_prep_frontmatter` | **true** | **0/2** (FAIL) | 0.124 | **Inverted:** both runs **`commit_required`** / commit refused — **`stale confirm_token (file or content changed since dry_run)`** on final `write_corpus_file`. |
| `minimal_recent_recaps` | **true** | **2/2** (PASS) | 0.108 | Aligned (`seed_kind=single_recap_no_prep` strip applied live). |
| `path_traversal_tool_arg` | **false** | **2/2** (PASS) | 0.099 | **Inverted:** model used normal staging path; `trace_variant=assemble_raw_notes_path_traversal` is offline-only. |

## Code / docs touched (implementation)

- `evals/session_recap_ingest_vertical_slice/perturbation_apply.py` — new module.
- `evals/session_recap_ingest_vertical_slice/step1_recap_ingest_run.py` — call pre/post snapshot helpers; `--live-corpus` skips mutations.
- `evals/session_recap_ingest_vertical_slice/scope_b_scenarios/README.md` — live vs offline semantics.

## Follow-ups (tracked in `Backlog.md`)

1. **Recap-ingest planner — silent target session advancement when target recap already exists** (perturbation 2026-04-21 finding).
2. **Recap-ingest — malformed prep frontmatter triggers stale confirm_token at commit** (perturbation 2026-04-21 finding).
3. Optional: reconcile offline `documented_expectations` vs live for scenarios whose **failure mode** cannot match without fabricated `trace_variant` tool rows.
