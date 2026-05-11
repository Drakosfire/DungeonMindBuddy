---
# Optional workflow contract: literal markdown the worker pastes into the
# GitHub PR description. Dispatcher fills once; reviewers and parallel
# agents see one stable shape without inferring sections from free-form §2 prose.
pr_body_template: |
  ## Summary

  Land **A/B Benchmarking Sprint L2** ("would-this-help" leading indicator): add an additive `expected_route_substring_breakdown` per-row field to `breadcrumb_query_run.py`, derive `recall_via_equivalence` per-scenario in `cohort_baseline_run.py`, bump the cohort summary schema to `dmb_breadcrumb_query_cohort_summary_v2`, and reroll the C1S1–C1S3 baseline accordingly. **Does not change retrieval.** Does not include a wider cohort (records files for `c1s13_v1` / `natural_v1` do not exist on disk yet — that is a separate slice).

  ## Verification (verbatim §7)

  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat origin/main...HEAD` (§4 paths only)

  ```text
  {{TODO}}
  ```

  ## What stayed unchanged

  {{TODO: one paragraph — `route_equivalence_shadow.py` untouched; `route_equivalence_loader.py` untouched; producer-side JSONL artifacts untouched; gold untouched; grader untouched (`hits_cover_expected_routes` semantics reused, not redefined); legacy retrieval ranking unchanged; canvases untouched.}}
---

> **COMPLETED — 2026-05-11T02:59:47Z.** Shipped via [PR #7](https://github.com/Drakosfire/DungeonMindBuddy/pull/7) (`main` merge commit `0036df30e5f53abd7ba76ab510483a9e1df0d3fa`). Single round of review (PR head `2bc6ad9e`); APPROVE demoted to `COMMENTED` verdict banner under self-review fallback (`pullrequestreview-4260504200`). Delivers additive `expected_route_substring_breakdown` on `breadcrumb_query_run.py`, `recall_via_equivalence` / aggregate on `cohort_baseline_run.py`, schema `dmb_breadcrumb_query_cohort_summary_v2`, frozen `cohort_baseline_c1s1_to_c1s3_v2.json` (v1 baseline removed), tests 47-pass regression bundle. §7 all green; `--write` smoke BYTE-IDENTICAL vs committed v2 baseline; `canvases/` clean; cost `$0`. Tight cohort: per-scenario `recall_via_equivalence: null` (denominator zero — expected L2 readout). Post-merge doc-sync: `PLAN-split-corpus-retrieval-to-autonomous-demo.md` v14, `CHECKLIST-dynamic-lexical-retrieval-rollout.md`, `external_pull_requests` gains `github-pr-7` with four NEW `rubric_when_we_judge` bullets; PLAN narrative renumber (producer lane -> PR #8). **Archived for historical reference; do not re-dispatch.**

# HANDOFF — Shadow recall-via-equivalence (L2 leading indicator) for C1S1 + C1S2 + C1S3

**Created:** 2026-05-11 (UTC).
**Status:** COMPLETED — see banner above. (Was: ACTIVE — dispatch this to one external/Codex subagent. **One PR.** Do not split into multiple PRs.)
**Parent agent:** Cursor agent; dispatcher is responsible for the post-merge doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc` and `.cursor/rules/anchor.mdc` (workstream-scope re-anchor).
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` v13 (`active_phase: B`, milestone progress **M2 in_progress · M3 in_progress**). This handoff opens the **A/B Benchmarking Sprint L2** workstream — the slice the PLAN's `next_gate_command` and § *A/B Benchmarking Sprint (post-PR #5)* call **"PR 6.5 / extension to PR 6 — shadow recall metric."** GitHub will assign **#7** when the PR opens; the post-merge atomic doc-sync will reconcile PLAN narrative numbering (`6.5` → `7`; producer-side `manifest_hash` lane in PLAN narrative bumps from `7` to `8`).

---

## §1 Mission

Add a **derived diagnostic field**, `recall_via_equivalence`, to the curated cohort summary produced by `cohort_baseline_run.py`. Per scenario, this answers: *of the gold's `expect_route_substrings` that today's retriever did NOT surface, what fraction would have been reachable through the loaded route-equivalence records?* Aggregate as `min/mean/max/scenarios_with_misses` across the cohort. **Does not change retrieval, ranking, the grader, or any gold file.** Bumps the cohort summary schema to `dmb_breadcrumb_query_cohort_summary_v2` and rerolls the baseline.

The metric requires structured per-substring miss evidence. The grader currently emits only the binary verdict `missing_expected_route_hit` in `violations`. To avoid the cohort runner re-implementing route matching by parsing free-text retrieval context (brittle), this PR adds one **purely additive** field to `breadcrumb_query_run`'s per-row report:

```text
"expected_route_substring_breakdown": [
  {"substring": "Campaign 1/PCs/karsemine", "matched": true},
  {"substring": "Campaign 1/Locations/wizards_tower_brewing_company", "matched": true},
  ...
]
```

The cohort runner consumes that field, attributes unmatched substrings to equivalence rescues via a small named bridging helper (defined below), and emits `recall_via_equivalence`. Retrieval, ranking, grading, and the legacy violation surface are unchanged. The new harness field is emitted unconditionally (always-present, even when `expect_route_substrings` is empty — then `[]`); legacy consumers that ignore unknown fields are unaffected.

## §2 Why this slice (context for the subagent)

- **PR #6** (merge `9af4741a635125d3403d66a9f266564f25bad746`, 2026-05-11T01:49Z) shipped **L1**: a frozen byte-stable cohort baseline at `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json` (`dmb_breadcrumb_query_cohort_summary_v1`). Aggregate: 44/44 questions `all_scenarios_all_ok`. **PR #6's `judgment_record.notes` and the PLAN's A/B sprint § *Concrete deliverables*** name **L2** as the next deliverable.
- **The retriever has not changed across PRs #2–#6.** `session_memory_query.py` and the breadcrumb ranking still use the legacy `build_campaign_lexicon` / benchmark-seeds path. Route-equivalence JSONL is consumed only as the `shadow_route_equivalences` diagnostic. **L2 = "would the new architecture have helped, on a baseline we already trust?"** without flipping retrieval. **L3** = true A/B = wiring change = a separate later slice (PLAN narrative PR 9, possibly re-sequenced ahead of producer-side `manifest_hash`).
- **Honest expectation, not a defect.** With L1 at 44/44 on this tight cohort, the metric's denominator (per-scenario miss count) is **expected to be zero for every scenario in C1S1–C1S3.** That means `recall_via_equivalence` will be `null` for every scenario in the rerolled baseline. **This is the correct L2 result on this cohort**, and is the leading-indicator signal the PLAN's re-sequencing question asks for: "tight cohort has no headroom; expand cohort to find the signal." This handoff therefore treats the **denominator-zero contract** (returning `null`, never `1.0` or omitted) as the load-bearing rubric, alongside byte-stability. A future PR will add a wider cohort manifest (likely `cohorts/c1s1_c1s3_c1s13_natural_v1.json`) once records files exist for `c1s13_v1` / `natural_v1` (they do **not** exist today — verified `Glob` returns 0 files for `evals/.../artifacts/*c1s13*` and `*natural*`).
- **Why this slice is NOT producer-side `manifest_hash`** (PLAN narrative PR 7 → 8 after this lands): file scopes don't overlap. They can ship in either order; L2 is cheaper to author + has lower risk.
- **Scope honesty — what this slice does NOT do:**
  - No retriever rewiring. No new ranking signal. `session_memory_query.py` and breadcrumb ranking untouched.
  - No grader change. `hits_cover_expected_routes` semantics are **reused** (the new harness field uses the same matching primitive); **not redefined.**
  - No new gold field. No gold edits.
  - No producer-side `manifest_hash` (sibling lane).
  - No new manifest. No wider cohort. Only the existing `cohorts/c1s1_to_c1s3_v1.json` is exercised.
  - No LLM calls (`--retrieval-only` stays mandatory). Cost stays `$0`.
  - No canvas perturbation.

## §3 Authoritative inputs (read these before writing code)

| Path | Why |
|---|---|
| `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | The runner you are extending. `build_cohort_summary` is where the new field lands; `_write_mode` already loads `route_equivalence_jsonl` paths. **Lines 70–113** of current `main` are the curation site. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` lines 1121–1180 | The per-row enrichment site (after `grade_natural_scenario`). The new `expected_route_substring_breakdown` field is appended **here**, in the same block as `row["retrieved_context"]`. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_grader.py` lines 43–67 | The matching primitive `hits_cover_expected_routes`. **Reuse its substring-in-`normalized_route` semantics**; do NOT redefine matching in this PR. The new harness field exposes per-substring `matched` booleans using the same logic. |
| `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py` | Source of `load_route_equivalence_shadow_records(paths) -> list[RouteEquivalenceRecord]`. Use it to load the records once in `_write_mode` and pass into `build_cohort_summary`. Do **not** modify this file. |
| `src/lexicon_phase_b/schemas.py` | `RouteEquivalenceRecord` fields used by the bridging helper (`from_route_id`, `to_route_id`). Do not modify. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl` (line 1) | Real-shape edge — `from_route_id: "route:longmont-c1:npc:captain-lysandra-ironveil"`, `to_route_id: "route:elderwyld:npc:captain-lysandra-ironveil"`. Slug component (`captain-lysandra-ironveil`) is the bridging hinge. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s1_v1.json` | Real-shape `expect_route_substrings` (`"Campaign 1/PCs/karsemine"`, `"Campaign 1/Locations/wizards_tower_brewing_company"`). Last `/`-segment is the bridging hinge from the gold side. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json` | Current PR #6 baseline. **This file is deleted by this PR**; replaced by `_v2.json`. |
| `tests/test_cohort_baseline_run.py` | Existing 9 tests. The PR #6 harness-boundary CWD-invariance test (`test_cohort_baseline_run_write_is_byte_identical_across_cwds`) is **carried forward** with its baseline path bumped from `_v1.json` to `_v2.json` — it must still pass against the rerolled file. |
| `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | Existing 11 tests. **+1** test: assert the new harness row field is present, well-shaped, and consistent with the existing `violations` / `missing_expected_route_hit` signal (matched-count parity). |
| `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` § *A/B Benchmarking Sprint (post-PR #5)* (lines 749–805 approx) | Authoritative L1/L2/L3 framing and the open re-sequencing question. |
| `.cursor/rules/anti-oracle-leakage.mdc` (always-on) | The new metric reads gold (`expect_route_substrings`) into a benchmarking-call output. This is fine because it is a **grader-side derivation**, not a generation input. **§9 below explicitly forbids this field ever being plumbed back into retrieval as a ranking signal.** |
| `.cursor/rules/external-agent-pr-loop.mdc` invariant #2 ("test the boundary that owns the rubric") | The harness-boundary CWD-invariance test from PR #6 is the canonical pattern. Mirror it for the new field. |

## §4 Allowlist — only these paths may be touched

| Path | Mode | Lines (rough) | Role |
|---|---|---|---|
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | modify | +5 / -0 | Add `expected_route_substring_breakdown` row field after `grade_natural_scenario` (in the same enrichment block as `row["retrieved_context"]`). |
| `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | modify | +60 / -10 | Add `_normalize_substring_to_slug`, `_equivalence_can_rescue`, `_compute_recall_via_equivalence`; thread `route_equivalence_records` into `build_cohort_summary`; bump schema constant; bump `_DEFAULT_BASELINE` filename to `_v2.json`. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json` | **delete** | -321 / +0 | Replaced by `_v2.json`. PR #6's L1 contract is preserved by the v2 baseline (same scenarios, additional field). |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` | add | +~340 | New schema (`dmb_breadcrumb_query_cohort_summary_v2`) frozen baseline. Generated via `cohort_baseline_run --write` on a clean checkout. |
| `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | modify | +20 / -0 | +1 test: `test_expected_route_substring_breakdown_is_consistent_with_violations`. Total → 12 passed. |
| `tests/test_cohort_baseline_run.py` | modify | +120 / -5 | +4 tests for bridging + recall + denominator-zero + schema-bump; bump CWD-invariance test's baseline path. Total → 13 passed. |

**Total: 6 paths.** All other files are out of scope.

## §5 Denylist — anything else is scope creep, revert if touched

| Path | Why it is out of scope |
|---|---|
| `src/lexicon_phase_b/**` | Producer side; sibling lane (PLAN narrative PR 8) owns it. |
| `tests/lexicon_phase_b/**` | Pairs with `src/lexicon_phase_b/**`. |
| `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py` | Already shipped in PR #4/#5; its rubric is closed. Use it as a library only. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_grader.py` | Grader semantics reused, not redefined. The new harness field uses `hits_cover_expected_routes`-equivalent logic — call it, don't reimplement matching. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_canvas_payload.py` | Canvas not touched. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_rank_report.py` | Rank report not touched. |
| `evals/sentence_routing_retrieval_falsification/c1s*_benchmark_canvas_emit.py` | Canvas emitters not touched. |
| `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` | The cohort manifest is byte-stable; only the **baseline** file rerolls. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c*_v1.jsonl` | Producer-side artifacts; sibling lane owns them. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold is never edited in this PR. |
| `evals/sentence_routing_retrieval_falsification/artifacts/c1s2_norm_smoke.records_meta.jsonl` | Records are never edited. |
| `evals/sentence_routing_retrieval_falsification/artifacts/c1s3_norm_smoke.records_meta.jsonl` | Records are never edited. |
| `evals/sentence_routing_retrieval_falsification/artifacts/last_session1_c1_breadcrumb_records.jsonl` | Records are never edited. |
| `evals/sentence_routing_retrieval_falsification/artifacts/.gitignore` | Not touched. |
| `evals/sentence_routing_retrieval_falsification/README.md` | Documentation update is welcome **only** if you also touch the runner; if you do, keep it strictly factual (one sentence noting `--check` enforces both schemas going forward is fine). Otherwise leave it alone. |
| `tests/test_token_resolution_*.py` | Different surface; out of scope. |
| `tests/test_benchmark_lexicon_seeds.py` | Different surface; out of scope. |
| `scripts/build_route_equivalence_manifests.py` | Producer-side; sibling lane owns it. |
| `src/agent/session_memory_query.py` | Retriever wiring belongs to L3 (PLAN narrative PR 9). |
| `canvases/**` | Never touched. The cohort runner's `--skip-*-canvas-refresh` flags ensure this; the §7 verification check enforces it. |
| `corpus/**` | Never touched. |
| `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` | Doc-sync happens **after** merge by the parent agent, not by the worker. |
| `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` | Doc-sync happens **after** merge by the parent agent, not by the worker. |
| `Docs/Plans/HANDOFF-*.md` | Doc-sync happens **after** merge. The worker does not move handoffs. |
| `Docs/Plans/archive/**` | Doc-sync happens **after** merge. |
| `.cursor/rules/*.mdc` | Always-on; not touched in this PR. |
| `.cursor/skills/**` | Skills not touched in this PR. |

## §6 Implementation contract (precise; deviations are review failures)

### 6.1 Bridging algorithm (exact spec)

```python
# In cohort_baseline_run.py — module-level helpers.

def _normalize_substring_to_slug(s: str) -> str:
    """Convert a gold expect_route_substring into a slug suitable for
    substring matching against route_equivalence record IDs.

    Algorithm (deterministic, no external state):
      1. Take the LAST '/'-separated segment of the input.
         "Campaign 1/PCs/karsemine"      -> "karsemine"
         "campaign 1/locations/wizards_tower_brewing_company"
                                         -> "wizards_tower_brewing_company"
      2. Strip surrounding whitespace; lowercase.
      3. Replace '_' with '-'  (gold uses underscores; route IDs use hyphens).
      4. Return the result.

    No tokenization, no stemming, no normalization tables. The bridging is
    intentionally narrow: if the simple slug-tail substring match misses,
    that is a true miss (and a signal that a future bridging-helper
    refinement may be warranted — but NOT in this PR).
    """

def _equivalence_can_rescue(slug: str, records: list[RouteEquivalenceRecord]) -> bool:
    """Return True iff `slug` (already lowercased, hyphen-form) appears
    as a case-insensitive substring of any record's `from_route_id` OR
    `to_route_id`. Empty `slug` returns False (defensive)."""

def _compute_recall_via_equivalence(
    *,
    breakdown: list[dict[str, Any]],   # the new harness field per row
    records: list[RouteEquivalenceRecord],
) -> dict[str, Any] | None:
    """Per-scenario recall_via_equivalence.

    Returns None when the scenario has zero misses
    (i.e. all `breakdown[i].matched is True`). This is the
    DENOMINATOR-ZERO CONTRACT: never 0.0, never 1.0, never an empty dict.

    Otherwise returns:
        {
            "missed_substrings":         [str, ...],   # sorted, deduped
            "rescued_substrings":        [str, ...],   # subset of missed
            "still_missing_substrings":  [str, ...],   # missed - rescued
            "missed_count":              int,
            "rescued_count":             int,
            "recall":                    float,        # rescued / missed, 4 decimal places
        }
    """
```

### 6.2 Harness row field (exact shape)

In `breadcrumb_query_run.py`, immediately after `row = grade_natural_scenario(...)` (around line 1121) and **before** any of the existing `row["..."] = ...` enrichment lines, add:

```python
exp_subs = list(scen.get("expect_route_substrings") or [])
hits_for_breakdown = bundle.hits  # use whatever is already in scope; same hits hits_cover_expected_routes uses
row["expected_route_substring_breakdown"] = [
    {
        "substring": sub,
        "matched": hits_cover_expected_routes(
            hits_for_breakdown,
            [sub],
            location_hierarchy_equivalences=scen.get("location_hierarchy_equivalences"),
        ),
    }
    for sub in exp_subs
]
```

(Adapt the `hits` reference to whatever variable currently holds the hit list at that line — the implementer MUST verify by reading lines 1100–1150 first; do not paste this snippet blindly.)

**Field is always present**, even when `expect_route_substrings` is empty (`[]`). Order matches the gold's order. **Per-substring `matched` MUST agree with `missing_expected_route_hit`** in `violations`: if any breakdown row has `matched: false`, the scenario MUST also list `missing_expected_route_hit` in violations (and vice versa). The §7 #2 test asserts this consistency.

### 6.3 Cohort summary changes

In `cohort_baseline_run.py`:

1. **Schema constant.** Replace:
   ```python
   COHORT_SUMMARY_SCHEMA_V1 = "dmb_breadcrumb_query_cohort_summary_v1"
   ```
   with:
   ```python
   COHORT_SUMMARY_SCHEMA_V2 = "dmb_breadcrumb_query_cohort_summary_v2"
   ```
   (Drop the V1 constant entirely; only V2 is supported going forward.)

2. **Default baseline path.** Replace `_DEFAULT_BASELINE`'s `_v1.json` with `_v2.json`.

3. **Load records once.** In `_write_mode`, after the existing `route_paths = [...]` line, add:
   ```python
   route_equivalence_records = load_route_equivalence_shadow_records(route_paths)
   ```
   and pass `route_equivalence_records=route_equivalence_records` into `build_cohort_summary`.

4. **`build_cohort_summary` signature change** (additive kwarg):
   ```python
   def build_cohort_summary(
       *,
       manifest: dict[str, Any],
       per_scenario_reports: list[dict[str, Any]],
       workspace_root: Path,
       manifest_path: Path,
       route_equivalence_records: list[RouteEquivalenceRecord],   # NEW
   ) -> dict[str, Any]:
   ```

5. **Per-scenario recall.** Inside the existing `for scenario, report in zip(...)` loop, after computing `pass_count`, derive:
   ```python
   per_question_breakdowns = [row["expected_route_substring_breakdown"] for row in results]
   # Flatten to a single per-scenario breakdown by collecting all (substring, matched) pairs.
   # A substring is considered "matched at the scenario level" iff it was matched on AT LEAST ONE question
   # that listed it; "missed at scenario level" iff it appears in some question and was matched in NONE.
   # Deduplicate substrings per scenario; preserve first-seen order from the gold.
   scenario_recall = _compute_recall_via_equivalence(
       breakdown=_aggregate_question_breakdowns(per_question_breakdowns),
       records=route_equivalence_records,
   )
   ```
   Add `"recall_via_equivalence": scenario_recall` to each `scenarios_out[i]` dict.

6. **Aggregate field.** In the top-level summary, add a new key after `aggregate`:
   ```python
   "recall_via_equivalence_aggregate": {
       "scenarios_with_misses": int,        # count of scenarios where recall is not None
       "min": float | null,                 # null when scenarios_with_misses == 0
       "mean": float | null,
       "max": float | null,
   }
   ```
   When `scenarios_with_misses == 0` (the expected case for this cohort), all three of `min/mean/max` are JSON `null`. Do **not** emit `0.0` placeholders.

7. **Schema field.** Bump the `"schema"` value in the returned dict to `COHORT_SUMMARY_SCHEMA_V2`.

### 6.4 Curated field exclusions (carry forward from PR #6)

The new `recall_via_equivalence` field is the **only** schema addition. The curated summary continues to exclude:

- `records_source` (CWD-dependent absolute path)
- `aggregate_llm_cost_usd`, `llm_model`, per-row `llm_*` (LLM not used in `--retrieval-only`)
- `scenario_estimated_cost_usd`
- `shadow_token_resolution_build`
- per-row `hit_count`, `top_hit`, `retrieved_context`, `retrieval_hit_context_full` (volatile / large)
- per-row `expected_route_substring_breakdown` itself (it is **input** to the metric, **not** part of the curated summary — only the derived `recall_via_equivalence` lands in the summary)

The §7 #4 test asserts these exclusions still hold.

### 6.5 File rename (delete `_v1.json`, add `_v2.json`)

The old PR #6 baseline file is **deleted** in this PR. The new `_v2.json` is **generated** via `cohort_baseline_run --write` on a clean checkout (after the code changes), then committed verbatim. The `--check` mode then enforces byte-identity against `_v2.json`. **Do not** keep both files; the `_v1.json` schema is no longer supported.

## §7 Verification commands (run all; paste output verbatim into PR description)

> **Numbering note:** each command below is one shell invocation, numbered 1:1 with prose comments to keep `scripts/review_external_pr.py fetch --extract-rubric` and §9 rubric pairing aligned. Adding multi-line scripts here is forbidden — split into separately numbered commands instead. (Reason: prose vs parser drift, see `Backlog.md` 2026-05-10.)

```bash
# 1. Existing producer-side regression. Untouched by this PR.
uv run pytest tests/lexicon_phase_b/ -q

# 2. Existing harness-boundary regression. Test count grows from 11 to 12 with the new
#    test asserting expected_route_substring_breakdown ↔ violations consistency.
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q

# 3. Existing producer-side determinism. Untouched by this PR.
uv run python scripts/build_route_equivalence_manifests.py --check

# 4. Cohort-runner unit + curation tests. Test count grows from 9 to 13.
uv run pytest tests/test_cohort_baseline_run.py -q

# 5. Harness-boundary CWD-invariance test, run isolated to confirm the rerolled
#    baseline byte-identity holds across operator CWDs.
uv run pytest tests/test_cohort_baseline_run.py::test_cohort_baseline_run_write_is_byte_identical_across_cwds -q

# 6. Frozen baseline regression: --check exits 0 on the committed _v2.json.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check

# 7. Smoke: generate the cohort baseline to /tmp and confirm it is byte-identical to the committed file.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --write --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json --baseline /tmp/pr7-cohort-summary-smoke.json

# 8. Schema + shape probe. The expected output is the v2 schema string, the new
#    aggregate field, and recall_via_equivalence == null for every scenario in the cohort
#    (denominator-zero contract on the C1S1-C1S3 cohort).
python -c "import json; s=json.load(open('/tmp/pr7-cohort-summary-smoke.json')); print('schema:', s['schema']); print('cohort_id:', s['cohort_id']); print('scenarios:', [x['scenario_id'] for x in s['scenarios']]); print('recall_per_scenario:', [x['recall_via_equivalence'] for x in s['scenarios']]); print('recall_aggregate:', s['recall_via_equivalence_aggregate']); print('aggregate:', s['aggregate'])"

# 9. Byte-identity vs committed baseline.
diff -u /tmp/pr7-cohort-summary-smoke.json evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json && echo "BYTE-IDENTICAL"

# 10. v1 baseline is removed; ls returns 1 (no such file).
test ! -f evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json && echo "v1 deleted"

# 11. No canvas perturbation.
git status --short canvases/
```

## §8 Reporting contract (paste into PR body when opening)

Two sections, both required:

1. **§7 verification.** Paste each command's tail (`pytest -q` summary line is enough; for the diff and `python -c` commands paste full stdout). The §7 #8 output MUST show `schema: dmb_breadcrumb_query_cohort_summary_v2`, all `recall_per_scenario` entries `None`, and `recall_aggregate` with `scenarios_with_misses: 0` and three `null`s.
2. **`git diff --stat origin/main...HEAD` filtered to §4 paths only.** Six paths exactly. If your diff has more or different paths, you have scope creep — revert and re-verify.

## §9 Acceptance rubric (every bullet pairs with a §7 command)

The reviewer will accept ONLY if every bullet below is true. Each bullet names the §7 command that verifies it. **Behavioral guarantees are paired with commands at the boundary the guarantee describes** (`.cursor/rules/external-agent-pr-loop.mdc` invariant #2 — tightened by PR #4 round 1, PR #5, and PR #6).

- [ ] **`expected_route_substring_breakdown` is always present on every per-row report** (empty list `[]` when the gold has no `expect_route_substrings`); per-row `matched` booleans agree with `missing_expected_route_hit` in the existing `violations` list — verified by §7 #2 (`test_expected_route_substring_breakdown_is_consistent_with_violations`). Mismatch is a hard fail.
- [ ] **Cohort summary schema is `dmb_breadcrumb_query_cohort_summary_v2`** and the v1 baseline file is deleted — verified by §7 #6, §7 #8, and §7 #10. The schema string is the version contract; the filename `cohort_baseline_c1s1_to_c1s3_v2.json` mirrors it exactly.
- [ ] **`recall_via_equivalence` is JSON `null` for every scenario in this cohort** (denominator-zero contract: every scenario has `all_ok: true`, so misses == 0) — verified by §7 #8 (`recall_per_scenario: [None, None, None]`). Never `0.0`, never an empty dict, never an omitted key.
- [ ] **`recall_via_equivalence_aggregate` reports `scenarios_with_misses: 0` and `min/mean/max: null`** — verified by §7 #8. Do not emit `0.0` placeholders for the three statistics; `null` is the contract for "no signal." This is the load-bearing leading-indicator readout for L2 on this cohort.
- [ ] **Bridging helpers (`_normalize_substring_to_slug`, `_equivalence_can_rescue`, `_compute_recall_via_equivalence`) are unit-tested with hand-crafted fixtures** that include: (a) a scenario with zero misses → returns `None`; (b) a scenario with one miss rescued by a `from_route_id` substring match → recall `1.0`; (c) a scenario with one miss NOT rescued → recall `0.0`; (d) the slug-tail / underscore-to-hyphen normalization on `"Campaign 1/PCs/karsemine"` → `"karsemine"` — verified by §7 #4.
- [ ] **Cohort summary is byte-identical across operator CWDs** — verified at the **harness boundary** by `test_cohort_baseline_run_write_is_byte_identical_across_cwds` (§7 #5; subprocess from `_REPO_ROOT` and `_REPO_ROOT / "tests"`, full curated JSON byte-equality asserted against the rerolled v2 baseline). The PR #5 + PR #6 CWD-invariance contracts are preserved against the new schema; this carries forward, not redefines.
- [ ] **`--check` mode exits 0 against the committed v2 baseline on a clean checkout** — verified by §7 #6. Exit 1 (MISMATCH) or 2 (error) is a hard fail.
- [ ] **Frozen baseline is byte-identical to a fresh `--write` smoke output** (§7 #7 and §7 #9). The committed file is the canonical generator output, not a hand-edited derivative.
- [ ] **Curated summary continues to exclude all CWD-dependent and run-volatile fields** — no `records_source`, no LLM cost fields, no per-row `hit_count`/`top_hit`/`retrieved_context`/`retrieval_hit_context_full`, and importantly **no per-row `expected_route_substring_breakdown`** in the curated summary (that field is **input** to the metric, not curated output) — verified by §7 #4 via `test_build_cohort_summary_curates_expected_shape`.
- [ ] **`shadow_route_equivalences` payload remains uniform within the cohort and lifted to scenario level** (PR #6's contract). The new `recall_via_equivalence` field does not perturb this — verified by §7 #4 (existing `test_build_cohort_summary_rejects_inconsistent_shadow_payload` continues to pass).
- [ ] **`breadcrumb_query_run.py` change is purely additive** — the new row field is the only diff in that file (modulo whitespace). Every other field in every other row is byte-identical to PR #6's harness behavior. Existing PR #4 + PR #5 harness-boundary tests pass without modification (§7 #2 count is **exactly 12** — adding a 13th there would be scope creep into PR #4/#5's surface). Producer-side files unchanged: §7 #1 still **22 passed**, §7 #3 still `OK`.
- [ ] **Anti-oracle rule (`.cursor/rules/anti-oracle-leakage.mdc`):** `expected_route_substring_breakdown` and `recall_via_equivalence` are **diagnostic fields on the benchmarking-call output only.** They MUST NOT be plumbed back into retrieval, ranking, or the legacy lexical-seed path as a signal — verified by inspection (no edits to `session_memory_query.py`, the retrieval/ranking blocks of `breadcrumb_query_run.py`, or `breadcrumb_query_grader.py`).
- [ ] **No canvas perturbation** — `git status --short canvases/` is empty after a `--write` run (§7 #11). The `--skip-*-canvas-refresh` flags are passed for every scenario (carried forward from PR #6's runner).
- [ ] **Cost is `$0`** — no LLM calls; `--retrieval-only` is mandatory; the cohort summary's `llm_enabled: False` and the absence of `aggregate_llm_cost_usd` prove this.
- [ ] **No files outside §4 are touched** — verified by `git diff --stat origin/main...HEAD` filtered to §4 (must be exactly six paths: 4 modified, 1 added, 1 deleted).

## §10 Naming + numbering hard rules

- **Filename of new files:**
  - Baseline: `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` (note: the **scope id** stays `c1s1_to_c1s3`; only the **schema version** segment of the filename bumps `_v1` → `_v2`).
  - **No new manifest.** The cohort manifest at `cohorts/c1s1_to_c1s3_v1.json` is unchanged.
- **Test names (new tests):**
  - `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py::test_expected_route_substring_breakdown_is_consistent_with_violations`
  - `tests/test_cohort_baseline_run.py::test_normalize_substring_to_slug_examples`
  - `tests/test_cohort_baseline_run.py::test_equivalence_can_rescue_positive_and_negative`
  - `tests/test_cohort_baseline_run.py::test_compute_recall_via_equivalence_denominator_zero_returns_none`
  - `tests/test_cohort_baseline_run.py::test_compute_recall_via_equivalence_rescued_and_unrescued`
  - (rename existing CWD-invariance test's baseline path argument; **don't** rename the test itself — the function name is part of the rubric carry-forward).
- **GitHub PR number:** when this is dispatched, GitHub will assign **#7**. The PLAN currently uses "PR #7" in narrative for the producer-side `manifest_hash` lane (a different slice). Post-merge atomic doc-sync MUST reconcile by either (a) renaming PLAN-narrative "PR 6.5" → "PR 7" and bumping producer-side from "PR #7" → "PR #8", or (b) keeping the GitHub number distinct from PLAN narrative names and stating that explicitly. **Decision: option (a) — straight renumber.** Don't carry the divergent naming forward.
- **Schema string:** exactly `dmb_breadcrumb_query_cohort_summary_v2`. No suffix. No date. No campaign id.
- **Field names:** exactly `expected_route_substring_breakdown`, `recall_via_equivalence`, `recall_via_equivalence_aggregate`. No camelCase. No alternate spellings.

---

**End of handoff.** Dispatcher: paste this entire document (§1–§10) as the worker's prompt; do not summarize.
