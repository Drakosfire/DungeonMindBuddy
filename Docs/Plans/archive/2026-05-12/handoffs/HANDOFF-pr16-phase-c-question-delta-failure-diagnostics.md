---
pr_body_template: |
  ## Summary
  Add deterministic failure-mode diagnostics to L3 question-delta artifacts so Phase C can distinguish missing lexical handles from retriever/rubric failures before any default retrieval promotion.

  ## Verification (verbatim §7)
  Worker: paste command outputs after running every §7 command.

  ## `git diff --stat` (§4 paths only)
  ```text
  Worker: paste allowlist-filtered diff stat.
  ```
---

> **MERGED:** `main` @ `7978cd06151e6104fe064eba2e4c0fed1bb9a8f3` (2026-05-12T20:24:05Z); review fallback id **`4275831033`** (round 2 APPROVE); round 1 review id **`4275322528`**.

# HANDOFF — PR #16: Phase C question-delta failure diagnostics

**Created:** 2026-05-12 (UTC).  
**Status:** COMPLETED — merged; atomic doc-sync archived this handoff.  
**Parent agent:** Cursor agent; parent handles post-merge atomic doc-sync.  
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`; `M2: in_progress`, `M3: complete`, `M4: not_started`). This handoff advances the Phase C promotion decision path without flipping defaults.

---

## §0 Re-anchor Snapshot

- `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` Reanchor Block: Phase C gated wiring exists, promotion is still blocked by PR #12 `promotion_gate_candidate.status:none_found`; C1S13 now has routed session memory and a 16/25 baseline pass readout, but 9/25 failures remain.
- `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` v22: next fork is promotion acceptance criteria vs wider falsification cohorts vs further gold audit/normalization. This PR takes the smallest useful wiring step for that fork: make question-delta failures machine-classified.
- Git state verified before authoring: local `HEAD` and `origin/main` both `2cb4b0f7a1503c24db70e0a6ba196950b5eae095` (`feat(eval): add C1S13 unit-annotation beat ablations and smallest-span default`). That commit is unrelated to this Phase C workstream but is now the integration tip.
- Latest GitHub PR at author time: #15, so this handoff reserves #16 by convention.

## §1 Mission

Add deterministic per-question failure diagnostics to `cohort_l3_ab_question_delta_*` generation so unchanged failures can be bucketed before changing route-equivalence ranking behavior.

## §2 Why this slice

- PR #9 wired generated route equivalences into retrieval behind `--use-route-equivalence-for-ranking`, and PR #10/#11/#13 gave us per-question deltas for tight, natural, and C1S13 holdout cohorts.
- PR #12 proved the packaged alias-count promotion gate has `promotion_gate_candidate.status: none_found`; PR #15 fixed a C1S13 hierarchy-gold error but did not move the holdout pass signal.
- The open Phase C checklist item is explicit: failure-mode diagnostics must distinguish "missing lexical handle" from retriever bug before default promotion. Today the artifacts show `unchanged_fail`, but not why.
- This slice is **diagnostics only**. It must not flip default retrieval, tune ranking, edit gold, or change corpus/session-memory inputs.

## §3 Authoritative inputs

Read these in order before writing code:

1. `.cursor/rules/external-agent-pr-loop.mdc` — review contract: §4 allowlist, §5 denylist, §7 verification, §9 rubric pairing.
2. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` — Reanchor Block and Phase C status.
3. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — v22 `execution_state`, PR #12/#13/#15 `integration_notes`, and `external_pull_requests` rubric lineage.
4. `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` — current `_build_question_delta` shape and `--check-question-delta` contract.
5. `tests/test_cohort_baseline_run.py` — current subprocess boundary tests for question-delta generation/checking.
6. `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json`
7. `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json`
8. `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json`
9. `evals/sentence_routing_retrieval_falsification/README.md` — current route-equivalence and L3 diagnostics documentation.
10. `tests/conftest.py` — confirms env loading discipline; this PR should remain retrieval-only and should not require API keys.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Add deterministic question-delta failure classification and summary counts. |
| Modify | `tests/test_cohort_baseline_run.py` | Boundary and helper tests for the new diagnostic fields and existing check-mode determinism. |
| Modify | `evals/sentence_routing_retrieval_falsification/README.md` | Document the diagnostic buckets and how to interpret them. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json` | Regenerate deterministic tight-cohort question delta with additive diagnostics. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json` | Regenerate deterministic natural-cohort question delta with additive diagnostics. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json` | Regenerate deterministic C1S13 holdout question delta with additive diagnostics. |

> The expected `git diff --stat` must be expressible from this allowlist. If another path changes, revert it before opening the PR.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch these paths:

| Path | Why this PR must not touch it |
|---|---|
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Ranking behavior already landed behind `--use-route-equivalence-for-ranking`; this slice classifies outcomes and must not change retrieval. |
| `evals/sentence_routing_retrieval_falsification/route_equivalence_shadow.py` | Loader/shadow contracts are not the failure surface for this slice. |
| `src/lexicon_phase_b/**` | Producer artifacts and schema are not changing. |
| `scripts/build_route_equivalence_manifests.py` | Producer determinism is already guarded; this PR consumes existing artifacts. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | No gold/rubric edits. A diagnostic saying "gold_or_rubric_gap" is evidence for a later human review, not permission to edit gold here. |
| `evals/sentence_routing_retrieval_falsification/cohorts/**` | No cohort membership changes. |
| `canvases/**` | Do not regenerate canvases in this slice; the existing deep-dive canvas already renders raw question rows via JSON. A later UI-only PR may surface the new bucket visually. |
| `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` and `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` | Parent dispatcher handles atomic doc-sync after merge; worker must not partially advance the plan. |
| `Backlog.md` / `Backlog-DONE.md` | Parent owns backlog hygiene; do not mix planning bookkeeping into the implementation PR. |

If one of these seems necessary, stop and explain in the PR body instead of editing it.

## §6 Implementation Contract

### 6.1 Additive diagnostic shape

Keep `COHORT_L3_QUESTION_DELTA_SCHEMA_V1` unchanged. This PR adds fields inside the existing artifact shape; it does not define a new artifact family.

Each question row in `_build_question_delta` should gain:

```python
"failure_diagnostic": {
    "bucket": "<one of the closed values below>",
    "reasons": [str, ...],
    "baseline_missing_route_substrings": [str, ...],
    "with_equivalence_missing_route_substrings": [str, ...],
}
```

Top-level question-delta output should gain:

```python
"failure_diagnostic_summary": {
    "<bucket>": int,
    ...
}
```

Closed bucket vocabulary:

- `passed` — `delta.verdict == "unchanged_pass"`.
- `equivalence_helped` — `delta.verdict == "improved"`.
- `ranking_regression` — `delta.verdict == "regressed"` OR equivalence mode loses route substrings / must-hit tokens that baseline had.
- `missing_lexical_handle` — both baseline and equivalence runs fail, and at least one expected route substring remains unmatched in equivalence mode.
- `retriever_support_gap` — route substrings are all matched in equivalence mode (or no route substrings are expected), but required must-hit tokens or context-support ratio still fail.
- `gold_or_rubric_gap` — deterministic fallback when none of the above explain the failure; this means "needs human/gold/rubric review", not "auto-edit gold".

### 6.2 Helper function

Add a small pure helper near `_build_question_delta`:

```python
def _classify_question_delta_failure(
    *,
    verdict: str,
    expected_route_substrings: list[str],
    baseline_route_breakdown: dict[str, bool],
    equivalence_route_breakdown: dict[str, bool],
    required_must_hits: list[str],
    baseline_hits: list[str],
    equivalence_hits: list[str],
    min_context_support_ratio: float,
    baseline_context_support_ratio: float,
    equivalence_context_support_ratio: float,
) -> dict[str, object]:
    ...
```

Rules:

- Deterministic only; no LLM calls, no filesystem reads.
- Preserve input order where it is meaningful, otherwise sort lists for byte stability.
- Do not mutate `brow`, `erow`, or gold payload dictionaries.
- The function must be directly unit-testable without subprocess.

### 6.3 Artifact regeneration

Regenerate only the three allowlisted question-delta artifacts:

1. tight C1S1–C1S3 default question delta,
2. natural cohort question delta,
3. C1S13 holdout question delta.

Do not regenerate scenario deltas, baselines, canvases, gold, route-equivalence JSONL, or corpus/session-memory files.

## §7 Verification Commands

Run every command and paste output into the PR body.

```bash
# Unit + subprocess boundary coverage for the changed generator.
uv run pytest tests/test_cohort_baseline_run.py -q

# Existing consumers still tolerate the additive question-row fields.
uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py tests/test_cohort_l3_alias_saturation_canvas_emit.py -q

# Existing lexicon + breadcrumb harness surfaces remain green.
uv run pytest tests/lexicon_phase_b/ tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q

# Regenerate the three committed question-delta artifacts.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --mode both --write-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json --mode both --write-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json --mode both --write-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json

# Check the committed deterministic artifacts at the harness boundary.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-question-delta
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json

# Human-readable readout for review. The output must include all three files.
uv run python - <<'PY'
import json
from pathlib import Path
files = [
    Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json"),
    Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json"),
    Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json"),
]
for path in files:
    payload = json.loads(path.read_text(encoding="utf-8"))
    print(path.name, payload.get("summary"), payload.get("failure_diagnostic_summary"))
PY
```

## §8 Reporting Contract

In the PR body, include:

1. `git diff --stat` filtered to §4 allowlist paths only.
2. Verbatim §7 outputs.
3. The readout from the final Python snippet.
4. One paragraph stating what stayed unchanged:
   - default retrieval behavior unchanged,
   - `--use-route-equivalence-for-ranking` semantics unchanged,
   - no gold/cohort/route-equivalence/corpus/canvas files changed.

## §9 Acceptance Rubric

Reviewer accepts only if every bullet is true:

- [ ] `cohort_l3_ab_question_delta_*` artifacts include per-question `failure_diagnostic` and top-level `failure_diagnostic_summary` with the closed bucket vocabulary above — verified by `uv run pytest tests/test_cohort_baseline_run.py -q` and the final readout command.
- [ ] `--check-question-delta` passes for tight, natural, and C1S13 manifests after regeneration — verified by the three `cohort_baseline_run --check-question-delta` commands.
- [ ] Existing consumers remain compatible with the additive fields — verified by `uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py tests/test_cohort_l3_alias_saturation_canvas_emit.py -q`.
- [ ] Lexicon producer, shadow consumer, and breadcrumb harness behavior remain green and unchanged — verified by `uv run pytest tests/lexicon_phase_b/ tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q`.
- [ ] The PR does not change retrieval ranking/default behavior, route-equivalence producer artifacts, gold files, cohort manifests, canvases, or plan/checklist docs — verified by `git diff --stat <base>...HEAD` and the §4 allowlist.
- [ ] Diagnostic buckets are deterministic and explainable from existing artifact fields only; no LLM calls, semantic graders, timestamps, or environment-dependent paths enter the output — verified by helper tests plus `--check-question-delta` byte stability.

## §10 Out-of-band Notes

- This is intentionally **not** a promotion PR. If diagnostics imply the next move is default flip, gold audit, or ranking-rule change, capture that in PR notes for the parent; do not implement it here.
- Question-delta artifacts are normally read-only for analysis slices. This PR is the exception because it changes the generator contract and regenerates the deterministic baselines from the same committed inputs.
- Cost should be `$0` because every command is retrieval-only and pytest-only.
