---
pr_body_template: |
  ## Summary
  Add a retrieval-only alias-saturation diagnostic surface that explains why `query_token_aliases` augmentation helps some questions and hurts others by measuring alias-count contribution, top-K rank movement, and contested-slot token wins across the committed tight and natural L3 question-delta artifacts.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

> **COMPLETED:** [PR #12](https://github.com/Drakosfire/DungeonMindBuddy/pull/12) merged 2026-05-11T20:37:15Z (merge `7eface014b3d5824a11d29ad1e91ed67c153711f`, PR head `00659b29d84dbbae57cc8ccd2567d925454a6b9c`); Stage 4b doc-sync landed PLAN v19, checklist Reanchor + Session Log, and `github-pr-12` in `external_pull_requests`.

# HANDOFF - PR #12: alias-saturation diagnostics + promotion-gate evidence surface

**Created:** 2026-05-11 (UTC).
**Status:** COMPLETED — merged via [PR #12](https://github.com/Drakosfire/DungeonMindBuddy/pull/12) on 2026-05-11T20:37:15Z (merge commit `7eface014b3d5824a11d29ad1e91ed67c153711f`). Review round: 1 (`APPROVE` posted as `COMMENTED` under self-review fallback, review id `4267219742`).
**Parent agent:** Cursor agent; dispatcher is responsible for post-merge atomic doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, milestone progress `M2: in_progress`, `M3: complete`, `M4: not_started`). **Outcome:** alias-saturation emitter + generated canvas shipped; combined payload `promotion_gate_candidate.status: none_found` under packaged rule — promotion to default remains blocked with explicit threshold-scan evidence.

---

## §1 Mission

Add a deterministic, retrieval-only alias-saturation analysis emitter that consumes the committed L3 per-question delta artifacts and produces a canvas showing per-question alias contribution plus aggregate threshold evidence for promotion-gate decisioning.

## §2 Why this slice (context for the subagent)

- PR #9 and PR #10 established L3 A/B and per-question diagnostics for the tight cohort (`c1s1_to_c1s3_v1`), and PR #11 added the `natural_v1` lane with one improvement and no regressions.
- We currently have symptom-level evidence but no mechanism-level readout for why alias augmentation helps `natural_v1` while hurting `c1s1/c1s3`; this slice converts existing committed artifacts into a falsifiable alias-saturation hypothesis surface.
- This slice intentionally does **not** change retrieval behavior, ranking logic, gold files, route-equivalence producer artifacts, prompts, or any default `--check*` baseline contracts.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** - §4 allowlist / §5 denylist / §7 verification contract.
2. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` - `execution_state.next_gate_command`, `external_pull_requests[]` rubric carry-forward, and PR #9/#10/#11 notes.
3. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` - Reanchor block and session-log wording around tight vs natural L3 outcomes.
4. `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` - canonical emitter shape and marker contract (`BEGIN/END GENERATED`).
5. `tests/test_cohort_l3_question_deep_dive_canvas_emit.py` - canonical emitter test style and custom input/output expectations.
6. `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json` and `.../cohort_l3_ab_question_delta_natural_v1.json` - committed input artifacts; source of truth for alias/rank-movement analysis.
7. `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json` and `.../cohort_l3_ab_delta_natural_v1.json` - scenario-level companion deltas for cross-check summaries.
8. **`tests/conftest.py`** - confirm env bootstrap expectations (`load_dungeonmindbuddy_dotenv()`).

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/sentence_routing_retrieval_falsification/cohort_l3_alias_saturation_canvas_emit.py` | New deterministic emitter that reads two question-delta artifacts and computes per-question alias-count + rank-movement evidence with threshold aggregates. |
| Create | `tests/test_cohort_l3_alias_saturation_canvas_emit.py` | Unit tests for deterministic aggregation, threshold analysis output shape, and generated marker contract. |
| Create | `canvases/cohort-l3-alias-saturation.canvas.tsx` | Generated analysis canvas with embedded payload from the committed artifacts. |
| Modify | `evals/sentence_routing_retrieval_falsification/README.md` | Add a short section documenting the new alias-saturation emitter command and output path. |

> Expected diff stat shape: **4 paths** exactly. If extra paths appear, revert them before opening the PR.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these. Concrete collision risks named alongside the path:

| Path | Why this PR must not touch it |
|---|---|
| `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Harness behavior already frozen by PR #9/#10/#11; changing it would confound diagnostics with retrieval-runner behavior changes. |
| `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` | Existing deep-dive canvas contract is already in active use; this slice should be additive via sibling emitter. |
| `tests/test_cohort_baseline_run.py` | Baseline/delta boundary tests are stable anchors; this slice should not alter them. |
| `tests/test_cohort_l3_question_deep_dive_canvas_emit.py` | Existing emitter tests must stay untouched to prove no regression to current diagnostic lane. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_*.json` | These are input anchors; editing them would rewrite evidence instead of analyzing it. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_*.json` | Scenario-level delta anchors for PR #9/#11; must remain immutable for comparability. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold/rubric edits are out of scope for a diagnostics-only PR. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/*.jsonl` | Producer artifacts are fixed inputs; mutating them invalidates A/B interpretation. |
| `src/agent/session_memory_query.py` | Retrieval/ranking behavior changes are explicitly out of scope. |
| `src/prompts/**` | Prompt-path changes are out of scope and would break retrieval-only attribution. |
| `Docs/Plans/**` (other than this handoff file) | Parent owns post-merge atomic doc-sync; worker must not pre-edit plan/checklist docs. |

If the worker thinks one of these is genuinely needed, it must stop and ask in the PR description before opening the PR.

## §6 Implementation contract

### §6.1 New sibling alias-saturation emitter

Create `cohort_l3_alias_saturation_canvas_emit.py` as a sibling module with CLI:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_alias_saturation_canvas_emit \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json \
  --output canvases/cohort-l3-alias-saturation.canvas.tsx
```

Required output payload (embedded in generated TSX constant):

```python
{
  "schema_id": "dmb_cohort_l3_alias_saturation_v1",
  "inputs": [<workspace-relative paths in CLI order>],
  "question_count": <int>,
  "verdict_counts": {"regressed": int, "improved": int, "unchanged_pass": int, "unchanged_fail": int},
  "rows": [
    {
      "scenario_id": str,
      "question_id": str,
      "verdict": str,  # from q["delta"]["verdict"]
      "alias_tokens_added": [str, ...],  # q["delta"]["tokens_added_by_equivalences"]
      "alias_count": int,  # len(alias_tokens_added)
      "topk_swapped_in": [str, ...],  # q["delta"]["topk_units_swapped_in"]
      "topk_swapped_out": [str, ...],  # q["delta"]["topk_units_swapped_out"]
      "contested_slot_unit_in": str | null,  # first entry in topk_swapped_in if present
      "contested_slot_unit_out": str | null,  # first entry in topk_swapped_out if present
      "support_ratio_delta": float,
    },
    ...
  ],
  "threshold_scan": [
    {
      "threshold_alias_count": int,
      "at_or_below": {"regressed": int, "improved": int, "unchanged_pass": int, "unchanged_fail": int},
      "above": {"regressed": int, "improved": int, "unchanged_pass": int, "unchanged_fail": int}
    },
    ...
  ],
  "promotion_gate_candidate": {
    "threshold_alias_count": int | null,
    "rule": "no_regressed_above_threshold_and_net_nonnegative_below",
    "status": "candidate_found" | "none_found"
  }
}
```

### §6.2 Determinism and rendering rules

- Preserve input artifact order exactly as passed by repeated `--input`.
- Preserve scenario and question iteration order as they appear in each input artifact.
- `threshold_scan` must be sorted by `threshold_alias_count` ascending from `0..max(alias_count)` inclusive.
- Generated canvas markers must exist and be stable:
  - `// BEGIN GENERATED COHORT_L3_ALIAS_SATURATION`
  - `// END GENERATED COHORT_L3_ALIAS_SATURATION`
- Canvas body must render:
  - verdict counts summary,
  - promotion-gate candidate status,
  - per-question rows for verdicts `regressed` and `unchanged_fail` (at minimum), including alias_count, tokens, and top-K contested units.

### §6.3 Legacy-path no-op expectation

- Existing deep-dive emitter remains unchanged and still passes its current tests.
- Existing baseline/question-delta artifacts remain byte-identical and untouched.

## §7 Verification commands

The worker must run **every** command and paste output into the PR body.

```bash
# 1) Existing surfaces still green (proves no regressions to current diagnostics lane).
uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py -q
uv run pytest tests/test_cohort_baseline_run.py -q

# 2) New emitter unit tests.
uv run pytest tests/test_cohort_l3_alias_saturation_canvas_emit.py -q

# 3) Emit alias-saturation canvas from committed artifacts (retrieval-only, no re-run).
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_alias_saturation_canvas_emit \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json \
  --output canvases/cohort-l3-alias-saturation.canvas.tsx

# 4) Marker + schema smoke from generated file.
uv run python -c "from pathlib import Path; import re, json; p=Path('canvases/cohort-l3-alias-saturation.canvas.tsx'); t=p.read_text(encoding='utf-8'); print('canvas_exists', p.exists()); print('has_generated_markers', 'BEGIN GENERATED COHORT_L3_ALIAS_SATURATION' in t and 'END GENERATED COHORT_L3_ALIAS_SATURATION' in t); m=re.search(r'const cohortL3AliasSaturationGenerated = (\\{.*?\\}) as const;', t, re.S); d=json.loads(m.group(1)); print('schema_id', d['schema_id']); print('question_count', d['question_count']); print('verdict_counts', d['verdict_counts']); print('promotion_gate_candidate', d['promotion_gate_candidate'])"

# 5) Retrieval-only evidence smoke from existing committed cohort summaries.
uv run python -c "import json; p='evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json'; d=json.load(open(p)); print('tight_llm_enabled', d.get('llm_enabled')); print('tight_retrieval_only', d.get('retrieval_only'))"
uv run python -c "import json; p='evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json'; d=json.load(open(p)); print('natural_llm_enabled', d.get('llm_enabled')); print('natural_retrieval_only', d.get('retrieval_only'))"
```

## §8 Reporting contract

In the PR body the worker MUST include:

1. `git diff --stat origin/main...HEAD` filtered to §4 allowlist paths only (exactly 4 rows).
2. Verbatim output for every §7 command.
3. One short "what stayed unchanged" paragraph that explicitly states:
   - no retrieval-core code changes,
   - no cohort baseline or question-delta artifact edits,
   - no gold edits,
   - no lexicon JSONL edits.
4. A short "hypothesis readout" paragraph from generated payload:
   - `verdict_counts`,
   - whether `promotion_gate_candidate.status` is `candidate_found` or `none_found`,
   - one regressed/unchanged_fail row and one improved row excerpt with `alias_count` and `contested_slot_unit_*`.

## §9 Acceptance rubric

The reviewer will accept ONLY if every bullet below is true.

- [ ] New alias-saturation emitter produces a deterministic generated canvas with stable markers and schema `dmb_cohort_l3_alias_saturation_v1` - verified by §7 #3 and #4.
- [ ] Per-question rows include alias contribution (`tokens_added_by_equivalences`/`alias_count`) and top-K contested-slot movement (`topk_units_swapped_in/out`) for at least regressed + unchanged_fail questions - verified by §7 #2 and #4.
- [ ] Threshold aggregate surface (`threshold_scan`) and promotion gate candidate status are emitted from both committed question-delta artifacts in one run - verified by §7 #3 and #4.
- [ ] Legacy diagnostic boundary remains intact (existing deep-dive emitter and cohort baseline tests still green) - verified by §7 #1.
- [ ] Retrieval-only invariant holds (`llm_enabled: false`, `retrieval_only: true` in both committed cohort summary inputs) - verified by §7 #5.
- [ ] No files outside §4 are touched - verified by filtered diff-stat.

> Reviewer reminder: rubric bullets claiming boundary behavior must be proven by emitted payload + boundary smoke, not only helper-level unit assertions.

## §10 Out-of-band notes (optional)

- Keep this slice measurement-only: do not add runtime alias caps, weighting changes, or retrieval default flips.
- If no threshold satisfies the candidate rule, that is a valid and expected output (`promotion_gate_candidate.status = "none_found"`), not a failure to be patched around.
- Post-merge doc-sync should carry forward one rubric bullet about requiring aggregate threshold evidence before any future default-flip proposal.

---

**End of handoff.** Dispatcher next step after PR opens:
`uv run python scripts/review_external_pr.py fetch 12 --handoff Docs/Plans/HANDOFF-pr12-alias-saturation-analysis-promotion-gate.md --extract-rubric`
