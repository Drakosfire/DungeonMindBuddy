---
# Optional workflow contract: literal markdown the worker pastes into the
# GitHub PR description.
pr_body_template: |
  ## Summary
  Fix C1S13 question-delta provenance so `scenario_level_delta_path` points at the C1S13 scenario-level delta artifact when the manifest is `c1s13_v1`.

  ## Verification (verbatim §7)
  Worker: paste §7 command outputs here before opening the PR.

  ## `git diff --stat` (§4 paths only)
  ```text
  Worker: paste allowlisted diff stat here before opening the PR.
  ```
---

# HANDOFF — PR #21: C1S13 question-delta `scenario_level_delta_path`

**Created:** 2026-05-13 (UTC).
**Status:** COMPLETE — merged to `main` (merge commit `eabd3a83024b9cabe4a07cc22e4f072512730096`, 2026-05-13T15:23:54Z). Archived under `Docs/Plans/archive/2026-05-13/handoffs/`.
**Parent agent:** Cursor agent; dispatcher is responsible for post-merge atomic doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, `M2: in_progress`, `M3: complete`, `M4: not_started`). This handoff is a data-provenance repair after PR #19; it does not change retrieval behavior, gold, scoring, or canvas presentation.

---

## §1 Mission

Fix C1S13 question-delta provenance so `cohort_l3_ab_question_delta_c1s13_v1.json` records `scenario_level_delta_path` as `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json`, and harden the writer path so manifest-specific question-delta writes do not silently fall back to the tight-cohort delta path.

## §2 Why this slice (context for the subagent)

- The C1S13 holdout L3 question-delta artifact currently embeds the wrong scenario-level delta pointer:
  - current bad value: `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json`
  - correct value: `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json`
- `cohort_baseline_run.py` already has `_default_delta_for_manifest(manifest)` for `c1s13_v1.json` and `natural_v1.json`, but the `--mode both --write-question-delta` path uses `args.delta` directly when `--write-delta` is absent. Because `args.delta` defaults to the tight-cohort `_DEFAULT_DELTA`, C1S13 question-delta writes record the wrong path unless the operator passes `--delta ...c1s13...` explicitly.
- `--check-question-delta` is currently too forgiving: it reads the expected artifact's existing `scenario_level_delta_path` and passes that back into the regeneration command, so it can preserve and bless the stale pointer instead of catching it.
- This slice should prefer the robust fix: normalize the effective delta path from the manifest whenever the operator has not explicitly supplied `--delta`. Merely re-emitting the artifact with an explicit `--delta` would fix today's JSON but leave the footgun in place.
- This slice is data-provenance only. It must not touch canvases, presentation templates, route-equivalence manifests, retriever code, or gold.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — non-negotiable §4 allowlist / §5 denylist / §7 verification contract.
2. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — current Phase B state, PR #19 integration note, and C1S13 `next_gate_command` entries.
3. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` — Reanchor block and C1S13 / PR #19 evidence.
4. `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` — `_DEFAULT_DELTA`, `_default_delta_for_manifest`, `--check-delta`, `--check-question-delta`, and `--mode both --write-question-delta` paths.
5. `tests/test_cohort_baseline_run.py` — existing question-delta, C1S13, and check-delta tests to extend.
6. `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json` — artifact to regenerate after the code fix.
7. `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json` — correct scenario-level delta artifact for C1S13.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Harden question-delta write/check path so manifest-specific default delta selection is used when `--delta` is not explicitly supplied. |
| Modify | `tests/test_cohort_baseline_run.py` | Add regression coverage proving C1S13 `--write-question-delta` without explicit `--delta` records the C1S13 scenario-level delta path, and that `--check-question-delta` does not preserve a stale expected path. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json` | Regenerate committed C1S13 question-delta artifact so `scenario_level_delta_path` points at `cohort_l3_ab_delta_c1s13_v1.json`. |

> Expected diff stat shape: **3 paths** exactly. If extra paths appear, revert them before opening the PR.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these:

