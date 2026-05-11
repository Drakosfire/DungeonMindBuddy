---
pr_body_template: |
  ## Summary
  Add a wider-cohort (`natural_v1`) A/B baseline + scenario-delta + per-question-delta surface, including a dedicated deep-dive canvas, so we can test whether the tight-cohort L3 regressions generalize or dissolve at scale.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

# HANDOFF — PR #11: wider-cohort `natural_v1` A/B baseline + per-question delta

**Created:** 2026-05-11 (UTC).
**Status:** COMPLETED — merged via [PR #11](https://github.com/Drakosfire/DungeonMindBuddy/pull/11) on 2026-05-11T19:39:14Z (merge commit `eec38807ea1866e63b5997e21558968d7559ea16`). Review round: 1 (`APPROVE` demoted to `COMMENTED` under self-review fallback, review id `4266836748`).
**Parent agent:** Cursor agent; dispatcher is responsible for post-merge atomic doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, `M2: in_progress`, `M3: complete`, `M4: not_started`). This handoff opens the wider-cohort falsification lane named in `next_gate_command`.

---

## §1 Mission

Add a committed wider-cohort `natural_v1` manifest plus deterministic baseline, scenario-level delta, and per-question delta artifacts (and matching deep-dive canvas) while fixing `cohort_baseline_run` check-mode manifest forwarding so these contracts are verifiable at the harness boundary.

## §2 Why this slice (context for the subagent)

- PR #9 and PR #10 established the tight-cohort (`c1s1_to_c1s3_v1`) A/B diagnostics surface and found a real regression headline (`with_equivalence_all_ok_count` 1 vs baseline 3; per-question `regressed: 2/44`).
- The next decision is empirical, not speculative: run the same diagnostics shape on a wider cohort (`natural_v1`) to test whether broadcast-alias dilution generalizes.
- This slice intentionally does **not** change retrieval/scoring behavior, route-equivalence producer artifacts, prompt text, gold files, or default cohort anchors.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — §4 allowlist / §5 denylist / §7 verification contract.
2. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — current phase, PR #9/#10 judgment records, and wider-cohort next slice language.
3. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` — Reanchor block + current evidence wording.
4. `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` — canonical manifest shape to mirror.
5. `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` — current baseline/delta/question-delta contracts and existing `--check*` behavior.
6. `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` — current emitter contract to extend for alternate input/output paths.
7. `tests/test_cohort_baseline_run.py` and `tests/test_cohort_l3_question_deep_dive_canvas_emit.py` — boundary tests to extend.
8. **`tests/conftest.py`** — confirm env bootstrap expectations (`load_dungeonmindbuddy_dotenv()`).

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Make `--check-delta` and `--check-question-delta` honor `--manifest`; ensure question-delta metadata references the active delta path; keep deterministic ordering. |
| Modify | `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` | Add CLI args for input/output paths (default behavior unchanged) so wider-cohort canvas can be emitted without clobbering tight-cohort canvas. |
| Create | `evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json` | New wider-cohort manifest using `breadcrumb_query_natural_v1.json` + existing `c2s20_norm_smoke.records_meta.jsonl`. |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json` | Frozen wider-cohort baseline summary (`dmb_breadcrumb_query_cohort_summary_v2`). |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_natural_v1.json` | Frozen wider-cohort scenario-level L3 A/B delta (`dmb_breadcrumb_query_cohort_l3_delta_v1`). |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json` | Frozen wider-cohort per-question L3 A/B delta (`dmb_breadcrumb_query_cohort_l3_question_delta_v1`). |
| Create | `canvases/cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx` | Generated wider-cohort deep-dive canvas output. |
| Modify | `tests/test_cohort_baseline_run.py` | Add/extend tests for manifest-aware check modes and question-delta metadata consistency for non-default manifests. |
| Modify | `tests/test_cohort_l3_question_deep_dive_canvas_emit.py` | Add/extend tests for parameterized emitter input/output while preserving default path behavior. |

> Expected diff stat shape: **9 paths** exactly. If extra paths appear, revert them before opening the PR.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these. Concrete collision risks named alongside the path:

| Path | Why this PR must not touch it |
|---|---|
| `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` | Tight-cohort historical anchor; mutating it erases prior PR #6/#9/#10 comparability. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` | Existing frozen baseline contract for `--check` on default lane. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json` | Existing frozen scenario-level delta anchor from PR #9. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json` | Existing frozen per-question anchor from PR #10 + follow-up commit. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold/rubric drift risk; this slice measures behavior, it does not rewrite expectations. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/*.jsonl` | Producer artifacts are fixed inputs; modifying them creates a confounded experiment. |
| `src/agent/session_memory_query.py` | Retrieval logic changes would invalidate A/B comparability. |
| `src/prompts/**` | Prompt changes are out of scope for retrieval-only falsification. |
| `Docs/Plans/**` (other than this handoff file) | Parent agent owns post-merge atomic doc-sync; worker should not pre-edit plan/checklist docs. |

If the worker thinks one of these is genuinely needed, stop and ask in the PR description before opening the PR.

## §6 Implementation contract

### §6.1 Manifest-aware boundary checks in `cohort_baseline_run.py`

The following checks must run against the **caller-selected manifest**, not implicitly against defaults:

```python
# Existing CLI (keep flags) must support:
#   --manifest <cohort_manifest_path>
#   --delta <delta_path>
#   --check-delta
#   --check-question-delta [<question_delta_path>]
#
# Required behavior:
# - check-delta rerun command forwards --manifest and compares to --delta.
# - check-question-delta rerun command forwards --manifest and compares to the selected qdelta path.
# - both checks remain byte-identity checks against committed baselines.
```

