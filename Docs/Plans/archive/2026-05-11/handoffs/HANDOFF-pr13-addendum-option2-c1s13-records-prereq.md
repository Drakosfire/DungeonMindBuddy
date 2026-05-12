> **COMPLETED:** This addendum authored **Option 2**: prerequisite **records-meta** ingest artifacts land in **[PR #14](https://github.com/Drakosfire/DungeonMindBuddy/pull/14)** (**merge `3e1f32a551b3600f77531a0708da18e89a1e5bd1`**, **`2026-05-12T00:22:14Z`**) **before** holdout regeneration merged as **[PR #13](https://github.com/Drakosfire/DungeonMindBuddy/pull/13)** (**merge `761bd007af6e47210dc69a1a60b8afc42c751822`**, **`2026-05-12T00:48:43Z`**). Stage **4b** moved this markdown from `Docs/Plans/` to `Docs/Plans/archive/2026-05-11/handoffs/` for lineage only.

# HANDOFF ADDENDUM — Option 2 prerequisite for PR #13 (`c1s13_v1` holdout cohort)

**Created:** 2026-05-11 (UTC)  
**Applies to:** `HANDOFF-pr13-c1s13-holdout-cohort-ab-baseline-and-deltas.md` (archived sibling in this folder)  
**Status:** **ARCHIVED — prerequisite satisfied via PR #14; PR #13 merged**  
**Reason (historical):** PR #13 §7 blocked until `evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.jsonl` existed on `main`; **resolved** prior to **PR #13** integration.

---

## Decision

Use **Option 2**:

1. Land/provide the missing C1S13 records input in a **separate prerequisite slice/PR**.
2. Then resume PR #13 unchanged and generate the 5 allowlist outputs from the original handoff.

This preserves clean scope boundaries:

- prerequisite PR = input existence,
- PR #13 = holdout manifest + baseline/deltas/canvas evidence.

---

## What changes right now

- ~~PR #13 remains **REQUEST_CHANGES** until prerequisite input exists.~~ (**Obsolete:** **PR #14** + **PR #13** are **merged**.)
- ~~Do **not** merge manifest-only PR #13.~~ (**Obsolete.**)
- Do **not** silently repoint `records_jsonl` to a dated `artifacts/runs/...` file. (**Standing anti-pattern.**)

---

## Prerequisite slice requirements (new PR)

Create/commit:

- `evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.jsonl`

Also include its companion metadata json (same convention as c1s2/c1s3/c2s20):

- `evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.json`

Constraints:

- Retrieval-only source path (no prompt/retrieval code changes).
- Keep schema/shape consistent with existing committed `*.records_meta.jsonl` cohort inputs.
- No edits to gold, runner logic, or PR #13 target artifacts in this prerequisite PR.

---

## Resume protocol for PR #13 after prerequisite lands

(**Executed:** prerequisites merged **`2026-05-12T00:22:14Z`**; holdout **`2026-05-12T00:48:43Z`**.)

Re-run the original PR #13 §7 commands verbatim. Expected outputs to newly appear:

- `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json`
- `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json`
- `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json`
- `canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx`

Allowlist for PR #13 must then be exactly 5 paths as already defined in the original handoff.

---

## Reporting requirement (carry-forward caveat)

When PR #13 is resumed, keep this caveat explicit in the PR body:

`unchanged_fail` rows in `c1s13_v1` may reflect gold-quality artifacts (known C1S13 hierarchy-content risk), not confirmed retrieval failures, until the gold audit lands.

---

## Dispatcher note

Once the prerequisite PR merges, run:

`uv run python scripts/review_external_pr.py verify 13 --handoff Docs/Plans/archive/2026-05-11/handoffs/HANDOFF-pr13-c1s13-holdout-cohort-ab-baseline-and-deltas.md --parse-counts`

Then continue the normal external-agent loop for PR #13.

**Post-merge reminder:** authoritative handoffs for this sequencing now live under `Docs/Plans/archive/2026-05-11/handoffs/`; use **`PLAN-split-corpus-retrieval-to-autonomous-demo.md`** `external_pull_requests` for judgment/rubric lineage.