| Path | Why this PR must not touch it |
|---|---|
| `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` | Canvas presentation is the separate planned PR #20. |
| `tests/test_cohort_l3_question_deep_dive_canvas_emit.py` | Canvas presentation tests belong to PR #20. |
| `canvases/cohort-l3-ab-question-deep-dive*.canvas.tsx` | Do not regenerate canvases in this data-provenance slice. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json` | Tight-cohort artifact should remain unchanged. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json` | Natural cohort artifact should remain unchanged unless a failing test proves the same bug affects committed data; if so, stop and ask. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_*.json` | Scenario-level deltas are inputs; do not regenerate them here. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold edits would change the rubric; forbidden here. |
| `evals/sentence_routing_retrieval_falsification/cohorts/**` | Cohort manifests are stable inputs. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/**` | Route-equivalence producer artifacts are stable inputs. |
| `src/agent/session_memory_query.py` | Retriever/ranking behavior is out of scope. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Harness row production is out of scope. |
| `.cursor/**` | Do not include local rule/skill experiments or Cursor metadata. |
| `Docs/Plans/**` except this handoff | Post-merge doc-sync belongs to the parent after merge, not the worker PR. |

If a denylisted file appears necessary, stop and say so in the PR body before proceeding.

## §6 Implementation contract

### §6.1 Effective delta path selection

Implement a small helper or equivalent local logic so there is one definition of the "effective delta path":

```python
def _effective_delta_for_args(*, manifest: Path, delta: Path) -> Path:
    if Path(delta) == _DEFAULT_DELTA:
        return _default_delta_for_manifest(Path(manifest))
    return Path(delta)
```

The exact function name/signature may differ, but the behavior must hold:

- For default manifest `c1s1_to_c1s3_v1.json` + default `--delta`, effective path is `_DEFAULT_DELTA`.
- For `natural_v1.json` + default `--delta`, effective path is `cohort_l3_ab_delta_natural_v1.json`.
- For `c1s13_v1.json` + default `--delta`, effective path is `cohort_l3_ab_delta_c1s13_v1.json`.
- If the operator explicitly passes `--delta /some/path.json`, preserve that explicit path.

Use this effective path in both:

- `--mode both --write-question-delta` when `--write-delta` is absent.
- `--check-question-delta`, so the check regenerates with the manifest-appropriate path rather than copying the stale path from the expected artifact.

Keep `--write-delta` behavior unchanged: if the operator writes a scenario-level delta to a custom path and also writes question-delta in the same invocation, the question-delta should point at that custom written delta path.

### §6.2 Artifact regeneration

After the code fix, regenerate only the C1S13 question-delta artifact:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --mode both \
  --write-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json
```

The resulting JSON must have:

```json
"scenario_level_delta_path": "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json"
```

Do not regenerate canvases in this PR.

### §6.3 Tests

Add regression coverage in `tests/test_cohort_baseline_run.py`.

At minimum:

1. A test that runs:

   ```bash
   uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
     --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
     --mode both \
     --write-question-delta <tmp_path>/c1s13_qdelta.json
   ```

   and asserts `scenario_level_delta_path` ends with `cohort_l3_ab_delta_c1s13_v1.json`.

2. A test that preserves explicit `--delta` behavior for custom paths. Existing `test_mode_both_question_delta_uses_active_delta_path` covers custom `--write-delta`; extend or add a sibling test if needed to prove explicit `--delta` is not ignored.

3. A committed-artifact check or direct assertion that `cohort_l3_ab_question_delta_c1s13_v1.json` contains the C1S13 delta path.

## §7 Verification commands

Run all commands and paste outputs verbatim in the PR body.

```bash
# 1) Cohort runner unit/integration tests, including new regression coverage.
uv run pytest tests/test_cohort_baseline_run.py -q

# 2) Regenerate only the C1S13 question-delta artifact.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --mode both \
  --write-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json

# 3) C1S13 question-delta check must pass against the regenerated artifact.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json

# 4) Inspect the committed artifact pointer.
uv run python - <<'PY'
import json
from pathlib import Path
p = Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json")
d = json.loads(p.read_text(encoding="utf-8"))
print(d["scenario_level_delta_path"])
assert d["scenario_level_delta_path"] == "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json"
print("c1s13_question_delta_pointer OK")
PY

# 5) Guard the other committed question-delta artifacts still check.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-question-delta
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json \
  --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json
```

## §8 Reporting contract

PR body must include:

1. `git diff --stat origin/main...HEAD` filtered to §4 paths only (exactly 3 rows).
2. Verbatim output for all §7 commands.
3. One paragraph "what stayed unchanged" explicitly stating:
   - no retriever/ranking logic changed,
   - no gold changed,
   - no cohort manifests changed,
   - no route-equivalence manifests changed,
   - no canvases or canvas emitters changed.
4. One sentence naming the before/after pointer:
   - before: `cohort_l3_ab_delta_c1s1_to_c1s3_v1.json`
   - after: `cohort_l3_ab_delta_c1s13_v1.json`

## §9 Acceptance rubric

- [ ] C1S13 `--mode both --write-question-delta` without explicit `--delta` records `scenario_level_delta_path` as `cohort_l3_ab_delta_c1s13_v1.json` — verified by §7 #1, #2, and #4.
- [ ] `--check-question-delta` for C1S13 regenerates with the manifest-appropriate default delta path and passes against the committed C1S13 artifact — verified by §7 #3.
- [ ] Existing default and natural question-delta checks remain green — verified by §7 #5.
- [ ] Explicit custom delta paths remain honored when provided by the operator — verified by `tests/test_cohort_baseline_run.py` in §7 #1.
- [ ] Only the C1S13 question-delta artifact is regenerated; no canvases, gold, manifests, lexicon artifacts, scenario-level deltas, or retriever files are touched — verified by allowlisted diff stat.
- [ ] Cost remains $0; this is retrieval-only deterministic artifact regeneration with no LLM calls — verified by §7 command set and PR diff.

> Reviewer reminder: this PR fixes provenance metadata only. If the worker changes presentation, ranking behavior, gold, or route-equivalence manifests, request changes and split that work into the relevant handoff.

## §10 Out-of-band notes

- Planned PR #20 is the separate C1S13 L3 canvas presentation fix (`Docs/Plans/HANDOFF-pr20-c1s13-l3-canvas-presentation.md`). Keep this PR independent so either can land first.
- Current local `main` re-anchor before writing this handoff: `HEAD d884d93 eval: default-equivalence L3 canvases; holdout payload without legacy lane`; GitHub PR list ends at #19; PR #20 is reserved by the active presentation handoff, so this handoff reserves planned PR #21.
