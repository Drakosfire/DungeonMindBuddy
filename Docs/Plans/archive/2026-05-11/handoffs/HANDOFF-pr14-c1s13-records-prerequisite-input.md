---
pr_body_template: |
  ## Summary
  Add the missing C1S13 records input artifacts required to unblock PR #13 holdout cohort generation.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

> **COMPLETED:** [PR #14](https://github.com/Drakosfire/DungeonMindBuddy/pull/14) merged 2026-05-12T00:22:14Z (merge `3e1f32a551b3600f77531a0708da18e89a1e5bd1`, PR head `4cc593429417ac0f457e7ba10583065069891fbd`; review **`COMMENTED`**, id **`4268310498`**). Stage 4b atomic doc-sync: PLAN v20 (`github-pr-14`), CHECKLIST PR history / Reanchor / session log, `archive/2026-05-11/README.md`, and this archival copy. Probe facts archived: **`rows`/`unit_count` 68**, **`records_with_routes` 0**, **`size_bytes` 31286** — two artifact files only; **$0**.

# HANDOFF - PR #14: C1S13 records prerequisite input for PR #13

**Created:** 2026-05-12 (UTC).  
**Status:** COMPLETED — merged via [PR #14](https://github.com/Drakosfire/DungeonMindBuddy/pull/14) on 2026-05-12T00:22:14Z (merge commit `3e1f32a551b3600f77531a0708da18e89a1e5bd1`). Round 1: APPROVE requested, posted **`COMMENTED`** (self‑review fallback, review id **`4268310498`**).  
**Parent agent:** Cursor agent (external-agent PR loop).  
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`). This slice is a prerequisite unblocker for PR #13, not a retrieval behavior change.

---

## §1 Mission

Commit the missing C1S13 records input artifacts so PR #13 can generate and freeze its holdout baseline/delta/question-delta/canvas outputs.

## §2 Why this slice (context for the subagent)

- PR #13 failed §7 because `evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.jsonl` was absent.
- This PR is the Option-2 prerequisite from `HANDOFF-pr13-addendum-option2-c1s13-records-prereq.md`.
- Scope is input-only: no cohort artifacts, no retrieval code, no gold updates.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. `.cursor/rules/external-agent-pr-loop.mdc`
2. `Docs/Plans/HANDOFF-pr13-addendum-option2-c1s13-records-prereq.md`
3. `Docs/Plans/HANDOFF-pr13-c1s13-holdout-cohort-ab-baseline-and-deltas.md`
4. Existing input patterns:
   - `evals/sentence_routing_retrieval_falsification/artifacts/c1s2_norm_smoke.records_meta.jsonl`
   - `evals/sentence_routing_retrieval_falsification/artifacts/c1s2_norm_smoke.records_meta.json`
   - `evals/sentence_routing_retrieval_falsification/artifacts/c1s3_norm_smoke.records_meta.jsonl`
   - `evals/sentence_routing_retrieval_falsification/artifacts/c1s3_norm_smoke.records_meta.json`

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.jsonl` | Missing records input required by `cohorts/c1s13_v1.json` in PR #13. |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.json` | Companion metadata summary for the records input (same convention as c1s2/c1s3/c2s20). |

> Expected diff stat shape: exactly 2 files.

## §5 Files explicitly OUT OF SCOPE (denylist)

| Path | Why this PR must not touch it |
|---|---|
| `evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json` | Belongs to PR #13 scope; this PR is prerequisite input only. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_*c1s13_v1.json` | Those are PR #13 outputs; keep slices separated. |
| `canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx` | PR #13 output; not part of prerequisite input slice. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json` | Gold remains unchanged in this prerequisite slice. |
| `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | No runner behavior changes in this PR. |
| `Docs/Plans/**` | Parent handles doc-sync after merge. |

## §6 Implementation contract

- `c1s13_norm_smoke.records_meta.jsonl` must be valid JSONL, non-empty, and shaped compatibly with existing `*.records_meta.jsonl` cohort inputs.
- `c1s13_norm_smoke.records_meta.json` must include expected summary keys and must reference the new `.records_meta.jsonl` path.
- No additional normalization pipeline or harness logic changes in this PR.

## §7 Verification commands

```bash
# 1) JSON summary parses and points to the new JSONL.
uv run python -c "import json; from pathlib import Path; p=Path('evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.json'); d=json.loads(p.read_text()); print('source_recap_path', d.get('source_recap_path')); print('campaign_id', d.get('campaign_id')); print('session_number', d.get('session_number')); print('unit_count', d.get('unit_count')); print('records_with_routes', d.get('records_with_routes'))"

# 2) JSONL file exists, parses line-by-line, and has at least one row.
uv run python -c "import json; from pathlib import Path; p=Path('evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.jsonl'); rows=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]; print('rows', len(rows)); print('first_keys', sorted(rows[0].keys())[:12] if rows else []); print('has_routes_field', 'routes' in rows[0] if rows else False)"

# 3) PR #13 blocker path now exists at expected location.
uv run python -c "from pathlib import Path; p=Path('evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.jsonl'); print('exists', p.exists()); print('size_bytes', p.stat().st_size if p.exists() else -1)"
```

## §8 Reporting contract

PR body must include:
1. `git diff --stat` filtered to the 2 allowlist files only.
2. Verbatim §7 command output.
3. One paragraph explicitly stating this PR only unblocks missing input and does **not** deliver PR #13 baseline/delta/canvas outputs.

## §9 Acceptance rubric

- [x] Exactly the two §4 files are changed and no extras.
- [x] Both files parse and align with existing `*_norm_smoke.records_meta.*` conventions.
- [x] Missing-path blocker for PR #13 is resolved (`c1s13_norm_smoke.records_meta.jsonl` exists at expected path).
- [x] Scope remains prerequisite-only (no cohort artifacts, no code/gold/prompt edits).
