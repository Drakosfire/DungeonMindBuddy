---
# Optional workflow contract: literal markdown the worker pastes into the
# GitHub PR description.
pr_body_template: |
  ## Summary
  Improve the L3 question deep-dive canvas presentation so the C1S13 holdout surfaces cohort headline counts, failure buckets, support deltas, and compact baseline-vs-default must-hit evidence without restoring the old full baseline panel.

  ## Verification (verbatim §7)
  Worker: paste §7 command outputs here before opening the PR.

  ## `git diff --stat` (§4 paths only)
  ```text
  Worker: paste allowlisted diff stat here before opening the PR.
  ```
---

# HANDOFF — PR #20: C1S13 L3 deep-dive canvas presentation

**Created:** 2026-05-13 (UTC).
**Status:** COMPLETE — merged to `main` (merge commit `bb19d22910c4fb8720704ad6469d35165620936e`, 2026-05-13T14:11:45Z). Archived under `Docs/Plans/archive/2026-05-13/handoffs/`.
**Parent agent:** Cursor agent; dispatcher is responsible for post-merge atomic doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, `M2: in_progress`, `M3: complete`, `M4: not_started`). This handoff is a presentation/diagnostics slice after PR #19; it does not change retrieval behavior, gold, or scoring.

---

## §1 Mission

Improve the shared L3 question deep-dive canvas emitter so the C1S13 holdout canvas renders the headline cohort counts, failure-diagnostic buckets, support-ratio deltas, and compact baseline-vs-default must-hit comparisons needed to judge failures skeptically.

## §2 Why this slice (context for the subagent)

- PR #19 promoted the equivalence-augmented cohort baseline as the default `--write` / `--check` lane and removed the old full baseline section from the generated L3 deep-dive canvases.
- A follow-up audit of `canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx` found the canvas was technically refreshed but under-presented the important evidence: it showed only `question_count`, collapsed `unchanged_fail` rows by default, hid `failure_diagnostic.bucket`, hid `support_ratio_delta`, and did not show the baseline-vs-default must-hit evidence needed to understand a `regressed` row.
- The underlying C1S13 question-delta artifact already contains the data needed for a better canvas: `summary`, `failure_diagnostic_summary`, per-scenario pass counts, per-row `failure_diagnostic`, per-row `support_ratio_delta`, and both `baseline.context_must_hits` and `with_equivalence.context_must_hits`.
- This slice is **presentation-only**. Do not change the retriever, route-equivalence manifests, gold, cohort artifacts, or scorer/classifier logic.
- Known separate issue, explicitly out of scope here: the existing C1S13 question-delta JSON embeds `scenario_level_delta_path` pointing at `cohort_l3_ab_delta_c1s1_to_c1s3_v1.json` instead of `cohort_l3_ab_delta_c1s13_v1.json`. Do not fix that in this PR; leave it for a data-layer follow-up.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — non-negotiable §4 allowlist / §5 denylist / §7 verification contract.
2. **`.cursor/skills/benchmark-review-canvas/SKILL.md`** — benchmark review canvas layout principles; use its "headline stats", "gate table", "per-item cards", and "open failing cards by default" guidance, but do not migrate this PR to a brand-new canvas architecture.
3. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — current Phase B state, PR #19 integration note, and `next_gate_command` canvas regeneration command.
4. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` — Reanchor block and C1S13 / PR #19 evidence.
5. `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` — shared emitter/template to modify.
6. `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json` — source data for the C1S13 holdout canvas; read-only in this PR.
7. `canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx` — generated canvas whose rendered review surface is the acceptance target.
8. `tests/test_cohort_l3_question_deep_dive_canvas_emit.py` — emitter tests to extend.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` | Render headline stats, failure-diagnostic bucket/reasons, support-ratio delta, compact baseline-vs-default must-hit comparison, C1S13-aware title, and open `unchanged_fail` rows by default. |
| Modify | `tests/test_cohort_l3_question_deep_dive_canvas_emit.py` | Assert the new C1S13 presentation contract and guard against accidentally restoring the old full baseline panel. |
| Modify | `canvases/cohort-l3-ab-question-deep-dive.canvas.tsx` | Regenerated output from the shared emitter so default cohort canvas stays in sync with the template. |
| Modify | `canvases/cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx` | Regenerated output from the shared emitter so natural cohort canvas stays in sync with the template. |
| Modify | `canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx` | Regenerated C1S13 holdout canvas; this is the primary review target. |

