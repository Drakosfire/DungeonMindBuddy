---
pr_body_template: |
  ## Summary
  Deprecate legacy baseline as the default cohort lane and promote route-equivalence ranking as the default retrieval baseline, while preserving an explicit legacy lane for diagnostics.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

# Merge completion (Stage 4b, parent)

**COMPLETED:** 2026-05-13T03:20:11Z (merge timestamp UTC from Git merge commit metadata).

- **Merge commit:** `75996c52cb074f8c46d8e8615a422605e566c963`
- **Verified PR head:** `010898348b9905b3917f56dc6a2235c3ec119411`
- **Doc-sync:** `PLAN-split-corpus-retrieval-to-autonomous-demo.md` v26 (`github-pr-19`), `CHECKLIST-dynamic-lexical-retrieval-rollout.md` Reanchor + session log + PR #19 header line, this file under `Docs/Plans/archive/2026-05-13/handoffs/`.

---

# HANDOFF — PR #19: Deprecate Legacy Baseline, Promote Equivalence Default

**Created:** 2026-05-13 (UTC).
**Status:** COMPLETE — merged to `main`; do not re-dispatch.
**Parent agent:** Cursor agent; dispatcher is responsible for post-merge doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, `M2: in_progress`, `M3: complete`, `M4: not_started`). This handoff opened the promotion-default lane while retaining a diagnostics-only legacy comparison path.

---

## §0 Re-anchor snapshot

- Current local `main` at handoff authoring: `25d15fbbec8cd95b6425344681c3c13da3a9e70e`.
- PR #18 is merged and doc-sync is landed (`PLAN` v25 / checklist nineteenth entry).
- Most recent lane evidence:
  - Scene-beat packet lane (`/tmp` C1S13 smoke) shows packet contribution (`questions_with_packet_units_added` 21, `total_packet_units_added` 90).
  - Promotion is still blocked by PR #12 gate language (`promotion_gate_candidate.status:none_found`) under the old acceptance shape.
- This PR is the explicit policy shift slice: **promote equivalence to default retrieval baseline** and **deprecate legacy baseline to opt-in diagnostics mode**.

## §1 Mission

Make route-equivalence ranking the default cohort baseline lane, deprecate legacy baseline to explicit opt-in mode, and update C1S13 deep-dive surfaces to display promoted-vs-legacy comparison labels without breaking deterministic checks.

## §2 Why this slice (context for the subagent)