Metadata consistency:

```python
# In question-delta payload:
# "scenario_level_delta_path" should reflect the actual delta path used
# for the run/check lane (workspace-relative), not always _DEFAULT_DELTA.
```

Determinism requirements:
- Preserve manifest scenario order; preserve gold query order.
- Keep sorted list/set-derived fields sorted.
- No extra retrieval runs beyond existing `--mode both` baseline/equivalence pair.

### §6.2 Parameterized deep-dive canvas emitter

Add optional CLI args to `cohort_l3_question_deep_dive_canvas_emit.py`:

```bash
--input  <question_delta_json>
--output <canvas_tsx>
```

Rules:
- Defaults must preserve current behavior (`c1s1_to_c1s3` input and existing canvas output).
- Generated markers (`BEGIN GENERATED ...` / `END GENERATED ...`) remain stable.
- No runtime fetches; payload remains inlined in output TSX.

### §6.3 New wider-cohort artifacts

Create new manifest + baselines (do not mutate existing anchors):
- Manifest: `cohorts/natural_v1.json` (schema `dmb_breadcrumb_query_cohort_manifest_v1`).
- Baseline: `cohort_baseline_natural_v1.json`.
- Scenario delta: `cohort_l3_ab_delta_natural_v1.json`.
- Question delta: `cohort_l3_ab_question_delta_natural_v1.json`.
- Canvas: `cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx`.

`natural_v1.json` should point to:
- `gold`: `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json`
- `records_jsonl`: `evals/sentence_routing_retrieval_falsification/artifacts/c2s20_norm_smoke.records_meta.jsonl`
- route equivalence inputs identical to existing cohort manifest unless a concrete mismatch is discovered.

## §7 Verification commands

The worker must run **every** command and paste output into the PR body.

```bash
# 1) Existing suites still green.
uv run pytest tests/lexicon_phase_b/ -q
uv run pytest tests/test_cohort_baseline_run.py -q
uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py -q

# 2) Build/freeze wider-cohort artifacts.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json \
  --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json \
  --write

uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json \
  --mode both \
  --write-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_natural_v1.json \
  --write-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json

# 3) Boundary checks for the new cohort (must use --manifest, not defaults).
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json \
  --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json \
  --check

uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json \
  --delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_natural_v1.json \
  --check-delta

uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json \
  --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json

# 4) Emit wider-cohort deep-dive canvas and smoke marker presence.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json \
  --output canvases/cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx

uv run python -c "from pathlib import Path; p=Path('canvases/cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx'); t=p.read_text(encoding='utf-8'); print('canvas_exists', p.exists()); print('has_generated_markers', 'BEGIN GENERATED' in t and 'END GENERATED' in t)"

# 5) Empirical readout + retrieval-only cost lane smoke.
uv run python -c "import json; p='evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json'; d=json.load(open(p)); print('schema', d['schema_id']); print('question_count', d['question_count']); print('summary', d['summary'])"
uv run python -c "import json; p='evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json'; d=json.load(open(p)); print('llm_enabled', d.get('llm_enabled')); print('retrieval_only', d.get('retrieval_only')); print('all_ok', d.get('aggregate',{}).get('all_scenarios_all_ok'))"
```

## §8 Reporting contract

In the PR body the worker MUST include:

1. `git diff --stat origin/main...HEAD` filtered to §4 allowlist paths only (exactly 9 rows).
2. Verbatim output for every §7 command.
3. One short “what stayed unchanged” paragraph that explicitly states:
   - no retrieval-core code changes,
   - no gold edits,
   - no route-equivalence JSONL edits,
   - default tight-cohort baselines remain untouched.

## §9 Acceptance rubric

The reviewer will accept ONLY if every bullet is true.

- [ ] Wider-cohort manifest + three baseline artifacts + natural-v1 canvas are present and deterministic on rerun — verified by §7 #2, #3, and #4.
- [ ] `--check-delta` and `--check-question-delta` now validate against the caller-provided `--manifest` path (boundary-level, not helper-only) — verified by §7 #3.
- [ ] Question-delta metadata references the active delta lane (not always default c1s1 path) and remains schema-valid (`dmb_breadcrumb_query_cohort_l3_question_delta_v1`) — verified by §7 #5.
- [ ] Emitter defaults remain backward-compatible while custom `--input/--output` emits a second canvas deterministically with generated markers — verified by §7 #1 and #4.
- [ ] No files outside §4 are touched — verified by filtered diff-stat.
- [ ] Cost lane stays retrieval-only (`llm_enabled: false`, `retrieval_only: true`) for this slice — verified by §7 #5.

> Reviewer reminder: rubric bullets tied to harness behavior must be proven by harness commands (`cohort_baseline_run ... --check*`), not only unit tests.

## §10 Out-of-band notes (optional)

- If `natural_v1` unexpectedly lacks stable records input, stop and report before inventing a new ingestion pipeline in this PR.
- Keep this slice measurement-first; do not add alias-saturation heuristics yet.
- Post-merge parent doc-sync should carry forward one rubric bullet about “check-mode reruns must forward non-default manifest args.”

---

**End of handoff.** Dispatcher next step after PR opens:
`uv run python scripts/review_external_pr.py fetch 11 --handoff Docs/Plans/HANDOFF-pr11-wider-cohort-natural-v1-ab-baseline-and-question-delta.md --extract-rubric`
