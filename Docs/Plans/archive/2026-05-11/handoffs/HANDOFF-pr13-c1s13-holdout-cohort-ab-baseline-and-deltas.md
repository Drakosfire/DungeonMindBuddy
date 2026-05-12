---
pr_body_template: |
  ## Summary
  Add a C1 holdout cohort (`c1s13_v1`) with frozen baseline, scenario delta, per-question delta, and deep-dive canvas so we can test whether L3 regression/improvement behavior generalizes beyond current C2-heavy lanes.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

> **COMPLETED:** [PR #13](https://github.com/Drakosfire/DungeonMindBuddy/pull/13) merged **`2026-05-12T00:48:43Z`** (merge commit **`761bd007af6e47210dc69a1a60b8afc42c751822`**; verified head **`fd8c4c6d1affbaa3f8dc45c3ee4c729ee2f228c5`**).
> Review: **`APPROVE`** expressed as **`COMMENTED`** under self‑review fallback (review id **`4268385088`**). Stage **4b** doc-sync: PLAN **v21** + CHECKLIST fifteenth Session Log entry + **`github-pr-13`** judgment.
> Prerequisites: **`HANDOFF-pr13-addendum-option2-c1s13-records-prereq`** (**Option 2**) fulfilled by **[PR #14](https://github.com/Drakosfire/DungeonMindBuddy/pull/14)** (`c1s13_norm_smoke.records_meta.{jsonl,json}`).

# HANDOFF - PR #13: C1 holdout `c1s13_v1` cohort baseline + L3 deltas

**Created:** 2026-05-11 (UTC).
**Status:** **COMPLETED** — merged **[PR #13](https://github.com/Drakosfire/DungeonMindBuddy/pull/13)** **`2026-05-12T00:48:43Z`** (merge commit **`761bd007af6e47210dc69a1a60b8afc42c751822`**). Review id **`4268385088`** (COMMENTED self‑review fallback). §4 allowlist **5/5**; **`test_cohort_baseline_run`** **19 passed** / **`test_cohort_l3_question_deep_dive_canvas_emit`** **3 passed** at merged verification; **`c1s13_v1`** holdout **`question_count` 25** with **`unchanged_fail` 25** (carry **gold-quality** caveat forward).
**Parent agent:** Cursor agent; dispatcher owns post-merge atomic doc-sync (`CHECKLIST-dynamic-lexical-retrieval-rollout.md` + `PLAN-split-corpus-retrieval-to-autonomous-demo.md`).
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`; **PR #13** evidence captured under **`external_pull_requests.github-pr-13`**).

**Archive:** this file resides under `Docs/Plans/archive/2026-05-11/handoffs/` after Stage **4b** (no longer `Docs/Plans/HANDOFF-pr13-c1s13-holdout-cohort-ab-baseline-and-deltas.md`).

---

## §0 Re-anchor + risk caveat (must read before coding)

- **Dominant question this slice answers:** does the L3 regression/improvement pattern hold in a C1 holdout lane, or is the current split C2-specific?
- **Known caveat (load-bearing):** `Backlog.md` flags C1S13 `location_hierarchy_equivalences` content smell (possible copy-paste mappings). Treat this cohort as **measurement with caveat**, not promotion evidence by itself.
- **Interpretation rule for this PR:** `unchanged_fail` rows in `c1s13_v1` may be gold-quality artifacts rather than retrieval failures until the C1S13 hierarchy content audit lands. The worker must call this out in the PR body.

## §1 Mission

Create a new C1 holdout cohort manifest (`c1s13_v1`) plus frozen baseline, L3 scenario delta, L3 per-question delta, and deep-dive canvas artifacts using existing retrieval-only harness contracts without changing retrieval or grading code.

## §2 Why this slice (context for the subagent)

- PR #9/#10/#11/#12 established tight + natural A/B and alias-saturation evidence, but the practical A/B lanes remain C2-heavy for promotion decisioning.
- A C1 holdout cohort broadens the falsification surface before any default flip discussion, while preserving existing anchors untouched.
- This slice intentionally does **not** answer mechanism-level "why" (alias split cause), and it intentionally does **not** edit gold, retriever behavior, prompt text, or producer artifacts.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** - §4 allowlist / §5 denylist / §7 verification contract.
2. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` - current phase and post-PR #12 promotion-gate state.
3. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` - Reanchor block and current next-slice language.
4. `Backlog.md` entry: **[IDEA] C1S13 hierarchy content audit — copy-paste smell** (risk caveat to preserve in reporting).
5. `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` - canonical C1 manifest shape.
6. `evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json` - current widened-lane manifest shape.
7. `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json` - holdout gold target for this lane (read-only in this PR).
8. `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` - existing baseline/delta/question-delta writer/check contracts.
9. `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` - canvas emitter used for holdout output.
10. **`tests/conftest.py`** - confirm env bootstrap expectations (`load_dungeonmindbuddy_dotenv()`).

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json` | New C1 holdout cohort manifest (`campaign_id: longmont-c1`) targeting `breadcrumb_query_natural_c1s13_v1.json`. |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json` | Frozen retrieval-only holdout baseline summary (`dmb_breadcrumb_query_cohort_summary_v2`). |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json` | Frozen holdout scenario-level L3 A/B delta (`dmb_breadcrumb_query_cohort_l3_delta_v1`). |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json` | Frozen holdout per-question L3 A/B delta (`dmb_breadcrumb_query_cohort_l3_question_delta_v1`). |
| Create | `canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx` | Generated holdout deep-dive canvas from the new per-question delta artifact. |

> Expected diff stat shape: **5 paths** exactly. If extra paths appear, revert them before opening the PR.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these. Concrete collision risks named alongside the path:

| Path | Why this PR must not touch it |
|---|---|
| `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Runner behavior is already locked by prior PRs; this slice is artifact generation only. |
| `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` | Existing emitter contract is stable; use it, do not modify it. |
| `tests/test_cohort_baseline_run.py` | Stable contract tests for baseline/delta runners; untouched to avoid confounded evidence. |
| `tests/test_cohort_l3_question_deep_dive_canvas_emit.py` | Existing emitter tests should remain untouched; run-only verification. |
| `evals/sentence_routing_retrieval_falsification/README.md` | Collision risk from pre-flight: file already references `c1s13_v1`; doc edits would add review noise without moving holdout evidence. |
| `evals/sentence_routing_retrieval_falsification/c1s1_benchmark_canvas_emit.py` | Pre-flight surfaced this file as another `c1s13_v1` mention; it is unrelated historical canvas wiring and must not be "cleaned up" in this slice. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json` | Gold edits are explicitly out of scope; risk is noted, not fixed in this PR. |
| `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json` | Tight-cohort anchor must remain immutable. |
| `evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json` | Natural lane anchor must remain immutable. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` | Existing default check anchor must remain immutable. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json` | Existing widened lane anchor must remain immutable. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json` | Existing tight L3 scenario delta anchor must remain immutable. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_natural_v1.json` | Existing natural L3 scenario delta anchor must remain immutable. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json` | Existing tight question-delta anchor must remain immutable. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json` | Existing natural question-delta anchor must remain immutable. |
| `src/agent/session_memory_query.py` | Retrieval/ranking changes are out of scope for holdout measurement. |
| `src/prompts/**` | Prompt changes are out of scope and confound A/B interpretation. |
| `Docs/Plans/**` (other than this handoff file) | Parent owns post-merge atomic doc-sync. |

If the worker thinks one of these is genuinely needed, it must stop and ask in the PR description before opening the PR.

## §6 Implementation contract

### §6.1 Manifest contract (`c1s13_v1`)

Create `evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json` with:

```json
{
  "schema": "dmb_breadcrumb_query_cohort_manifest_v1",
  "cohort_id": "c1s13_v1",
  "campaign_id": "longmont-c1",
  "route_equivalence_jsonl": [
    "evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl",
    "evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl"
  ],
  "scenarios": [
    {
      "scenario_id": "c1s13",
      "gold": "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json",
      "records_jsonl": "evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.jsonl",
      "session_number": 13
    }
  ]
}
```

Include a notes field that explicitly records the C1S13 gold-quality caveat from §0.

### §6.2 Artifact generation contract

Use existing runner/emitter behavior only; no code edits.

- Generate holdout baseline JSON (`cohort_baseline_c1s13_v1.json`).
- Generate holdout scenario delta JSON (`cohort_l3_ab_delta_c1s13_v1.json`) via `--mode both --write-delta`.
- Generate holdout question delta JSON (`cohort_l3_ab_question_delta_c1s13_v1.json`) via `--write-question-delta`.
- Emit holdout deep-dive canvas from the new question delta JSON using existing emitter with `--input`/`--output`.

### §6.3 Determinism / compatibility

- New artifacts must pass `--check`, `--check-delta`, and `--check-question-delta`.
- Existing default/tight/natural baseline contracts must remain untouched and still pass their checks.
- `llm_enabled` must remain `false` and `retrieval_only` must remain `true` for the new holdout baseline.

## §7 Verification commands

The worker must run **every** command and paste output into the PR body.

```bash
# 1) Existing contracts still green.
uv run pytest tests/test_cohort_baseline_run.py -q
uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py -q

# 2) Generate holdout baseline + deltas.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json \
  --write

uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --mode both \
  --write-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json \
  --write-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json

# 3) Boundary checks for holdout artifacts.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json \
  --check

uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json \
  --check-delta

uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json

# 4) Emit holdout canvas + marker smoke.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json \
  --output canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx

uv run python -c "from pathlib import Path; import json; p=Path('canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx'); t=p.read_text(encoding='utf-8'); print('canvas_exists', p.exists()); print('has_generated_markers', 'BEGIN GENERATED' in t and 'END GENERATED' in t)"

# 5) Retrieval-only and holdout summary smoke (include caveat in PR prose).
uv run python -c "import json; p='evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json'; d=json.load(open(p)); print('schema', d.get('schema_id')); print('llm_enabled', d.get('llm_enabled')); print('retrieval_only', d.get('retrieval_only')); print('all_ok', d.get('aggregate',{}).get('all_scenarios_all_ok'))"
uv run python -c "import json; p='evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json'; d=json.load(open(p)); print('question_count', d.get('question_count')); print('summary', d.get('summary')); print('scenario_level_delta_path', d.get('scenario_level_delta_path'))"
```

## §8 Reporting contract

In the PR body the worker MUST include:

1. `git diff --stat origin/main...HEAD` filtered to §4 allowlist paths only (exactly 5 rows).
2. Verbatim output for every §7 command.
3. One short "what stayed unchanged" paragraph that explicitly states:
   - no retrieval-core code changes,
   - no gold file edits,
   - no existing tight/natural baseline or delta artifact edits,
   - no lexicon JSONL edits.
4. One explicit caveat paragraph:
   - quote that C1S13 `unchanged_fail` rows may represent gold-quality artifacts pending hierarchy-content audit,
   - do not frame those rows as confirmed retrieval regressions.

## §9 Acceptance rubric

The reviewer will accept ONLY if every bullet below is true.

- [x] New holdout manifest `c1s13_v1` is present, points at C1S13 gold + records, and carries the gold-quality caveat note — verified by §7 #2 and manifest inspection (**MERGED PR #13**).
- [x] Holdout baseline + scenario delta + question delta are all committed and pass check-mode reruns at the harness boundary — verified by §7 #3.
- [x] Holdout deep-dive canvas is generated deterministically with marker block present — verified by §7 #4.
- [x] Retrieval-only invariants hold on the new holdout baseline (`llm_enabled: false`, `retrieval_only: true`) — verified by §7 #5.
- [x] Scope remained artifact-only: no retrieval/prompt/gold/baseline-anchor codepath edits outside §4 — verified by filtered diff-stat / allowlist **5/5**.
- [x] PR reporting explicitly distinguishes possible gold-quality `unchanged_fail` rows from confirmed retrieval failures — verified in §8 narrative + PLAN rubric **`github-pr-13`.

> Reviewer reminder: every behavioral claim in this rubric is anchored to harness commands and committed artifacts, not inferred from unit-only checks.

## §10 Out-of-band notes (optional)

- This slice broadens where we measure; it does **not** explain why the flag splits (that remains alias/mechanism analysis).
- If `c1s13_norm_smoke.records_meta.jsonl` is missing, stop and report instead of substituting a different records file silently. (**Resolved** by prerequisite **PR #14** before merge of **PR #13**.)
- Post-merge doc-sync carried forward rubric bullets about caveated interpretation for known gold-quality-risk lanes (**PLAN `github-pr-13` `rubric_when_we_judge`**).

---

**End of handoff (archived post-merge).** Historical fetch path was `Docs/Plans/HANDOFF-pr13-c1s13-holdout-cohort-ab-baseline-and-deltas.md`; canonical archive copy lives here alongside other **2026-05-11** external-agent handoffs.
