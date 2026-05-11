---
# Optional workflow contract: literal markdown the worker pastes into the
# GitHub PR description. Dispatcher fills once; reviewers and parallel
# agents see one stable shape without inferring sections from free-form §2 prose.
pr_body_template: |
  ## Summary

  Ship a `cohort_baseline_run.py` CLI that drives `breadcrumb_query_run --retrieval-only` against a committed cohort manifest (C1S1 + C1S2 + C1S3, all `longmont-c1`), emits a curated byte-stable cohort summary, commits one frozen baseline, and exposes a `--check` regression mode mirroring `scripts/build_route_equivalence_manifests.py --check`. This freezes the **pre-plan retrieval baseline** for the A/B Benchmarking Sprint (PLAN § *A/B Benchmarking Sprint (post-PR #5)*, level L1).

  ## Verification (verbatim §7)

  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat origin/main...HEAD` (§4 paths only)

  ```text
  {{TODO}}
  ```

  ## What stayed unchanged

  {{TODO: one paragraph — `breadcrumb_query_run.py` and `route_equivalence_shadow.py` untouched; producer-side artifacts untouched; PR #4 + PR #5 invariants still hold; legacy retrieval/grading unchanged.}}
---

> **COMPLETED — 2026-05-11T01:49:53Z.** Shipped via [PR #6](https://github.com/Drakosfire/DungeonMindBuddy/pull/6) (`main` merge commit `9af4741a635125d3403d66a9f266564f25bad746`). Single round of review (PR head `06280c87`); APPROVE demoted to `COMMENTED` verdict banner under self-review fallback (`pullrequestreview-4260316552`). Diff held to exactly the §4 allowlist (four additive paths). Delivers `cohort_baseline_run.py`, `cohorts/c1s1_to_c1s3_v1.json`, frozen `artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json`, and `tests/test_cohort_baseline_run.py` (harness-boundary CWD invariance on full curated JSON). §7 all green; `--write` smoke BYTE-IDENTICAL vs committed baseline; `canvases/` clean; cost `$0`. Post-merge doc-sync: `PLAN-split-corpus-retrieval-to-autonomous-demo.md` v13, `CHECKLIST-dynamic-lexical-retrieval-rollout.md` (header / Reanchor / PR #6 evidence / session log). `external_pull_requests` gains `github-pr-6` with three NEW `rubric_when_we_judge` bullets. **Archived for historical reference; do not re-dispatch.**

# HANDOFF — Cohort baseline runner: frozen pre-plan retrieval baseline for C1S1 + C1S2 + C1S3

**Created:** 2026-05-10 (UTC).
**Status:** COMPLETED — see banner above. (Was: ACTIVE — dispatch this to one external/Codex subagent. **One PR.** Do not split into multiple PRs.)
**Parent agent:** Cursor agent; dispatcher is responsible for the post-merge doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, milestone progress **M2 in_progress · M3 in_progress**). This handoff opens the **A/B Benchmarking Sprint (post-PR #5)** workstream — specifically **L1: pre-plan baseline frozen**. The byte-stability contract is unblocked by **PR #5** (`40be747a`) which made `shadow_route_equivalences.source_paths` workspace-relative.

---

## §1 Mission

Ship a cohort-level harness `cohort_baseline_run.py` that runs `breadcrumb_query_run --retrieval-only --route-equivalence-jsonl …` against the committed C1S1 + C1S2 + C1S3 scenarios (all `longmont-c1`), aggregates a **curated byte-stable cohort summary** under a fixed schema, commits one frozen **pre-plan baseline** under `artifacts/baselines/`, and exposes a `--check` regression mode that exits non-zero on byte-level drift. No retriever, grader, prompt, gold, or `breadcrumb_query_run.py` changes — purely additive.

## §2 Why this slice (context for the subagent)

- **PR #5** (`main` merge commit `40be747a87d0eecb4dc1c865f236f3728cf1d4d4`, 2026-05-10T21:09Z) made `shadow_route_equivalences.source_paths` workspace-relative POSIX strings rendered at the harness boundary, with a CWD-invariance test (`test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant`). PR #5's `judgment_record.notes` named **this** slice (cohort baseline) as the immediate next deliverable — it is the byte-stability **consumer** of PR #5's contract.
- **Phase setting.** Today's retrieval algorithm in `breadcrumb_query_run.py` / `session_memory_query.py` is the same one that existed before this PLAN started. PRs #2–#5 added schema, committed JSONL artifacts, a CLI flag, the shadow consumer, and provenance hardening — all **upstream** of retrieval. So the cohort baseline produced here IS literally the **pre-plan retrieval baseline**, frozen as an artifact, against the existing question gold. The A/B Benchmarking Sprint defined in PLAN § *A/B Benchmarking Sprint (post-PR #5)* uses this baseline as the L1 anchor for every later comparison.
- **Why a cohort runner instead of a 3-shell-for-loop.** Three reasons: (a) the cohort summary needs a **curated** schema that excludes CWD-dependent and run-volatile fields from the per-scenario report (e.g. absolute `records_source` / `gold` paths), so the regression contract is meaningful; (b) the cohort manifest gives the slice a single source-of-truth file naming exactly which (gold, records, equivalence-jsonl) tuples constitute the **pre-plan baseline cohort**, so future cohort additions (C1S13, `natural_v1`) become a new manifest + new baseline and never silently mutate this one; (c) `--check` enforces that the contract is regression-tested, mirroring the proven `scripts/build_route_equivalence_manifests.py --check` UX from PR #3.
- **Open scope question (resolved for PR 6).** The PLAN's open question — should the first cohort include `c1s13_v1` and `natural_v1`, or scope tightly to C1S1-C1S3 — is resolved **tight** for this slice. Adding the wider cohort is a follow-up: a new manifest `cohorts/c1s1_c1s3_c1s13_natural_v1.json` + new baseline file. **Do not** include those scenarios in this slice's manifest; do not reference them in this slice's tests.
- **Scope honesty — what this slice does NOT do:**
  - No new metric (recall-via-equivalence comes in PR 6.5 / extension — separate slice).
  - No retriever rewiring (Phase C **exit** / true A/B is PR 7-or-9 — separate slice).
  - No producer-side `manifest_hash` (sibling lane — separate PR).
  - No grader change, no prompt change, no gold edit, no canvas refresh.
  - No new fields added to `breadcrumb_query_run.py`'s per-scenario report. The cohort runner consumes the existing report shape and curates from it.
  - No LLM calls of any kind (`--retrieval-only` is mandatory in this cohort runner; cost should be `$0`).

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — the §4 allowlist / §5 denylist / §7 verification contract, and the **"test the boundary that owns the rubric"** invariant (PR #5's new bullet) that this PR will be reviewed against.
2. **`Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`** § *A/B Benchmarking Sprint (post-PR #5)* — the framing this slice instantiates. Read at minimum the "Three comparison-fidelity levels mapped to PRs" table and the "PR 6 — cohort baseline runner" bullet.
3. **`evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`** — read **only** these line ranges, not the whole 1400-line file:
   - **lines 655–710** — argparse for `--records-jsonl`, `--gold`, `--retrieval-only`, `--output`. Your subprocess invocations will set exactly these.
   - **lines 825–837** — argparse for `--route-equivalence-jsonl` (repeatable). Your subprocess invocations will pass each manifest path with one flag occurrence.
   - **lines 1065–1078** — load + resolve route-equivalence paths.
   - **lines 1167–1179** — per-scenario emission of `shadow_route_equivalences` (and the error branch you must NOT break).
   - **lines 1208–1247** — the per-scenario report assembly. Note: `report["records_source"]` and `report["gold"]` are **absolute** strings (CWD-dependent). Your curated cohort summary must **not** propagate these as-is; render them as workspace-relative POSIX strings (mirror PR #5's helper pattern).
4. **`evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py`** (whole file — 56 lines) — the canonical pattern for `_workspace_relative_posix(path, workspace_root)`. **Re-implement this helper inside `cohort_baseline_run.py`** (do not import from `route_equivalence_shadow.py`; that module's import surface is consumer-side, this module is its sibling — keep them independently testable). Identical semantics; identical fallback (`path.name` for paths outside `workspace_root`).
5. **`scripts/build_route_equivalence_manifests.py`** (whole file — 80 lines) — the canonical pattern for `--check` mode (build into a tempdir, `read_bytes()` compare, exit 1 on mismatch, exit 0 on OK, exit 2 on error). Mirror this UX exactly so the regression contract is uniform across the suite.
6. **`tests/test_breadcrumb_query_run_lexicon_records_jsonl.py`** — read in particular:
   - lines **181–245** (`_run_breadcrumb_query_run_subprocess`, the existing subprocess helper) — your cohort runner harness-boundary test will invoke `cohort_baseline_run.py` via a similar subprocess pattern.
   - lines **263–298** (`test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant`) — the canonical CWD-invariance pattern (subprocess from `_REPO_ROOT` and from `_REPO_ROOT / "tests"`, payload byte-equality assertion). Your new cohort harness-boundary test mirrors this shape with the cohort summary instead of one shadow payload.
7. **`evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s1_v1.json`**, **`…c1s2_v1.json`**, **`…c1s3_v1.json`** — read the frontmatter (top ~17 lines) of each to confirm `campaign_id: longmont-c1` and the `default_query_spec.session_min/max` are 1/1, 2/2, 3/3 respectively. Do **not** edit these files.
8. **`evals/sentence_routing_retrieval_falsification/artifacts/last_session1_c1_breadcrumb_records.jsonl`**, **`…/c1s2_norm_smoke.records_meta.jsonl`**, **`…/c1s3_norm_smoke.records_meta.jsonl`** — confirm the three records JSONL files exist and share schema `dmb_session_memory_record_v1`. The `meta` suffix on c1s2/c1s3 is historical naming; they ARE the records, not separate metadata. Do **not** regenerate them.
9. **`evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl`** and **`…_c2_v1.jsonl`** — the route-equivalence manifests your cohort runner will pass to every scenario (both manifests, in this exact order). Producer-side; do **not** regenerate.
10. **`src/bootstrap_env.py`** lines **1–15** — the canonical `_REPO_ROOT = Path(__file__).resolve().parents[1]` pattern. `cohort_baseline_run.py` lives at `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py`, so its repo root is `Path(__file__).resolve().parents[2]` — same offset as `breadcrumb_query_run.py`'s `_HARNESS_WORKSPACE_ROOT`.
11. **`tests/conftest.py`** — confirm session-autouse `load_dungeonmindbuddy_dotenv()` is wired (live tests don't need exported keys; see `.cursor/rules/dungeonbuddy-environment.mdc`). You should not need to touch this; just verify it's present. Note: `--retrieval-only` mode does not call OpenAI, so this test does not actually need API keys; the smoke check is for parity with the harness.
12. **`Docs/Plans/archive/2026-05-10/handoffs/HANDOFF-route-equivalence-shadow-source-paths-workspace-relative.md`** — the PR #5 handoff. Read §6.1 for the `_workspace_relative_posix` helper shape and §6.3.C for the harness-boundary CWD-invariance pattern. **Do not edit it.**

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| **Create** | `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | The cohort runner CLI. Loads a cohort manifest, invokes `breadcrumb_query_run --retrieval-only --route-equivalence-jsonl …` per scenario via `subprocess.run` (or in-process), curates a byte-stable cohort summary, supports `--write` and `--check` modes mirroring `scripts/build_route_equivalence_manifests.py`. |
| **Create** | `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` | The cohort manifest. Schema `dmb_breadcrumb_query_cohort_manifest_v1`. Lists exactly three scenarios (C1S1, C1S2, C1S3) with the (gold, records_jsonl) tuples, plus the two `route_equivalence_jsonl` paths. **Workspace-relative POSIX paths only**, no absolute paths. |
| **Create** | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json` | The frozen pre-plan retrieval baseline. Schema `dmb_breadcrumb_query_cohort_summary_v1`. Generated by `cohort_baseline_run.py --write` and committed verbatim. **Path is OUTSIDE `runs/` (which is gitignored — see `evals/sentence_routing_retrieval_falsification/artifacts/.gitignore`); the new `baselines/` directory MUST NOT be added to `.gitignore`.** |
| **Create** | `tests/test_cohort_baseline_run.py` | Unit tests for the manifest loader, the curated-summary builder, and the `_workspace_relative_posix` helper. Plus **one harness-boundary CWD-invariance test** that runs `cohort_baseline_run.py` via subprocess from `_REPO_ROOT` and from `_REPO_ROOT / "tests"` and asserts the resulting cohort summary is byte-identical (mirrors `test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant`). |

> Your `git diff --stat origin/main...HEAD` MUST be expressible from these **four** entries and **only** these four entries. Anything else is scope creep — see §5.

## §5 Files explicitly OUT OF SCOPE (denylist + concrete collision risks)

You will be tempted to "fix while I'm here." Resist. Each item below has a concrete risk attached.

| Path | Why out of scope | Concrete collision/regression risk |
|---|---|---|
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | The per-scenario engine. This slice consumes its existing report shape; do **not** add fields, flags, or normalization here. | Adding "convenient" fields to make cohort aggregation easier breaks the byte-stability contract for downstream consumers (PR 6.5 recall metric, future Phase C exit slice). The cohort runner does the curation; that is the contract. |
| `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py` | PR #5's just-shipped surface. | Touching it puts you on the wrong lane; any helper your cohort runner needs must live in `cohort_baseline_run.py`. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_grader.py` | Grader. | Any change makes this a grading-change PR. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_canvas_payload.py`, `…breadcrumb_query_rank_report.py`, `…c1s*_benchmark_canvas_emit.py` | Canvas / report consumers. | Out of scope; canvases haven't read the cohort summary yet (Phase 4 work). Canvas refresh discipline (`.cursor/rules/breadcrumb-query-canvas-sync.mdc`, `…stage-b-bucket-canvas-sync.mdc`) does **not** require a refresh for this slice — no benchmark numbers shown on existing canvases will change. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s*_v1.json` | Gold files. | **Hard rule: no gold edits in a baseline-capture slice.** The whole point of capturing a baseline is to fix the rubric in place. Gold tuning belongs in a separate, explicitly-justified slice (see `.cursor/rules/gold-realignment-vs-deflation.mdc`). |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json`, `…natural_v1.json` | Out-of-cohort gold (deferred to a follow-up cohort manifest). | Adding either to this slice's manifest silently widens the L1 baseline scope. Do **not** include them; do **not** reference them in the manifest, the runner default, or any test. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c*_v1.jsonl` | Canonical committed producer-side artifacts. | **Do not regenerate.** Producer-side; outside this slice's contract. |
| `evals/sentence_routing_retrieval_falsification/artifacts/.gitignore` | Adds `runs/` to gitignore. | **Hard rule: do NOT add `baselines/` here.** The frozen baseline must be committed; if you accidentally add `baselines/` to `.gitignore`, the baseline file will be untracked and the regression contract becomes empty. |
| `evals/sentence_routing_retrieval_falsification/artifacts/last_session1_c1_breadcrumb_records.jsonl`, `…c1s2_norm_smoke.records_meta.jsonl`, `…c1s3_norm_smoke.records_meta.jsonl` | The committed records JSONL files this cohort consumes. | **Do not regenerate.** The baseline is byte-stable only if the input records are byte-stable. If the records are stale or wrong, that is a separate slice with its own gold/records discussion. |
| `src/lexicon_phase_b/**` | Producer-side schemas + loaders + manifest builder. | Touching anything here puts you on the manifest-hash sibling lane (PR 7), which is a separate PR. |
| `src/agent/session_memory_query.py` | Planner-runtime path. | Phase C **exit** wiring; not this slice. |
| `tests/lexicon_phase_b/**` | Lexicon-only tests. | Any change here implies a producer-side scope shift. The harness-boundary test for this slice lives in `tests/test_cohort_baseline_run.py`. |
| `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | The PR #4/#5 harness-boundary suite. | This slice does **not** modify any existing tests there. Your new CWD-invariance test for the cohort runner lives in the new `tests/test_cohort_baseline_run.py` file, not bolted onto the existing module. |
| `tests/test_token_resolution_*.py`, `tests/test_benchmark_lexicon_seeds.py` | Unrelated existing suites. | **Hard collision risk.** PR #1 was closed precisely because it touched this namespace. Do not create new tests at any `tests/test_token_resolution_*` basename. |
| `scripts/build_route_equivalence_manifests.py` | Producer-side CLI; the `--check` UX you are mirroring. | Mirror the **shape** by hand-writing your own `_check_mode` in `cohort_baseline_run.py`; do **not** import from this script and do **not** factor a shared `_check_mode` helper into a new module. The two `--check` modes share UX but operate on different artifact families and must remain independently testable. |
| `evals/sentence_routing_retrieval_falsification/README.md` | Existing prose still describes the harness correctly. | If a doc tweak feels unavoidable, surface it in the PR description and let the dispatcher decide. Default answer: no — the README update is a parent-side post-merge concern. |
| `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`, `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` | Plan/checklist sync is the parent agent's atomic post-merge job. | If the subagent edits these, the parent will revert and re-brief. |
| `Docs/Plans/HANDOFF-*.md` other than this one, `Docs/Plans/archive/**` | Each handoff names exactly one slice; archived material is historical. | Editing other handoffs muddles the active-vs-archived boundary. |
| Any `corpus/**` | Corpus is GM-private. | See `.cursor/rules/corpus-pii-and-llm-payloads.mdc`. |
| Any `.cursor/rules/*.mdc`, `.cursor/skills/**` | Rules and skills are parent-managed. | Out of scope. |
| Any `canvases/**` | Canvas review surfaces. | Phase 4 work; no benchmark numbers on existing canvases change with this slice. |

**Naming hard rules:**
- The new directory `evals/sentence_routing_retrieval_falsification/cohorts/` must be created with the manifest file. Do **not** add a `__init__.py`, README, or any other file inside.
- The new directory `evals/sentence_routing_retrieval_falsification/artifacts/baselines/` must be created with the baseline file only. Do **not** add a `.gitkeep`, `.gitignore`, or any other file.
- Test file at the `tests/` root is `tests/test_cohort_baseline_run.py` (not `tests/test_cohort_baseline.py`, not under `tests/lexicon_phase_b/`).

## §6 Implementation contract

### 6.1 Cohort manifest schema

Schema id: `dmb_breadcrumb_query_cohort_manifest_v1`. JSON shape:

```json
{
  "schema": "dmb_breadcrumb_query_cohort_manifest_v1",
  "cohort_id": "c1s1_to_c1s3_v1",
  "notes": "Pre-plan retrieval baseline cohort: C1S1 + C1S2 + C1S3 (all longmont-c1, retrieval-only). PR 6 / A/B Benchmarking Sprint L1 anchor. Adding scenarios = new manifest + new baseline file; do not mutate this one.",
  "campaign_id": "longmont-c1",
  "route_equivalence_jsonl": [
    "evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl",
    "evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl"
  ],
  "scenarios": [
    {
      "scenario_id": "c1s1",
      "gold": "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s1_v1.json",
      "records_jsonl": "evals/sentence_routing_retrieval_falsification/artifacts/last_session1_c1_breadcrumb_records.jsonl",
      "session_number": 1,
      "notes": "C1 Session 1 — roster/identity-bundle coverage; 23 records."
    },
    {
      "scenario_id": "c1s2",
      "gold": "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s2_v1.json",
      "records_jsonl": "evals/sentence_routing_retrieval_falsification/artifacts/c1s2_norm_smoke.records_meta.jsonl",
      "session_number": 2,
      "notes": "C1 Session 2 — clean control lane; 13 records."
    },
    {
      "scenario_id": "c1s3",
      "gold": "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s3_v1.json",
      "records_jsonl": "evals/sentence_routing_retrieval_falsification/artifacts/c1s3_norm_smoke.records_meta.jsonl",
      "session_number": 3,
      "notes": "C1 Session 3 — location-entity hierarchy pressure; 61 records."
    }
  ]
}
```

Determinism / ordering rules:
- Top-level keys in the order shown: `schema`, `cohort_id`, `notes`, `campaign_id`, `route_equivalence_jsonl`, `scenarios`.
- `route_equivalence_jsonl` order MUST be C1 then C2 (matches the `expected_source_paths` in the existing PR #5 test).
- `scenarios` order MUST be C1S1, C1S2, C1S3 (numeric session order).
- All paths workspace-relative POSIX. **No absolute paths**, **no `~`**, **no globs**.
- Pretty-print with `indent=2`, `ensure_ascii=False`, trailing newline. Mirror the formatting of existing committed JSON gold under `gold/` for byte-stability.

### 6.2 `cohort_baseline_run.py` — argparse + modes

CLI shape (mirroring `scripts/build_route_equivalence_manifests.py`):

```python
# evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

_HARNESS_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MANIFEST = (
    Path("evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json")
)
_DEFAULT_BASELINE = (
    Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json")
)

COHORT_MANIFEST_SCHEMA_V1 = "dmb_breadcrumb_query_cohort_manifest_v1"
COHORT_SUMMARY_SCHEMA_V1 = "dmb_breadcrumb_query_cohort_summary_v1"


def _workspace_relative_posix(path: Path, workspace_root: Path) -> str:
    """Mirrors `route_equivalence_shadow._workspace_relative_posix` (PR #5)."""
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.name


def load_cohort_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load + minimally validate. Raises ValueError on schema mismatch or path issues."""
    ...


def run_one_scenario(
    *,
    scenario: dict[str, Any],
    route_equivalence_jsonl: Sequence[Path],
    workspace_root: Path,
    per_scenario_out: Path,
) -> dict[str, Any]:
    """Invoke `breadcrumb_query_run --retrieval-only` via subprocess; return parsed report."""
    ...


def build_cohort_summary(
    *,
    manifest: dict[str, Any],
    per_scenario_reports: list[dict[str, Any]],
    workspace_root: Path,
) -> dict[str, Any]:
    """Curate the byte-stable cohort summary. See §6.3 for exact shape."""
    ...


def _write_mode(
    *,
    manifest_path: Path,
    baseline_out: Path,
    per_scenario_out_dir: Path,
    workspace_root: Path,
) -> int:
    ...


def _check_mode(
    *,
    manifest_path: Path,
    baseline_path: Path,
    workspace_root: Path,
) -> int:
    """Build into a tempdir; byte-compare against the committed baseline."""
    ...


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Cohort baseline runner: pre-plan retrieval baseline for the A/B "
            "Benchmarking Sprint. See PLAN-split-corpus-retrieval-to-autonomous-demo.md "
            "section 'A/B Benchmarking Sprint (post-PR #5)'."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true",
                     help="Run the cohort and write the baseline (default).")
    mode.add_argument("--check", action="store_true",
                     help="Run the cohort into a tempdir and byte-compare against --baseline.")
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--baseline", type=Path, default=_DEFAULT_BASELINE)
    parser.add_argument("--per-scenario-out-dir", type=Path, default=None,
                        help=(
                            "Where to write per-scenario reports (forensic detail). "
                            "Default: artifacts/runs/<date>/cohort_<cohort_id>/. "
                            "Files written here are gitignored via the existing artifacts/.gitignore."
                        ))
    args = parser.parse_args()

    try:
        if args.check:
            return _check_mode(
                manifest_path=args.manifest,
                baseline_path=args.baseline,
                workspace_root=_HARNESS_WORKSPACE_ROOT,
            )
        per_scenario_dir = args.per_scenario_out_dir or _default_per_scenario_dir(args.manifest)
        return _write_mode(
            manifest_path=args.manifest,
            baseline_out=args.baseline,
            per_scenario_out_dir=per_scenario_dir,
            workspace_root=_HARNESS_WORKSPACE_ROOT,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

Subprocess invocation per scenario:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --records-jsonl <records_jsonl> \
  --gold <gold> \
  --retrieval-only \
  --output <per_scenario_out>/<scenario_id>_retrieval_baseline.json \
  --route-equivalence-jsonl <route_equivalence_jsonl[0]> \
  --route-equivalence-jsonl <route_equivalence_jsonl[1]> \
  --skip-c1s1-canvas-refresh --skip-c1s2-canvas-refresh --skip-c1s3-canvas-refresh
```

The `--skip-*-canvas-refresh` flags MUST be passed for every scenario regardless of which scenario is running, because the natural-gold runner's canvas-auto-refresh hooks will otherwise mutate `canvases/` files and corrupt your `git diff --stat`. Confirm this empirically: a `--write` run on a clean checkout must leave `git status canvases/` empty.

Subprocess CWD: the runner SHOULD set `cwd=workspace_root` for every subprocess so the relative paths in the manifest resolve consistently. Use `subprocess.run([...], capture_output=True, text=True, cwd=str(workspace_root), check=True)`. On non-zero exit code, print stderr and raise `RuntimeError` (caught by `main()`'s `OSError, ValueError` handler — wrap as `ValueError` with the scenario_id named in the message).

Determinism / ordering rules:
- Iterate scenarios in manifest order (no sort; the manifest IS the contract).
- Resolve manifest-relative paths against `workspace_root`, not the CWD.
- Per-scenario output filename: `<scenario_id>_retrieval_baseline.json`. No timestamps in the filename. (Timestamps would mean re-runs produce different files; the cohort runner overwrites in place.)
- The default `per_scenario_out_dir` lives under `artifacts/runs/<date>/cohort_<cohort_id>/` — under the existing `runs/` gitignore. The committed baseline lives under `artifacts/baselines/`, which is NOT gitignored.

### 6.3 Curated cohort summary schema

Schema id: `dmb_breadcrumb_query_cohort_summary_v1`. The cohort summary is the **frozen baseline** — every byte must be deterministic across operator CWDs, machines, and re-runs (within `--retrieval-only` mode). Top-level shape:

```python
def build_cohort_summary(...) -> dict[str, Any]:
    return {
        "schema": COHORT_SUMMARY_SCHEMA_V1,
        "cohort_id": manifest["cohort_id"],
        "manifest": _workspace_relative_posix(manifest_path, workspace_root),
        "campaign_id": manifest["campaign_id"],
        "route_equivalence_jsonl": list(manifest["route_equivalence_jsonl"]),  # already POSIX in manifest
        "retrieval_only": True,
        "llm_enabled": False,
        "scenarios": [
            {
                "scenario_id": s["scenario_id"],
                "gold": s["gold"],
                "records_jsonl": s["records_jsonl"],
                "session_number": s["session_number"],
                "gold_schema": <from per-scenario report>,
                "all_ok": <from per-scenario report>,
                "scenario_count": len(<per-scenario report>["results"]),
                "pass_count": sum(1 for r in <results> if r["ok"]),
                "fail_count": sum(1 for r in <results> if not r["ok"]),
                "violations": [
                    {
                        "scenario_id": r["scenario_id"],
                        "ok": r["ok"],
                        "violations": sorted(r["violations"]),  # sort for byte-stability
                    }
                    for r in <results>
                ],
                "shadow_route_equivalences": <results>[0]["shadow_route_equivalences"],
                # ^ Same payload across all rows in a single-campaign cohort; confirm + lift to scenario level.
            }
            for ... in zip(manifest["scenarios"], per_scenario_reports)
        ],
        "aggregate": {
            "total_questions": <sum of scenario_count>,
            "total_pass": <sum of pass_count>,
            "total_fail": <sum of fail_count>,
            "all_scenarios_all_ok": <bool: every scenario's all_ok is True>,
            # NOT: pass_rate as a float. Floats are platform-dependent edge-cases under JSON; report as ints.
        },
    }
```

Hard contract on the curated shape:

- **Excluded fields (from per-scenario reports) — must NOT appear in the summary:**
  - `records_source` (absolute path; CWD-dependent — even in subprocess with `cwd=workspace_root`, this is the resolved absolute path because `breadcrumb_query_run.py:1209` does `records_path.resolve()`).
  - `gold` (top-level absolute path field on the per-scenario report — same reason).
  - `aggregate_llm_cost_usd` (always 0.0 in `--retrieval-only`; redundant given `llm_enabled: False`).
  - `llm_model` (a string set unconditionally; varies if env vars or model policy shifts).
  - `scenario_estimated_cost_usd` (only set if `> 0`; absent in `--retrieval-only`).
  - `shadow_token_resolution_build` (legacy lexicon shadow surface; covered by other tests; out of scope here).
  - Any per-scenario row field not explicitly listed above (`hit_count`, `top_hit`, `retrieved_context`, `retrieval_hit_context_full`, etc.). The summary captures only the regression-bearing minimum.
- **Included fields — explicitly listed.** No others, even if they look harmless.
- `violations` is `sorted(...)` per row to defeat any nondeterministic ordering inside the per-scenario grader (none observed today, but the sort is cheap insurance).
- `shadow_route_equivalences` is taken from `results[0]` after asserting (in `build_cohort_summary`) that all rows in the same scenario have the same shadow payload. If they differ, raise `ValueError` — this would indicate a regression in PR #4/#5 invariants.
- JSON serialization: `indent=2`, `ensure_ascii=False`, `sort_keys=False` (key order is part of the contract above), trailing newline.

### 6.4 `_check_mode` UX

Mirror `scripts/build_route_equivalence_manifests.py:_check_mode` exactly (lines 44–59):

```python
def _check_mode(*, manifest_path, baseline_path, workspace_root) -> int:
    if not baseline_path.exists():
        print(f"MISSING {_workspace_relative_posix(baseline_path, workspace_root)}", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        generated = tmp_dir / baseline_path.name
        per_scenario_tmp = tmp_dir / "per_scenario"
        per_scenario_tmp.mkdir()
        # Build into the tempdir; do not write to baseline_path.
        _write_one(
            manifest_path=manifest_path,
            baseline_out=generated,
            per_scenario_out_dir=per_scenario_tmp,
            workspace_root=workspace_root,
        )
        if generated.read_bytes() != baseline_path.read_bytes():
            print(f"MISMATCH {_workspace_relative_posix(baseline_path, workspace_root)}")
            return 1
        print(f"OK {_workspace_relative_posix(baseline_path, workspace_root)}")
        return 0
```

Exit codes: `0` = OK; `1` = MISMATCH or MISSING; `2` = error (raised in `main()`'s except branch).

### 6.5 `tests/test_cohort_baseline_run.py`

Three layers:

**A. Unit tests (no subprocess) for the helpers and the curated-summary builder.**
- `test_workspace_relative_posix_in_repo` — happy path; returns `"evals/.../foo.json"`.
- `test_workspace_relative_posix_outside_repo` — fallback; returns `path.name`.
- `test_load_cohort_manifest_validates_schema` — wrong schema id raises `ValueError`.
- `test_load_cohort_manifest_validates_paths` — manifest with a missing gold path raises `ValueError`.
- `test_build_cohort_summary_curates_expected_shape` — feed in two synthetic per-scenario reports, assert the summary contains exactly the included fields and none of the excluded ones.
- `test_build_cohort_summary_rejects_inconsistent_shadow_payload` — two synthetic results with differing `shadow_route_equivalences` raises `ValueError`.
- `test_build_cohort_summary_sorts_violations` — input violations in random order, output deterministically sorted.

**B. End-to-end `--write` smoke (subprocess; uses real fixtures) for one scenario only.**
- `test_cohort_baseline_run_write_produces_summary_with_committed_manifest` — invoke `cohort_baseline_run.py --write --manifest <real manifest> --baseline <tmp_path/...>` from `cwd=_REPO_ROOT`. Assert exit code 0; assert the produced file exists; assert it parses as JSON with `schema == COHORT_SUMMARY_SCHEMA_V1`; assert `len(summary["scenarios"]) == 3`. Do **not** assert against the committed baseline byte-for-byte here — that's test C.

**C. Harness-boundary CWD-invariance test (THE rubric-bearing test).**
- `test_cohort_baseline_run_write_is_byte_identical_across_cwds` — mirror `test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant` (PR #5). Run `cohort_baseline_run.py --write --baseline <tmp_path/from_root.json>` once from `cwd=_REPO_ROOT` and once from `cwd=_REPO_ROOT / "tests"`. Assert both exit 0 and the two output files are byte-identical via `read_bytes()`. This is the test that owns the rubric bullet "cohort summary is byte-identical across operator CWDs."

Skeleton for test C:

```python
def test_cohort_baseline_run_write_is_byte_identical_across_cwds(tmp_path: Path) -> None:
    """The frozen baseline must be byte-identical regardless of operator CWD.

    Owns rubric bullet: 'Cohort summary byte-identity across CWDs is verified at
    the harness boundary by spawning subprocesses from at least two different CWDs
    and asserting full-file byte-equality.' (PR 6 / PR #5 invariant carried forward.)
    """
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    out_a = tmp_path / "from_repo_root.json"
    out_b = tmp_path / "from_subdir.json"
    cmd_base = [
        "uv", "run", "python", "-m",
        "evals.sentence_routing_retrieval_falsification.cohort_baseline_run",
        "--write",
        "--manifest", "evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json",
    ]
    run_a = subprocess.run(
        cmd_base + ["--baseline", str(out_a)],
        capture_output=True, text=True, cwd=str(_REPO_ROOT),
    )
    cwd_subdir = _REPO_ROOT / "tests"
    assert cwd_subdir.is_dir()
    run_b = subprocess.run(
        cmd_base + ["--baseline", str(out_b)],
        capture_output=True, text=True, cwd=str(cwd_subdir),
    )
    assert run_a.returncode == 0, run_a.stderr
    assert run_b.returncode == 0, run_b.stderr
    assert out_a.read_bytes() == out_b.read_bytes(), (
        "cohort summary must be byte-identical across operator CWDs"
    )
```

Place `_REPO_ROOT = Path(__file__).resolve().parents[1]` at the module top, mirroring `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py:21`.

**Total expected new test count: 9** (test A: 7, test B: 1, test C: 1). The pytest collection step in §7 verifies this.

## §7 Verification commands

The worker MUST run **every** command and paste the output into the PR body. The reviewer reruns each. **Every behavioral guarantee in §9 below must be exercised by at least one command here, at the boundary the guarantee describes** (`.cursor/rules/external-agent-pr-loop.mdc` invariant #2).

> **Numbering note (avoids a recurring drift trap).** The numbered comments below correspond **1:1** to the commands `scripts/review_external_pr.py fetch --extract-rubric` will report under `verification_commands[]`. There are **exactly 10** commands; do not bundle multiple commands under one numbered comment, even when they're logically grouped (e.g. "sanity tests"). This convention exists because handoff-prose vs parser command counts have drifted before — see `Backlog.md` (2026-05-10, "HANDOFF §0 expected §7 command counts vs parser").

```bash
# 1. Sanity: producer-side surfaces unchanged.
uv run pytest tests/lexicon_phase_b/ -q

# 2. Sanity: prior-PR harness-boundary suite unchanged.
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q

# 3. Producer-side regression gate (committed JSONL must remain byte-stable).
uv run python scripts/build_route_equivalence_manifests.py --check

# 4. Full new test module (unit + smoke + harness-boundary).
uv run pytest tests/test_cohort_baseline_run.py -q

# 5. Targeted: the rubric-bearing harness-boundary CWD-invariance test in isolation.
uv run pytest tests/test_cohort_baseline_run.py::test_cohort_baseline_run_write_is_byte_identical_across_cwds -q

# 6. The cohort runner --check mode against the committed baseline (THE end-to-end regression contract).
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check

# 7. Smoke: --write into a tempdir from the repo root.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --write --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json --baseline /tmp/pr6-cohort-summary-smoke.json

# 8. Eyeball the smoke output's top-level shape.
python -c "import json; s=json.load(open('/tmp/pr6-cohort-summary-smoke.json')); print('schema:', s['schema']); print('cohort_id:', s['cohort_id']); print('scenarios:', [x['scenario_id'] for x in s['scenarios']]); print('aggregate:', s['aggregate'])"

# 9. Confirm the committed baseline matches the smoke output (the --check ground truth, in shell form).
diff -u /tmp/pr6-cohort-summary-smoke.json evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json && echo "BYTE-IDENTICAL"

# 10. Confirm canvases were not perturbed (the --skip-*-canvas-refresh flags work).
git status --short canvases/
```

Expected outputs:
- §7 #1: `22 passed` (lexicon_phase_b — unchanged from PR #5).
- §7 #2: `11 passed` (existing breadcrumb_query_run boundary suite — unchanged from PR #5).
- §7 #3: `OK` for both `route_equivalence_longmont_c1_v1.jsonl` and `route_equivalence_longmont_c2_v1.jsonl`.
- §7 #4: `9 passed` (the new test module).
- §7 #5: `1 passed`.
- §7 #6: `OK evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json`. Exit code 0.
- §7 #7: exits 0; writes `/tmp/pr6-cohort-summary-smoke.json`.
- §7 #8: prints `schema: dmb_breadcrumb_query_cohort_summary_v1`, `cohort_id: c1s1_to_c1s3_v1`, `scenarios: ['c1s1', 'c1s2', 'c1s3']`, and the aggregate counts.
- §7 #9: prints `BYTE-IDENTICAL` (and `diff` exits 0).
- §7 #10: empty output (no canvases touched).

## §8 Reporting contract

In the PR body the worker MUST include:

1. **`git diff --stat origin/main...HEAD` filtered to the §4 allowlist paths only.** Four files. Anything else is scope creep.
2. **Verbatim §7 output for all 10 commands** — pass/fail counts (`22 passed` lexicon_phase_b, `11 passed` existing breadcrumb_query_run boundary suite, `9 passed` new module, `1 passed` targeted CWD-invariance), the `--check` mode `OK …` line, and the smoke step's `schema` / `cohort_id` / `scenarios` / `aggregate` printout. On any failure: paste the last 30 lines of the failing command's stderr.
3. **One-paragraph "what stayed unchanged"** — call out at least: (a) `breadcrumb_query_run.py`, `route_equivalence_shadow.py`, `route_equivalence_loader.py`, and the producer-side artifacts are byte-identical to current `main`; (b) PR #4 + PR #5 harness-boundary tests still pass without modification (`tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q -> 11 passed`); (c) `--check` on producer-side manifests is `OK`; (d) `git status --short canvases/` is empty (no canvas perturbation).

## §9 Acceptance rubric

The reviewer will accept ONLY if every bullet below is true. Each bullet names the §7 command that verifies it. **Behavioral guarantees are paired with commands at the boundary the guarantee describes** (`.cursor/rules/external-agent-pr-loop.mdc` invariant #2 — tightened by PR #4 round 1 and PR #5).

- [ ] **Cohort manifest is committed at `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` with schema `dmb_breadcrumb_query_cohort_manifest_v1`** and lists exactly C1S1, C1S2, C1S3 (3 scenarios) — verified by §7 #8 (`scenarios: ['c1s1', 'c1s2', 'c1s3']`).
- [ ] **Frozen baseline is committed at `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v1.json` with schema `dmb_breadcrumb_query_cohort_summary_v1`** — verified by `git ls-files` showing the path and by §7 #9 (`diff -u … && echo "BYTE-IDENTICAL"`).
- [ ] **`--check` mode exits 0 against the committed baseline on a clean checkout** — verified by §7 #6. Exit 1 (MISMATCH) or 2 (error) is a hard fail.
- [ ] **Cohort summary is byte-identical across operator CWDs** — verified at the **harness boundary** by `test_cohort_baseline_run_write_is_byte_identical_across_cwds` (§7 #5; subprocess run from `_REPO_ROOT` and from `_REPO_ROOT / "tests"`, full-file byte-equality asserted). Not just verified by a unit-level call to `build_cohort_summary`. Mirrors PR #5's CWD-invariance contract; this is the new bullet's natural application.
- [ ] **Curated summary excludes CWD-dependent and run-volatile fields.** No `records_source`, no top-level `gold` absolute path, no `aggregate_llm_cost_usd`, no `llm_model`, no `scenario_estimated_cost_usd`, no `shadow_token_resolution_build`, no per-row `hit_count` / `top_hit` / `retrieved_context` / `retrieval_hit_context_full` — verified by `test_build_cohort_summary_curates_expected_shape` (§7 #4).
- [ ] **`shadow_route_equivalences` payloads are uniform within a single-campaign cohort and lifted to scenario level** — verified by `test_build_cohort_summary_rejects_inconsistent_shadow_payload` (§7 #4). If a future cross-campaign cohort needs per-row payloads, that's a new schema version, not a quiet shape change.
- [ ] **`breadcrumb_query_run.py`, `route_equivalence_shadow.py`, and producer-side surfaces are byte-identical to current `main`** — verified by §7 #1 + #2 (existing test counts unchanged) and §7 #3 (`--check` OK on both manifests).
- [ ] **Existing PR #4 + PR #5 harness-boundary tests pass without modification** — `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q -> 11 passed` (§7 #2). Test count must be **exactly 11** — adding a 12th there is scope creep into the prior PR's surface.
- [ ] **No canvas perturbation.** `git status --short canvases/` is empty after a `--write` run (§7 #10). The `--skip-*-canvas-refresh` flags are passed for every scenario.
- [ ] **Cost is `$0`.** No LLM calls; `--retrieval-only` is mandatory; the cohort summary's `llm_enabled: False` and the absence of `aggregate_llm_cost_usd` proves this.
- [ ] **No files outside §4 are touched.** Verified by `git diff --stat origin/main...HEAD` filtered to §4 (must be exactly four paths).

> **Reviewer reminder:** if a bullet describes a behavioral guarantee at a particular boundary (harness, dispatcher, writer), the §7 command that verifies it MUST exercise it at that boundary. Loader-side or unit-side coverage is necessary but not sufficient. This rubric was tightened by PR #4 round 1 and PR #5; do not regress.

## §10 Out-of-band notes (optional)

- **A/B sprint context (for the worker, not the rubric).** This slice is L1 of the three-level A/B Benchmarking Sprint defined in `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` § *A/B Benchmarking Sprint (post-PR #5)*. L2 (recall-via-equivalence metric, PR 6.5 or extension) and L3 (true A/B at Phase C exit) build on this baseline. Do **not** speculatively design for L2/L3 here; their handoffs come after this lands.
- **Why workspace-relative POSIX paths matter for the manifest itself.** The cohort manifest names files; if those names contain `/home/<user>/...`, the manifest is per-machine and the cohort isn't a real contract. The cohort runner reads them relative to `_HARNESS_WORKSPACE_ROOT`, so they must be workspace-relative. This is the same byte-stability discipline PR #5 applied to `shadow_route_equivalences.source_paths`, lifted up one level.
- **Why no `manifest_hash` on the cohort summary.** The producer-side `manifest_hash` work (PR 7) is a sibling lane. When it lands, the cohort summary will gain a `manifest_hash` field naturally (alongside `shadow_route_equivalences`); this slice deliberately does not pre-shape the schema for that. The schema is `_v1`; a future schema is `_v2` and gets its own baseline file. **Do not** speculatively add a `manifest_hash` field here.
- **Why no PASS/FAIL pass-rate floats in the summary.** Floats serialize differently across platforms and Python versions in subtle edge cases (`0.5333…` vs `0.53333333333333333`). Integers are byte-stable. The reviewer or downstream consumer can compute pass-rate as `total_pass / total_questions` if they want a float; the regression contract stays in integers.
- **Why no `scripts/build_cohort_baselines.py` mirror.** `scripts/build_route_equivalence_manifests.py` exists at `scripts/` because it builds a producer-side artifact consumed by the harness. The cohort baseline is itself a harness artifact (it sits under `evals/.../artifacts/baselines/`), so its builder lives under the harness too. Do **not** create a `scripts/` mirror — that splits the contract across two places.
- **If the worker hits a sandbox / `gh pr create` issue,** post the PR-body markdown back to the dispatcher and the dispatcher will open the PR by hand. Do **not** widen scope to "fix the sandbox while I'm here." See `.cursor/rules/external-agent-pr-loop.mdc` and the PR #5 self-review fallback (APPROVE demoted to `COMMENTED` is the common path on this repo).
- **Self-review fallback is normal here.** When the dispatcher posts `--review-md` an APPROVE/REQUEST_CHANGES on a PR you authored, GitHub returns 422 and the script demotes to `event: COMMENT` with a verdict banner. Treat this as the common path, not the exception.
