---
pr_body_template: |
  ## Summary
  Audit and correct C1S13 `location_hierarchy_equivalences` mappings in gold so holdout failures can be interpreted as retrieval signal rather than rubric artifact.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

> **MERGED:** `main` @ `27b3eea7dd87331758ddd07e5919c5094f6702bd` (2026-05-12T01:32:31Z); review fallback id **`4268511628`**.

# HANDOFF - PR #15: C1S13 hierarchy gold audit (Wolf/Mossglade mapping correctness)

**Created:** 2026-05-12 (UTC).  
**Status:** COMPLETED — merged; atomic doc-sync archived this handoff.  
**Parent agent:** Cursor agent; parent handles post-merge atomic doc-sync.  
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, promotion still blocked).

---

## §1 Mission

Audit and fix incorrect `location_hierarchy_equivalences` entries in `breadcrumb_query_natural_c1s13_v1.json`, especially Wolf/Mossglade scenarios that currently point at Stormspire-family children.

## §2 Why this slice (context for the subagent)

- PR #13 holdout lane (`c1s13_v1`) produced `question_count: 25` with `unchanged_fail: 25`, which is uninterpretable while known C1S13 gold hierarchy mappings may be wrong.
- Backlog and checklist both flag copy-paste smell: two location-context scenarios appear to map Wolf/Mossglade parents to Stormspire descendants.
- This slice is rubric-quality repair, not retrieval tuning: no ranking/prompt/lexicon changes.

## §3 Authoritative inputs (read these in order)

1. `.cursor/rules/external-agent-pr-loop.mdc`
2. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` (Reanchor + flagged C1S13 hierarchy follow-up)
3. `Backlog.md` entry: `C1S13 hierarchy content audit`
4. `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json`
5. Corpus hierarchy references under  
   - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/`  
   - relevant Wolf/Mossglade subtrees the gold claims to represent
6. `scripts/audit_world_campaign_alignment.py` (structural guardrail; note it does not detect semantic mis-mapping)
7. `evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json`
8. `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` (for post-audit temp reruns)

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json` | Correct mis-mapped `location_hierarchy_equivalences` for C1S13 location scenarios. |

> Expected diff stat shape: exactly 1 file.

## §5 Files explicitly OUT OF SCOPE (denylist)

| Path | Why this PR must not touch it |
|---|---|
| `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Retrieval harness behavior must remain unchanged for attribution. |
| `evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json` | Holdout manifest is already merged and should stay stable. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_*c1s13_v1.json` | Frozen artifacts are downstream readouts; regenerate in a separate slice if needed. |
| `canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx` | Canvas refresh is downstream, not part of gold audit slice. |
| `src/agent/session_memory_query.py` | Retrieval/ranking code changes are out of scope. |
| `src/prompts/**` | Prompt edits would confound interpretation. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/*.jsonl` | Producer artifacts unrelated to this rubric correction. |
| `Docs/Plans/**` (except this handoff) | Parent does doc-sync post-merge. |

## §6 Implementation contract

- Edit only `location_hierarchy_equivalences` values that are demonstrably wrong against corpus tree semantics.
- For every changed parent key, ensure children are true descendants or justified location-family equivalents for that parent.
- Do not relax the benchmark by deleting expectations wholesale; replace wrong children with correct children.
- Preserve scenario IDs, question text, and non-location constraints unless they are directly invalidated by hierarchy correction.

## §7 Verification commands

```bash
# 1) Structural audit still passes (this is necessary but not sufficient).
uv run python scripts/audit_world_campaign_alignment.py

# 2) Gold parses and location_hierarchy_equivalences remain non-empty where expected.
uv run python -c "import json; p='evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json'; d=json.load(open(p)); print('schema', d.get('schema')); print('scenario_count', len(d.get('scenarios', []))); rows=[s for s in d.get('scenarios', []) if s.get('location_hierarchy_equivalences')]; print('with_location_hierarchy_equivalences', len(rows)); print('sample_ids', [r.get('id') for r in rows[:5]])"

# 3) Holdout rerun to TEMP outputs only (do not commit baselines in this PR).
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --mode both \
  --write-delta /tmp/c1s13_l3_delta_post_gold_audit.json \
  --write-question-delta /tmp/c1s13_l3_qdelta_post_gold_audit.json

# 4) Quick readout from temp rerun for PR narrative.
uv run python -c "import json; d=json.load(open('/tmp/c1s13_l3_qdelta_post_gold_audit.json')); print('question_count', d.get('question_count')); print('summary', d.get('summary')); print('scenario_level_delta_path', d.get('scenario_level_delta_path'))"
```

## §8 Reporting contract

PR body must include:
1. `git diff --stat` filtered to §4 allowlist (1 file).
2. Verbatim output from all §7 commands.
3. A concise “before vs after mapping” note listing each changed scenario id and the old/new parent→children rows.
4. Temp holdout rerun readout from `/tmp/c1s13_l3_qdelta_post_gold_audit.json`.

## §9 Acceptance rubric

- [ ] Only the C1S13 gold file changed (strict 1-file allowlist).
- [ ] Every hierarchy change is corpus-grounded (no stormspire children under Wolf/Mossglade unless explicitly justified by corpus structure).
- [ ] Structural alignment audit remains green after edits.
- [ ] Temp holdout rerun completed and is reported, so downstream PR can decide whether to regenerate frozen artifacts.
- [ ] No retrieval/prompt/manifest/lexicon codepath edits were introduced.

> Reviewer reminder: this slice improves rubric trustworthiness; it is not a retrieval improvement claim by itself.

## §10 Out-of-band notes (optional)

- If corpus evidence for a contested mapping is ambiguous, note it in PR body instead of guessing.
- If gold updates materially change holdout outcomes, open a follow-up PR to refresh frozen C1S13 baseline/delta/question-delta/canvas artifacts.

---

**End of handoff.** Dispatcher next step once PR opens:
`uv run python scripts/review_external_pr.py fetch 15 --handoff Docs/Plans/HANDOFF-pr15-c1s13-hierarchy-gold-audit.md --extract-rubric`
