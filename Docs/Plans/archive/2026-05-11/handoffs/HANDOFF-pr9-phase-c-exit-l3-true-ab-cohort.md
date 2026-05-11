---
# Optional workflow contract: literal markdown the worker pastes into the
# GitHub PR description. Dispatcher fills once; reviewers and parallel
# agents see one stable shape without inferring sections from free-form §2 prose.
pr_body_template: |
  ## Summary

  Wire route-equivalence records into the breadcrumb ranking path behind a `--use-route-equivalence-for-ranking` flag on `breadcrumb_query_run`; extend `cohort_baseline_run` with `--mode both` (true A/B delta) and fix hardcoded canvas `--skip-*` flags to derive from `scenario_id` in the manifest. Legacy default path byte-identical to current `main`. Closes the PLAN Phase C exit (L3) unchecked item.

  ## Verification (verbatim §7)

  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat origin/main...HEAD` (§4 paths only)

  ```text
  {{TODO}}
  ```

  ## What stayed unchanged

  {{TODO: one paragraph — default `breadcrumb_query_run` without `--use-route-equivalence-for-ranking` flag byte-identical to current main (modulo absent shadow_route_equivalences field when --route-equivalence-jsonl is also absent); default `cohort_baseline_run` (no --mode flag) byte-identical to v2 baseline; gold untouched; `route_equivalence_shadow.py` untouched; producer JSONL untouched; lexicon_phase_b tests unchanged at 25 passed; v2 frozen baseline `cohort_baseline_c1s1_to_c1s3_v2.json` untouched.}}
---

> **MERGED — 2026-05-11T04:13:54Z** — merge commit `976512e94df62e42a27d1a41aa876a2561a0cb70`; PR head `c89ba7f4ce7f8dfa74fef0e1e8d7d9215180b692`. Atomic doc-sync landed PLAN **v16** + CHECKLIST + this archive row. **Follow-ups:** handoff §7 #6 argv shape (`--write --baseline <path>`); multi-`scenario_id` skip-flag test; delta two-CWD harness; wider cohort + alias-saturation before default promotion. **Tight-cohort L3 readout:** baseline `all_ok` 3/3 vs with-equivalence 1/3 (c1s1 + c1s3 regress).

# HANDOFF — PR #9: Phase C exit — L3 true A/B cohort (ranking-input wiring + delta runner)

**Created:** 2026-05-10 (UTC).
**Status:** COMPLETED — merged to `main`; archived 2026-05-11 (UTC). Do not re-dispatch.
**Parent agent:** Cursor agent; post-merge atomic doc-sync completed (`PLAN-split-corpus-retrieval-to-autonomous-demo.md` v16, `CHECKLIST-dynamic-lexical-retrieval-rollout.md`, archive index).
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` **v16** (`active_phase: B`, M2 `in_progress`, M3 `complete`). **A/B Benchmarking Sprint — L3** checklist row marked `[x]` on super-plan.