> Expected diff stat shape: **5 paths** exactly. If extra paths appear, revert them before opening the PR.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these:

| Path | Why this PR must not touch it |
|---|---|
| `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Data-layer generation and `scenario_level_delta_path` fixes are a separate workstream; this PR is presentation-only. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_*.json` | Existing committed artifacts are inputs only. Do not regenerate or edit JSON in this presentation slice. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_*.json` | Scenario-level deltas are out of scope. |
| `evals/sentence_routing_retrieval_falsification/c1s13_holdout_l3_deep_dive_canvas_emit.py` | This module emits a small JSON payload for other tooling; it is not the C1S13 holdout L3 canvas generator. |
| `tests/test_c1s13_holdout_l3_deep_dive_canvas_emit.py` | Same reason: payload contract, not the rendered L3 canvas. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold edits would change the rubric; forbidden here. |
| `evals/sentence_routing_retrieval_falsification/cohorts/**` | Cohort manifests are stable inputs. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/**` | Route-equivalence producer artifacts are stable inputs. |
| `src/agent/session_memory_query.py` | Retriever/ranking behavior is out of scope. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Harness row production is out of scope. |
| `.cursor/**` | Do not include local rule/skill experiments or Cursor metadata. |
| `Docs/Plans/**` except this handoff | Post-merge doc-sync belongs to the parent after merge, not the worker PR. |

If a denylisted file appears necessary, stop and say so in the PR body before proceeding.

## §6 Implementation contract

### §6.1 Header and cohort identity

Update the template in `cohort_l3_question_deep_dive_canvas_emit.py` so the rendered canvas has:

- Title: `Cohort L3 Question Deep Dive — {cohort_id}`.
- `cohort_id` may be derived deterministically from `payload.cohort_manifest` by taking the basename without `.json` (for C1S13 this must render `c1s13_v1`).
- A header block/card near the top that renders:
  - `question_count`,
  - `summary.regressed`,
  - `summary.improved`,
  - `summary.unchanged_pass`,
  - `summary.unchanged_fail`,
  - per-scenario `baseline_pass_count` vs `with_equivalence_pass_count`.

The C1S13 source values currently are:

- `question_count: 25`
- `summary: { regressed: 4, improved: 2, unchanged_pass: 12, unchanged_fail: 7 }`
- scenario `baseline_pass_count: 16`
- scenario `with_equivalence_pass_count: 14`

Do not hardcode those numbers; render from payload.

### §6.2 Failure-diagnostic summary table

Render `payload.failure_diagnostic_summary` near the header, preferably as a compact table or list. The C1S13 source values currently include:

- `passed: 12`
- `equivalence_helped: 2`
- `ranking_regression: 8`
- `missing_lexical_handle: 0`
- `retriever_support_gap: 3`
- `gold_or_rubric_gap: 0`

Again: do not hardcode; render whatever keys exist.

### §6.3 Per-question card evidence

For each question card:

- Keep the summary line as `{question_id} — {q.delta.verdict}` or a clearer equivalent.
- Render `q.failure_diagnostic.bucket` prominently near the top of the card.
- Render `q.failure_diagnostic.reasons` as a short list or comma-separated line.
- Render `q.delta.support_ratio_delta` near the bucket/reasons.
- For `regressed` and `unchanged_fail` rows, render a compact side-by-side must-hit comparison:
  - required tokens (`q.must_hit_tokens`),
  - baseline matched tokens (`q.baseline.context_must_hits`),
  - baseline missing tokens (`q.baseline.context_must_hits_missing`),
  - default/equivalence matched tokens (`q.with_equivalence.context_must_hits`),
  - default/equivalence missing tokens (`q.with_equivalence.context_must_hits_missing`).
- It is acceptable to render this comparison for all rows if simpler, but the review-critical guarantee is that `regressed` and `unchanged_fail` rows show it.
- Open `regressed`, `improved`, and `unchanged_fail` rows by default.

Important nuance: do **not** restore the old full `<h3>Baseline</h3>` panel or a full baseline JSON dump. The PR #19 presentation goal still stands: the default lane is the primary rendered lane. This PR only adds compact baseline evidence where a comparison is necessary to understand why the verdict is `regressed` or `unchanged_fail`.

### §6.4 JSON dump behavior

Keep a debug JSON dump if useful, but do not make it the only place where headline/bucket/support evidence appears. If the dump still strips `baseline` for readability, the compact side-by-side must-hit comparison must be rendered outside the dump so reviewers can inspect baseline-vs-default evidence without opening raw JSON.

### §6.5 Generated outputs

After changing the shared template, regenerate all three existing deep-dive canvases so the repo does not carry mixed template generations:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json --output canvases/cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json --output canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx
```

## §7 Verification commands

Run all commands and paste outputs verbatim in the PR body.

```bash
# 1) Emitter contract tests, including the new C1S13 presentation assertions.
uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py -q

# 2) Canvas path guard remains green.
uv run pytest tests/test_cursor_canvas_paths.py -q

# 3) Regenerate all three shared-emitter canvases.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json --output canvases/cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json --output canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx

# 4) C1S13 canvas smoke: headline, bucket, support delta, compact comparison, no old full baseline panel.
uv run python - <<'PY'
from pathlib import Path
t = Path("canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx").read_text(encoding="utf-8")
required = [
    "Cohort L3 Question Deep Dive",
    "c1s13_v1",
    "regressed",
    "improved",
    "unchanged_pass",
    "unchanged_fail",
    "failure_diagnostic",
    "ranking_regression",
    "support_ratio_delta",
    "Baseline",
    "Default",
]
missing = [s for s in required if s not in t]
assert not missing, missing
assert "<h3>Baseline</h3>" not in t
assert "With Equivalence" not in t
print("c1s13_canvas_presentation_smoke OK")
PY

# 5) Optional but recommended full slice after the presentation change.
uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py tests/test_cursor_canvas_paths.py -q
```

## §8 Reporting contract

PR body must include:

1. `git diff --stat origin/main...HEAD` filtered to §4 paths only (exactly 5 rows).
2. Verbatim output for all §7 commands.
3. One paragraph "what stayed unchanged" explicitly stating:
   - no retriever/ranking logic changed,
   - no gold changed,
   - no cohort artifacts changed,
   - no route-equivalence manifests changed,
   - old full `<h3>Baseline</h3>` panel was not restored.
4. One paragraph "C1S13 presentation readout" with the rendered headline values observed in the canvas: `question_count`, `summary`, `baseline_pass_count`, `with_equivalence_pass_count`, and the top failure bucket.

## §9 Acceptance rubric

- [ ] C1S13 canvas renders the cohort identity and headline counts from payload (`c1s13_v1`, `question_count`, summary buckets, and per-scenario baseline/default pass counts) — verified by §7 #1, #3, and #4.
- [ ] C1S13 canvas renders `failure_diagnostic_summary` and each card renders `failure_diagnostic.bucket` plus `reasons`, so the reviewer no longer has to scroll raw JSON to see `ranking_regression` / `retriever_support_gap` — verified by §7 #1 and #4.
- [ ] C1S13 `regressed` and `unchanged_fail` cards render `support_ratio_delta` and compact baseline-vs-default must-hit evidence outside the JSON dump — verified by §7 #1 and #4.
- [ ] `unchanged_fail` rows open by default along with `regressed` and `improved` rows — verified by §7 #1 and source inspection of the generated TSX from §7 #3.
- [ ] The old full baseline panel is not restored: no `<h3>Baseline</h3>`, no `"With Equivalence"` heading, no full baseline-first UI — verified by §7 #4.
- [ ] Generated canvases remain deterministic and in sync across the shared emitter outputs (default, natural, C1S13) — verified by §7 #3 and allowlisted diff stat.
- [ ] No files outside §4 are touched — verified by allowlisted diff stat.
- [ ] Cost remains $0; this is local JSON/TSX generation only, with no LLM calls or benchmark reruns — verified by §7 command set and PR diff.

> Reviewer reminder: this PR fixes presentation only. If the worker changes `cohort_baseline_run.py`, any `artifacts/baselines/*.json`, gold, retriever code, or lexicon artifacts, request changes and split that into a separate handoff.

## §10 Out-of-band notes

- The C1S13 audit found a separate data-layer issue: `cohort_l3_ab_question_delta_c1s13_v1.json` currently embeds `scenario_level_delta_path` for the tight `c1s1_to_c1s3` delta. Do not fix it here.
- The dominant substantive C1S13 pattern appears to be equivalence token pollution (`captain`, `dustwalker`, `elderwyld`, `ironveil`, `jove`, `longmont`, `lysandra`, `npc`, `route`, `torbin`) creating `ranking_regression` rows. Do not change manifests or ranking in this PR.
- Current local `main` re-anchor before writing this handoff: `HEAD d884d93 eval: default-equivalence L3 canvases; holdout payload without legacy lane`; GitHub PR list ends at #19, so this handoff reserves planned PR #20.