- PR #9 introduced equivalence ranking as an opt-in lane; PR #10/#11/#12/#16 added diagnostic depth around baseline vs equivalence outcomes; PR #18 improved scene/beat context contribution instrumentation.
- We now need an explicit baseline policy transition: old baseline remains available for falsification, but no longer defines the default `--write` / `--check` cohort lane.
- This slice does **not** modify corpus files, gold files, planner prompts, or route-equivalence producer manifests; it is cohort-runner policy/wiring + tests/docs/artifact refresh only.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — §4 allowlist / §5 denylist / §7 verification contract.
2. **`Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`** — `execution_state`, `external_pull_requests` (especially PR #9/#12/#16/#18), and current blocker language.
3. **`Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`** — Reanchor block + latest session log entries for PR #17/#18.
4. **`evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py`** — baseline/write/check behavior, `--mode`, `--check-delta`, `--check-question-delta`, scene-beat lane.
5. **`tests/test_cohort_baseline_run.py`** — existing boundary guarantees for baseline/check/delta/question-delta behavior.
6. **`evals/sentence_routing_retrieval_falsification/c1s13_holdout_l3_deep_dive_canvas_emit.py`** — C1S13 review payload + baseline/equivalence report handling.
7. **`tests/test_c1s13_holdout_l3_deep_dive_canvas_emit.py`** — deep-dive payload and emit contract.
8. **`evals/sentence_routing_retrieval_falsification/README.md`** — operator-facing contract for baseline/check/promotion lanes.
9. **`tests/conftest.py`** — confirm session-autouse env loading remains untouched.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Promote equivalence lane to default `--write`/`--check`; retain legacy baseline behind explicit mode/flag. |
| Modify | `tests/test_cohort_baseline_run.py` | Lock new default/legacy contracts at harness boundary. |
| Modify | `evals/sentence_routing_retrieval_falsification/c1s13_holdout_l3_deep_dive_canvas_emit.py` | Ensure deep-dive cards clearly label promoted-vs-legacy comparison after default flip. |
| Modify | `tests/test_c1s13_holdout_l3_deep_dive_canvas_emit.py` | Assert updated payload labels and backward compatibility. |
| Modify | `evals/sentence_routing_retrieval_falsification/README.md` | Document deprecation and promoted default semantics, including legacy invocation. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` | Refresh committed baseline artifact to promoted-default lane output. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json` | Refresh committed baseline artifact to promoted-default lane output. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json` | Refresh committed baseline artifact to promoted-default lane output. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_scenario_report_c1s13_v1_baseline.json` | Keep C1S13 deep-dive scenario report aligned with promoted-vs-legacy labeling contract. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_scenario_report_c1s13_v1_equivalence.json` | Keep C1S13 deep-dive scenario report aligned with promoted-vs-legacy labeling contract. |

> The agent's expected `git diff --stat` MUST be expressible from this allowlist. If a path is not in this table, the worker will be told to revert it during review.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these. Concrete collision risks named alongside the path:

| Path | Why this PR must not touch it |
|---|---|
| `Docs/Plans/**` | Parent handles plan/checklist/handoff sync post-merge; worker edits here create contradictory-state windows. |
| `corpus/**` | Baseline promotion is harness policy; corpus changes would confound retrieval-policy attribution. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold/rubric edits hide policy regressions and invalidate promotion evidence lineage. |
| `evals/sentence_routing_retrieval_falsification/cohorts/*.json` | Cohort composition is fixed for this promotion slice; changing manifests is out-of-scope gate movement. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/**` | Producer artifacts are upstream invariants; this PR is consumer policy only. |
| `src/agent/session_memory_query.py` | Retrieval core and scoring logic are not part of this baseline policy transition. |
| `canvases/**` | Runtime canvas outputs are regenerated locally; this slice updates emitter/test contracts and committed baseline artifacts only. |
| `src/prompts/**` | No planner/prompt behavior changes in this slice. |

If the worker thinks one of these is genuinely needed, it must stop and ask in the PR description before opening the PR.

## §6 Implementation contract

### 6.1 Promote default baseline lane in `cohort_baseline_run.py`

Implement these behavior changes:

```python
# Existing argparse shape may stay; contract changes are behavioral:
parser.add_argument("--mode", choices=["baseline", "with-equivalence", "both"], default="with-equivalence")

# default write/check path should execute with use_route_equivalence_for_ranking=True
# legacy baseline remains reachable only via explicit --mode baseline
```

Required invariants:

- `--write` and `--check` with no explicit `--mode` now produce/validate **promoted** (equivalence-on) cohort summaries.
- `--mode baseline` remains functional and deterministic, but is explicitly treated as **legacy** diagnostics lane.
- `--mode both`, `--write-delta`, `--check-delta`, `--write-question-delta`, and `--check-question-delta` keep working, and still compare two lanes deterministically.
- Emitted summary metadata must clearly indicate which lane produced the artifact (forensics cannot rely on filename guessing alone). Add additive metadata rather than deleting existing keys.

### 6.2 Deep-dive emitter labeling

In `c1s13_holdout_l3_deep_dive_canvas_emit.py`:

- Update payload labels so cards explicitly indicate promoted-vs-legacy comparison naming.
- Preserve existing structure required by current canvas layout/tests.
- Keep behavior backward-compatible when only baseline/equivalence report pairs are present.

### 6.3 Artifact refresh

- Regenerate the three committed `cohort_baseline_*` JSON artifacts listed in §4 using the new default promoted lane.
- Regenerate C1S13 per-scenario baseline/equivalence reports listed in §4 so emitter readouts remain coherent under new labels.
- No manual JSON hand-editing. Artifacts must be command-generated.

## §7 Verification commands

The worker must run **every** command and paste the output into the PR body. The reviewer reruns each. Every behavioral guarantee in §9 must be exercised at the boundary where that guarantee lives.

```bash
# 1) Harness-boundary tests for runner policy flip and delta behavior.
uv run pytest tests/test_cohort_baseline_run.py -q

# 2) Emitter payload + canvas deep-dive label compatibility.
uv run pytest tests/test_c1s13_holdout_l3_deep_dive_canvas_emit.py -q

# 3) Promoted-default checks (no explicit --mode) must pass against committed artifacts.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json --check

# 4) Legacy lane still works when explicitly requested (diagnostics-only contract).
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json --mode baseline --write --baseline /tmp/cohort_baseline_c1s13_legacy_smoke.json
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json --mode baseline --check --baseline /tmp/cohort_baseline_c1s13_legacy_smoke.json

# 5) Existing L3 diagnostics lane still green after promotion flip.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json --check-delta
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json
```

## §8 Reporting contract

In the PR body the worker MUST include:

1. **`git diff --stat` filtered to §4 allowlist paths only.**
2. **Verbatim §7 output** with pass/fail counts and any non-zero exit tails.
3. **One explicit table/list of lane semantics before vs after**:
   - default `--write/--check`
   - explicit `--mode baseline`
   - `--mode both` / delta surfaces
4. **One paragraph "what stayed unchanged"**:
   - no corpus/gold/prompt changes,
   - no route-equivalence producer artifact changes,
   - existing question-delta lanes still deterministic.
5. **Cost line** (retrieval-only expected): report `$0` for this verification path unless a non-zero cost is observed.

## §9 Acceptance rubric

The reviewer will accept ONLY if every bullet below is true. Each bullet is paired with the §7 command that verifies it.

- [ ] Default cohort lane is promoted equivalence (no explicit `--mode` required) and committed `cohort_baseline_*` checks pass under that policy — verified by §7 commands #3.
- [ ] Legacy baseline is deprecated but still runnable only when explicitly requested (`--mode baseline`) — verified by §7 commands #4.
- [ ] Delta/question-delta diagnostics remain valid and deterministic after policy flip — verified by §7 commands #5.
- [ ] Deep-dive emitter payload/cards clearly label promoted-vs-legacy comparison semantics and tests remain green — verified by §7 command #2.
- [ ] No files outside §4 are touched — verified by `git diff --stat <base>...HEAD` filtered to §4.

> **Reviewer reminder:** each guarantee above is harness/emitter boundary behavior; unit-only proofs are insufficient without the end-to-end CLI checks in §7.

## §10 Out-of-band notes

- This PR intentionally does **not** modify PLAN/CHECKLIST/HANDOFF archive docs; parent handles Stage 4b atomic doc-sync after merge.
- This PR intentionally does **not** change promotion thresholds or gate criteria text; it changes default lane policy and preserves legacy diagnostics.