**Re-anchor note (read before touching any code):** HEAD on `main` at authoring time is `02bbcc0cdf263dd863d0fbab4f0361583f06f5b1` (doc-sync after PR #8 merge `adeb060911be35f4f477cb15eaf701ab7d409fbf`). PLAN v15 frontmatter matches. PR #7 + PR #8 `rubric_when_we_judge` carry two explicit prerequisites now discharged in this slice: (1) canvas `--skip-*` argv derivation from `scenario_id` before widening the cohort manifest; (2) sensitivity-test discipline (separate input mutation). Both land in this PR.

**Explicit fork (read before scope creep):** This PR is the **retrieval-wiring + delta-runner** slice only. The **wider cohort** (records + manifest for `c1s13_v1` / `natural_v1`) is a **separate follow-up** handoff. PR #9 does NOT widen the committed cohort manifest `cohorts/c1s1_to_c1s3_v1.json`. No `session_memory_query.py` changes are required — `query_session_memory_candidate` already accepts `query_token_aliases` as its augmentation surface; the Phase C exit wiring happens at the harness level in `breadcrumb_query_run.py` (see §6.1). No producer JSONL changes. No gold edits.

---

## §1 Mission

Wire route-equivalence records as additive `query_token_aliases` input into the `breadcrumb_query_run` retrieval path behind a new `--use-route-equivalence-for-ranking` flag, add `--mode both` (true A/B delta) to `cohort_baseline_run`, fix the hardcoded canvas `--skip-*` flag triple to derive from `scenario_id`, commit the initial L3 delta artifact, and prove default (no-flag) runs are byte-identical to the current `main` — **without** touching gold, `route_equivalence_shadow.py`, producer JSONL, or the existing v2 frozen baseline.

## §2 Why this slice (context for the subagent)

- **PRs #2–#8** built the Phase B artifacts and the L1/L2 diagnostic layer without flipping the retriever. Every PR through #8 left `session_memory_query.py`'s `query_session_memory_candidate` as the authoritative scoring entry point with `query_token_aliases` already wired — the extension point is ready; it just needs an upstream caller to supply equivalence-derived aliases.
- **PR #7** landed the L2 recall-via-equivalence diagnostic (`recall_via_equivalence: null` on tight C1S1–C1S3 — expected, denominator zero). **PR #8** added producer provenance (`route_equivalence_manifest_hash`, `schema_version 0.3.0`). Neither flipped the retriever.
- **L3** is the first PR that actually changes retrieval behavior (gated behind `--use-route-equivalence-for-ranking`). The comparison contract: same gold, same cohort, two modes (legacy seeds baseline vs equivalence-augmented), committed delta artifact that is reproducible and byte-stable.
- **PR #7 + PR #8 `rubric_when_we_judge`** carry two carry-forward prerequisites that land in this PR: (a) `cohort_baseline_run.run_one_scenario` must NOT hardcode `--skip-c1s1-canvas-refresh` / `--skip-c2s*`; derive from `scenario_id` / manifest so argv stays valid when the manifest expands. (b) Sensitivity-test discipline. Closing both here unblocks the wider-cohort PR that follows.
- **What this slice does NOT do:** no `session_memory_query.py` internal changes (the existing `query_token_aliases` parameter already handles augmentation — see §6.1); no `route_equivalence_shadow.py` changes; no producer JSONL regeneration; no gold edits; no wider cohort manifest expansion; no canvas or LLM pipeline changes.

## §3 Authoritative inputs (read these in this order, before writing any code)

| Path | Why |
|---|---|
| `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` | PLAN v15 — Phase C exit description (`## A/B Benchmarking Sprint`, L3 row, Phase 5 primary files), re-sequencing decision, Phase C checklist items. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Target for new flag; read §§ near line 1066–1100 (route_equivalence loading + shadow wiring) and line 1084 (`natural_retrieval_bundle(records=records, scenario=scen)` call) to see the injection point. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_grader.py` | `natural_retrieval_bundle` (line ~645) and `query_session_memory_for_scenario` (line ~552): read both to understand how `query_token_aliases` is currently plumbed from scenario → `query_session_memory_candidate`. **Do not modify** unless §6.1 approach requires it; prefer the scenario-copy approach first. |
| `src/agent/session_memory_query.py` | `query_session_memory_candidate` (line ~807): `query_token_aliases` parameter is already the augmentation surface. **Do not add new parameters.** Read `_tokenize_query` and `_score_record` to understand how aliases expand token matching. |
| `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | `run_one_scenario` (line 55): hardcoded `--skip-c1s1-canvas-refresh` / `--skip-c1s2-canvas-refresh` / `--skip-c1s3-canvas-refresh` at line 65 — this is the carry-forward to fix. Read the manifest JSON shape (`cohorts/c1s1_to_c1s3_v1.json`) for the `scenario_id` values. |
| `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` | Committed cohort manifest (`dmb_breadcrumb_query_cohort_manifest_v1`); read `scenario_id` values (e.g. `"c1s1"`, `"c1s2"`, `"c1s3"`) to derive the `--skip-<scenario_id>-canvas-refresh` pattern. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` | Existing frozen v2 baseline (`dmb_breadcrumb_query_cohort_summary_v2`) — **must not change**; `--check` must still pass after this PR. |
| `src/lexicon_phase_b/schemas.py` | `RouteEquivalenceRecord` field names — `from_route_id`, `to_route_id` — needed to derive alias tokens in §6.1. |
| `Docs/Plans/archive/2026-05-11/handoffs/HANDOFF-pr8-producer-route-equivalence-manifest-hash.md` | Prior HANDOFF for structural density reference; §4 allowlist table / §5 denylist table / §7 verbatim-output discipline. |
| `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | Existing harness-boundary tests (12 at HEAD); new test in this PR extends the file — read test structure before adding. |
| `tests/test_cohort_baseline_run.py` | Existing cohort suite (13 at HEAD); new tests in this PR extend the file. |

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Add `--use-route-equivalence-for-ranking` boolean flag (default: `False`); when set AND `route_equivalence_records` successfully loaded, build equivalence-derived alias tokens (see §6.1) and call `natural_retrieval_bundle` with an augmented scenario copy whose `query_spec.query_token_aliases` includes those tokens (merged with any existing aliases); legacy default path byte-identical. |
| Modify | `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | (a) Fix `run_one_scenario`: replace hardcoded `--skip-c1s1-canvas-refresh` / `--skip-c1s2-canvas-refresh` / `--skip-c1s3-canvas-refresh` with `--skip-<scenario_id>-canvas-refresh` derived from manifest row `scenario_id`; (b) add `--mode` CLI option (`baseline` | `with-equivalence` | `both`; default `baseline`); `with-equivalence` adds `--use-route-equivalence-for-ranking` to subprocess argv; `both` runs each scenario twice and emits delta summary; (c) add `--write-delta` / `--check-delta` for the new delta artifact (see §6.2). |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json` | L3 delta summary committed by `--mode both --write-delta` smoke (schema `dmb_breadcrumb_query_cohort_l3_delta_v1`; see §6.2). |
| Modify | `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | Add `test_use_route_equivalence_for_ranking_flag_is_additive_only_at_harness_boundary` (subprocess: run `breadcrumb_query_run` with valid `--route-equivalence-jsonl` twice — with and without `--use-route-equivalence-for-ranking` — assert all non-equivalence-ranking fields byte-identical when flag absent vs absent; assert `query_token_aliases` in trace is non-empty and route-slug tokens appear when flag is set). |
| Modify | `tests/test_cohort_baseline_run.py` | Add tests for: `--mode both` delta output has correct schema and required fields; `--check-delta` exits 0 against committed delta; `run_one_scenario` skip-flag derivation from `scenario_id` (unit-level: assert `--skip-c1s1-canvas-refresh` in argv when `scenario_id == "c1s1"`). |

> **Expected diff stat shape: 5 paths.** If `git diff --stat origin/main...HEAD` shows anything else, **revert** the extra paths — scope creep. If `breadcrumb_query_grader.py` needs a minor signature change to thread `query_token_aliases` through `natural_retrieval_bundle`, STOP and ask the parent agent before adding it to the diff; prefer the scenario-copy approach in §6.1 to avoid the threading.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these. Concrete collision risks named alongside the path:

| Path | Why this PR must not touch it |
|---|---|
| `src/agent/session_memory_query.py` | `query_token_aliases` is already the augmentation surface; **no new parameters needed** — see §6.1. Adding a new parameter here changes the API contract owned by the planner tool, risks breaking `tests/test_token_resolution_*.py`, and turns a 5-file PR into a 6-file one. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_grader.py` | `natural_retrieval_bundle` and `query_session_memory_for_scenario` do NOT need changes if the scenario-copy approach in §6.1 is followed. If the worker finds this is unavoidable, stop and ask the parent agent. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` | Existing frozen v2 baseline — `--check` must still pass against it; do not reroll. |
| `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` | Cohort manifest — wider cohort is a **different** follow-up handoff; do not add scenarios here. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold never edited for retrieval wiring. |
| `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py` | Shadow diagnostic stays unchanged; the shadow `shadow_route_equivalences` field continues to emit alongside the new `--use-route-equivalence-for-ranking` flag independently. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/*.jsonl` | Committed producer JSONL is input, not output, here. Do not regenerate. |
| `src/lexicon_phase_b/**` | Producer-side — untouched; this PR is purely consumer-side. |
| `corpus/**` | Read-only inputs for registry SHA hashing. |
| `src/prompts/**` | Forbidden. |
| `Docs/Plans/**` | Doc-sync is **parent post-merge**, not worker. This handoff file is also excluded — do not edit it. |
| `evals/sentence_routing_retrieval_falsification/c1s1_benchmark_canvas_emit.py`, `c1s2_benchmark_canvas_emit.py`, `c1s3_benchmark_canvas_emit.py`, `c1s13_benchmark_canvas_emit.py` | Canvas emitters are unchanged; `--skip-*-canvas-refresh` flags suppress their invocation at harness call sites, not within them. |

If the worker thinks one of these is genuinely needed, it must stop and ask in the PR description before opening the PR.

## §6 Implementation contract

### §6.1 Ranking-input wiring: scenario-copy approach (preferred — no grader changes)

`breadcrumb_query_run.py` currently calls `natural_retrieval_bundle(records=records, scenario=scen)` at line ~1084. When `--use-route-equivalence-for-ranking` is set AND `route_equivalence_records` is not `None` (loaded successfully), the worker MUST:

1. Build equivalence-derived alias tokens from the loaded `RouteEquivalenceRecord` list. The minimal approach:
   ```python
   import re as _re

   def _slug_from_route(route_id: str) -> str:
       """Extract the trailing path component and normalise to a lexical token."""
       part = route_id.rstrip("/").split("/")[-1].strip()
       # Convert underscores/dashes to spaces so the tokenizer can split sub-terms
       return _re.sub(r"[_-]+", " ", part).strip().lower()

   def _build_equivalence_aliases(records: list[RouteEquivalenceRecord]) -> list[str]:
       """Derive route-slug tokens from from_route_id + to_route_id of all loaded records."""
       seen: set[str] = set()
       aliases: list[str] = []
       for rec in records:
           for route_id in (rec.from_route_id, rec.to_route_id):
               slug = _slug_from_route(route_id)
               if slug and slug not in seen:
                   seen.add(slug)
                   aliases.append(slug)
       return aliases
   ```

2. Build an augmented scenario copy: **do NOT mutate `scen` in place**. Use a deep copy or a shallow merge of the `query_spec` subdict:
   ```python
   import copy

   extra_aliases = _build_equivalence_aliases(route_equivalence_records)
   if extra_aliases:
       scen_with_aliases = copy.deepcopy(scen)
       existing = list(scen_with_aliases.get("query_spec", {}).get("query_token_aliases") or [])
       scen_with_aliases.setdefault("query_spec", {})["query_token_aliases"] = existing + extra_aliases
       retrieval_scenario = scen_with_aliases
   else:
       retrieval_scenario = scen
   ```

3. Pass `retrieval_scenario` (not `scen`) to `natural_retrieval_bundle`. When the flag is unset, pass `scen` as before — no logic change on the default path.

4. The `shadow_route_equivalences` field continues to be built from the **unmodified** `route_equivalence_records` via `build_route_equivalence_shadow_payload` as today — no change to that code path.

5. Emit a new top-level row field `ranking_augmented_by_equivalences: bool` in the JSON output row (set `True` when the flag is set AND aliases were injected; `False` otherwise). This makes the per-scenario artifact self-describing for the delta runner.

**Key property to preserve:** when `--use-route-equivalence-for-ranking` is ABSENT (default), the retrieval call is byte-identical to the current `main` behavior. The harness-boundary test in §4 asserts this.

### §6.2 Cohort dual-mode runner and delta artifact

`cohort_baseline_run.py` gains:

**a. `--mode` option (required before §6.2b works):**

| `--mode` value | Effect |
|---|---|
| `baseline` (default) | Current behavior — runs each scenario once without `--use-route-equivalence-for-ranking`; `--write`/`--check` work against `cohort_baseline_c1s1_to_c1s3_v2.json` as before. |
| `with-equivalence` | Runs each scenario once with `--use-route-equivalence-for-ranking` appended to subprocess argv (requires `--route-equivalence-jsonl` paths from manifest). Writes to a separate path or `/tmp` unless `--write` is explicit. |
| `both` | Runs each scenario **twice** (one baseline pass, one with-equivalence pass); produces per-scenario delta rows and a cohort-level delta summary. |

**b. Canvas `--skip-*` derivation fix (carry-forward from PR #7 + PR #8 rubric):**

Replace the hardcoded triple in `run_one_scenario`:
```python
# BEFORE (hardcoded — denylist for wider manifest):
cmd.extend(["--skip-c1s1-canvas-refresh", "--skip-c1s2-canvas-refresh", "--skip-c1s3-canvas-refresh"])

# AFTER (derived from scenario_id in manifest row):
skip_flag = f"--skip-{scenario['scenario_id']}-canvas-refresh"
cmd.append(skip_flag)
```

Validation: assert `breadcrumb_query_run` accepts `--skip-<scenario_id>-canvas-refresh` as a valid flag (it already does — check the `--skip-*` argparse definition; if the dynamic flag name is not accepted, derive from the manifest `skip_canvas_refresh_flags` field or add the dynamic pattern to argparse). If the existing argparse only accepts a whitelist of skip flags, add the pattern `--skip-<scenario_id>-canvas-refresh` to that whitelist (still in `breadcrumb_query_run.py`, which IS in the §4 allowlist).

**c. `--write-delta` / `--check-delta` and delta artifact schema:**

Delta artifact path: `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json`

Schema `dmb_breadcrumb_query_cohort_l3_delta_v1`:
```json
{
  "schema_id": "dmb_breadcrumb_query_cohort_l3_delta_v1",
  "cohort_manifest": "<path to cohorts/c1s1_to_c1s3_v1.json>",
  "baseline_schema": "dmb_breadcrumb_query_cohort_summary_v2",
  "route_equivalence_jsonl": ["<workspace-relative POSIX path>", ...],
  "generated_at": "<ISO-8601 UTC>",
  "scenarios": [
    {
      "scenario_id": "c1s1",
      "baseline_all_ok": true,
      "with_equivalence_all_ok": true,
      "baseline_violations": [],
      "with_equivalence_violations": [],
      "delta_violation_count": 0
    }
  ],
  "delta_summary": {
    "total_scenarios": 3,
    "scenarios_changed": 0,
    "scenarios_improved": 0,
    "scenarios_regressed": 0,
    "baseline_all_ok_count": 3,
    "with_equivalence_all_ok_count": 3
  }
}
```

- `--write-delta <path>` writes this JSON (default path: the committed path above when `--write-delta` flag used without argument, or use `--write-delta` as a no-arg flag that implies the canonical path, matching `--write` / `--check` UX).
- `--check-delta` loads the committed delta file and verifies a fresh `--mode both` write produces byte-identical output (same discipline as `--check` for v2 baseline). Use the same CWD-invariance subprocess approach as PR #5 + PR #6.
- The `generated_at` field MUST be excluded from the curated delta file (volatile); use the same curated-fields exclusion pattern as `cohort_baseline_run.py::_build_curated_summary` in PR #6/PR #7.

**d. Byte-stability contract for delta artifact:**

`--check-delta` is the regression anchor. The delta is deterministic and retrieval-only ($0 LLM cost). A harness-boundary CWD-invariance test in `tests/test_cohort_baseline_run.py` MUST spawn `cohort_baseline_run --mode both --write-delta /tmp/...` from at least two operator CWDs and assert byte-identical output (matching PR #5/PR #6 pattern).

## §7 Verification commands (run all; paste output verbatim into PR description)

> **Numbering note:** each non-comment line inside the single ```bash``` fence is **exactly one** shell invocation. Parser count must be **8** to pair with §8 / §9.

```bash
# 1. Lexicon producer regression — must remain 25 passed unchanged.
uv run pytest tests/lexicon_phase_b/ -q

# 2. Harness-boundary suite (existing 12 + new test(s) — paste "N passed" line).
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q

# 3. Cohort baseline suite (existing 13 + new test(s) — paste "N passed" line).
uv run pytest tests/test_cohort_baseline_run.py -q

# 4. Producer CLI determinism gate — must remain OK for both artifacts.
uv run python scripts/build_route_equivalence_manifests.py --check

# 5. Existing v2 cohort baseline regression — must exit 0 (default --mode baseline unchanged).
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check

# 6. Default mode byte-identity check — fresh --write must be BYTE-IDENTICAL to committed v2 baseline.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --write /tmp/pr9_baseline_check.json && diff -u evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json /tmp/pr9_baseline_check.json && echo "BYTE-IDENTICAL"

# 7. L3 delta write smoke — paste schema_id + delta_summary from output.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --mode both --write-delta /tmp/pr9_l3_delta_smoke.json && uv run python -c "import json; d=json.load(open('/tmp/pr9_l3_delta_smoke.json')); print('schema_id', d.get('schema_id')); print('total_scenarios', d['delta_summary']['total_scenarios']); print('scenarios_changed', d['delta_summary']['scenarios_changed']); print('baseline_all_ok_count', d['delta_summary']['baseline_all_ok_count']); print('with_equivalence_all_ok_count', d['delta_summary']['with_equivalence_all_ok_count'])"

# 8. --check-delta against committed delta artifact — must exit 0.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-delta
```

## §8 Reporting contract

In the PR body the worker MUST include:

1. **§7:** paste stdout/stderr tails for all **8** commands; §7 **#7** must print `schema_id dmb_breadcrumb_query_cohort_l3_delta_v1` and `total_scenarios 3`; §7 **#6** must print `BYTE-IDENTICAL`; §7 **#5** must exit 0.
2. **`git diff --stat origin/main...HEAD`** filtered to **§4 paths only** — expect **5** rows (one per allowlisted path; note the new delta JSON counts as one `create` row).
3. **One-paragraph "what stayed unchanged"** — call out: `tests/lexicon_phase_b/` at 25 passed, `cohort_baseline_c1s1_to_c1s3_v2.json` untouched, default `cohort_baseline_run` behavior byte-identical, `route_equivalence_shadow.py` untouched, gold untouched.

## §9 Acceptance rubric (each bullet pairs with §7; reviewer uses `fetch --extract-rubric`)

- [ ] **`--use-route-equivalence-for-ranking` flag absent: default `breadcrumb_query_run` output is byte-identical (modulo `shadow_route_equivalences` field) to a run without the flag** — verified by §7 **#2** `test_use_route_equivalence_for_ranking_flag_is_additive_only_at_harness_boundary` at the harness boundary (subprocess, not loader-level). **Loader-side or unit-side coverage is necessary but not sufficient — test at the harness boundary.**
- [ ] **`--use-route-equivalence-for-ranking` flag set with valid JSONL: `query_token_aliases` in output row trace is non-empty and contains at least one route-slug token derived from the loaded equivalence records** — verified by §7 **#2** new test (inspect `trace.query_token_aliases` in harness output row).
- [ ] **`ranking_augmented_by_equivalences: true` appears in output row when flag is set with valid JSONL; `false` (or absent) when flag is not set** — verified by §7 **#2** test and §7 **#7** delta artifact field values.
- [ ] **`cohort_baseline_run` default mode (no `--mode` flag): byte-identical to `--write` output against `cohort_baseline_c1s1_to_c1s3_v2.json`; `--check` exits 0** — verified by §7 **#5** + §7 **#6** (`BYTE-IDENTICAL` line).
- [ ] **Canvas `--skip-*` flag triple is derived from `scenario_id` in manifest, NOT hardcoded**: `run_one_scenario` builds `--skip-<scenario_id>-canvas-refresh` per manifest row; verified by §7 **#3** `test_run_one_scenario_skip_flag_is_derived_from_scenario_id` (unit test asserting dynamic skip flag in subprocess argv).
- [ ] **`--mode both` produces delta artifact with `schema_id: "dmb_breadcrumb_query_cohort_l3_delta_v1"` and required top-level fields (`delta_summary`, `scenarios`, `route_equivalence_jsonl`, `cohort_manifest`)** — verified by §7 **#7** (`schema_id` + `total_scenarios 3`).
- [ ] **`--check-delta` exits 0 against committed delta artifact (byte-stable)** — verified by §7 **#8**; the CWD-invariance harness-boundary test in §7 **#3** must spawn `--mode both --write-delta` from at least two operator CWDs and assert byte-identical output.
- [ ] **Lexicon producer regression: `tests/lexicon_phase_b/ -q` ≥ 25 passed unchanged** — verified by §7 **#1**.
- [ ] **Harness and cohort regression bundles: §7 #2 paste shows previous 12 tests still passing + ≥ 1 new test; §7 #3 paste shows previous 13 tests still passing + ≥ 1 new test; §7 #5 exits 0** — verified by §7 **#2** + **#3** + **#5**.
- [ ] **No §5 denylist paths appear in `git diff`** — reviewer will **REQUEST_CHANGES** if violated. Pay special attention to `session_memory_query.py`, `breadcrumb_query_grader.py`, `cohort_baseline_c1s1_to_c1s3_v2.json`, gold files, and producer JSONL.
- [ ] **Cost: $0** — no LLM calls; `--retrieval-only` cohort run + pytest only; producer CLI only.

> **Reviewer reminder (PR #4 lesson):** if a bullet describes a behavioral guarantee at the harness boundary (flag-absent byte-identity; alias-presence in trace), the §7 command that verifies it MUST exercise it at the harness boundary via subprocess — not at the scenario-builder or loader level. Round 1 misses happen when only unit-level tests cover boundary properties.

## §10 Out-of-band notes + post-merge parent duties

- **Post-merge (parent, one atomic batch, PLAN v15 → v16):**
  1. PLAN: bump `version: 15 → 16`; `last_updated_at` to UTC merge time; `changelog` prepend; `execution_state.active_phase` advances from `B` to **`C`** (Phase C exit landed); `milestone_progress.M3: in_progress → complete`; `next_gate_command` updated to include `--check-delta`; `integration_notes` prepend with merge commit; `flagged_followups` add wider-cohort canvas `--skip-*` derivation note (no longer needed for C1S1-C1S3 since this PR closes it, but wider-cohort manifest expansion still needs the pattern); prepend `github-pr-9` entry with ≥3 new `rubric_when_we_judge` bullets.
  2. CHECKLIST: `Active phase: B (with Phase C exit landed via PR #9)` → advance to `C`; Phase C exit items `- [ ]` → `- [x]`; `Next command to run` update; session log newest entry.
  3. Archive: move this file to `Docs/Plans/archive/2026-05-11/handoffs/HANDOFF-pr9-phase-c-exit-l3-true-ab-cohort.md` with completion banner.
- **PLAN `external_pull_requests[github-pr-9].rubric_when_we_judge` must include at least:**
  1. **Ranking-wiring is additive and gated:** `--use-route-equivalence-for-ranking` absent → byte-identical default; set → aliases injected via existing `query_token_aliases` path at the harness boundary; grader and session_memory_query APIs unchanged.
  2. **Delta artifact byte-stability contract:** `--check-delta` mirrors `--check` discipline (PR #3 pattern); CWD-invariance via subprocess from two operator CWDs (PR #5 + PR #6 pattern extended to delta mode).
  3. **Canvas skip derivation closes carry-forward:** `run_one_scenario` derives `--skip-<scenario_id>-canvas-refresh` from manifest; hardcoded triple never present in final diff; wider-cohort manifest expansion no longer blocked by this pattern.
  4. **(carry-forward for wider-cohort PR):** before expanding `cohorts/c1s1_to_c1s3_v1.json`, verify `--check-delta` still exits 0 and the delta artifact schema validates against the new scenario count.
- **Wider cohort (next PR):** after PR #9 merges, the wider-cohort handoff should reference the committed `cohort_l3_ab_delta_c1s1_to_c1s3_v1.json` as the L3 anchor for C1S1–C1S3; the delta for a wider cohort will be in a separate artifact file.
- **PR title suggestion:** `PR #9: Phase C exit — L3 ranking-input wiring + true A/B cohort delta`.
- **Sandbox note:** if `--mode both` subprocess calls fail with sandbox restrictions, the worker should note this and the parent will run §7 outside the sandbox.

---

**End of handoff.** Dispatcher: run `uv run python scripts/review_external_pr.py fetch 9 --handoff Docs/Plans/HANDOFF-pr9-phase-c-exit-l3-true-ab-cohort.md --extract-rubric` **after** the PR opens to confirm §4/§5/§7/§9 parse; fix table headers if parser reports `allowlist: 0` or `denylist: 0`.
