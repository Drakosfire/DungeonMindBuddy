---
# Optional workflow contract: literal markdown the worker pastes into the
# GitHub PR description.
pr_body_template: |
  ## Summary
  Implement the route-equivalence alias safety baseline: compact entity aliases only, no structural route tokens, no manifest-wide alias injection, conservative query-text activation, and refreshed deterministic cohort artifacts.

  ## Verification (verbatim §7)
  Worker: paste §7 command outputs here before opening the PR.

  ## `git diff --stat` (§4 paths only)
  ```text
  Worker: paste allowlisted diff stat here before opening the PR.
  ```
---

> **COMPLETED — merged to `main`:** 2026-05-13T16:43:34Z — merge commit **`64b7546dbf72bed6feb911408c7f28cec2d008fd`**. Verified PR head **`1de5524e08b2f3b697794c6162a3b7a37e957c86`**. Round 2 closed structural-token leak in compact route-id aliases. Post-merge atomic doc-sync: PLAN v29, CHECKLIST Reanchor + session log, archive index — parent agent.

# HANDOFF — Equivalence Alias Safety Baseline

**Created:** 2026-05-13 (UTC).
**Status:** MERGED — PR [#22](https://github.com/Drakosfire/DungeonMindBuddy/pull/22); handoff archived as `HANDOFF-pr22-equivalence-alias-safety-baseline.md`.
**Parent agent:** Cursor agent; dispatcher is responsible for post-merge atomic doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, `M2: in_progress`, `M3: complete`, `M4: not_started`). This handoff is the safety slice after the C1S13 equivalence interrogation; it should stop equivalence from hurting before a later slice tries to make equivalence more powerful.

---

## §1 Mission

Implement a conservative, gold-free route-equivalence alias activation contract:

- extract compact entity aliases only,
- assert no structural route tokens enter query aliases,
- do not append every manifest alias to every question,
- activate aliases only when the natural query text mentions the entity,
- refresh deterministic cohort artifacts for the promoted/default equivalence lane.

This closes the current regression class without attempting a broader first-pass evidence design.

## §2 Why this slice

The C1S13 holdout falsified the current promoted equivalence default:

- committed C1S13 question delta: `regressed: 4`, `improved: 2`, `unchanged_pass: 12`, `unchanged_fail: 7`
- per-scenario pass counts: legacy baseline `16`, with-equivalence `14`
- dominant bucket: `ranking_regression: 8`

The parent investigation measured four temporary retrieval-only probes:

1. **Current committed behavior reproduced exactly.**
   - C1S13 stayed `16 -> 14`, with `regressed: 4`, `improved: 2`.
2. **C1-only equivalence manifest did not change C1S13.**
   - Removing C2 route-equivalence JSONL did not move the readout.
   - Cross-campaign Dustwalker contamination is not the primary mechanism.
3. **Final-segment aliases helped only partly.**
   - Structural tokens disappeared (`route`, `longmont`, `npc`, `elderwyld`), and one C1S13 regression (`covert_ops_meat_check`) recovered.
   - But C1S13 still stayed `16 -> 14`.
   - Natural cohort regressed `7 -> 5`.
4. **Query-text-gated compact aliases were the first clean safety baseline.**
   - C1S13: `16 -> 16`, `regressed: 0`, `improved: 0`, `unchanged_pass: 16`, `unchanged_fail: 9`
   - Tight cohort: `44 -> 44`, `regressed: 0`, `improved: 0`
   - Natural cohort: `7 -> 7`, `regressed: 0`, `improved: 0`

Important nuance: query-text activation mostly makes equivalence stop hurting; it does not yet make equivalence materially help. A later PR can design a stronger gold-free activation signal. Do not attempt that here.

## §3 Authoritative inputs

Read these before writing code:

1. `.cursor/rules/external-agent-pr-loop.mdc` — non-negotiable §4 allowlist / §5 denylist / §7 verification contract.
2. `.cursor/rules/anti-oracle-leakage.mdc` — the alias activation rule must not use benchmark gold, expected answers, expected route substrings, must-hit tokens, or grader internals.
3. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — current Phase B state and full invariant gate.
4. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` — Reanchor block and C1S13/PR #19 evidence.
5. `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`
   - `_slug_from_route`
   - `_build_equivalence_aliases`
   - `if args.use_route_equivalence_for_ranking and route_equivalence_records`
6. `src/agent/session_memory_query.py`
   - `_tokenize_query`
   - `_score_record`
   - `query_session_memory_candidate` trace behavior
7. `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` — harness-boundary subprocess tests for route-equivalence ranking.
8. `tests/test_cohort_baseline_run.py` — cohort baseline/delta/question-delta checks.
9. Route-equivalence artifacts:
   - `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl`
   - `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl`
10. Cohort manifests:
   - `evals/sentence_routing_retrieval_falsification/cohorts/c1s1_to_c1s3_v1.json`
   - `evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json`
   - `evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json`

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Implement compact entity alias extraction and conservative query-text-gated alias activation at the harness boundary. |
| Modify | `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | Add harness-boundary subprocess tests proving compact/no-structural/no-global alias behavior. |
| Modify | `tests/test_cohort_baseline_run.py` | Add or update cohort regression coverage for the safety-baseline readouts and artifact checks. |
| Modify | `evals/sentence_routing_retrieval_falsification/README.md` | Document the safety-baseline semantics for route-equivalence ranking, including that it is conservative and query-text activated. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s1_to_c1s3_v2.json` | Refresh promoted/default equivalence baseline for the tight cohort. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json` | Refresh promoted/default equivalence baseline for the natural cohort. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json` | Refresh promoted/default equivalence baseline for the C1S13 holdout. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s1_to_c1s3_v1.json` | Refresh L3 scenario delta for tight cohort. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_natural_v1.json` | Refresh L3 scenario delta for natural cohort. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json` | Refresh L3 scenario delta for C1S13. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json` | Refresh L3 question-delta for tight cohort. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json` | Refresh L3 question-delta for natural cohort. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json` | Refresh L3 question-delta for C1S13. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_scenario_report_c1s13_v1_baseline.json` | Refresh C1S13 holdout scenario report if the existing generator/check path rewrites it. |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_scenario_report_c1s13_v1_equivalence.json` | Refresh C1S13 holdout scenario report if the existing generator/check path rewrites it. |
| Modify | `canvases/cohort-l3-ab-question-deep-dive.canvas.tsx` | Regenerate only if question-delta refresh makes the committed canvas stale under existing emitter behavior. |
| Modify | `canvases/cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx` | Regenerate only if question-delta refresh makes the committed canvas stale under existing emitter behavior. |
| Modify | `canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx` | Regenerate only if question-delta refresh makes the committed canvas stale under existing emitter behavior. |

> Expected diff stat shape: code/test/doc plus refreshed deterministic artifacts above. If any file outside this table changes, revert it before opening the PR or stop and explain why the allowlist needs revision.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these:

| Path | Why this PR must not touch it |
|---|---|
| `src/agent/session_memory_query.py` | Ranker scoring and tokenizer internals are not the first fix. The measured issue is alias activation scope at the harness boundary. |
| `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/**` | Route-equivalence producer artifacts are inputs; do not mutate them to simulate behavior. |
| `src/lexicon_phase_b/**` | Producer/schema changes are not required for this safety slice. |
| `tests/lexicon_phase_b/**` | Producer tests are out of scope unless a failing import requires a mechanical update; if so, stop and ask. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold/rubric edits are forbidden in this PR. |
| `evals/sentence_routing_retrieval_falsification/cohorts/**` | Cohort manifests are stable inputs. Do not remove the C2 equivalence JSONL from manifests. |
| `evals/sentence_routing_retrieval_falsification/cohort_l3_question_deep_dive_canvas_emit.py` | Canvas presentation changes are separate. Regeneration is allowed only via existing emitter behavior. |
| `evals/sentence_routing_retrieval_falsification/c1s13_holdout_l3_deep_dive_canvas_emit.py` | Holdout-payload presentation changes are separate. |
| `.cursor/**` | Do not include local rule/skill experiments or Cursor metadata. |
| `Docs/Plans/**` except this handoff | Post-merge doc-sync belongs to the parent after merge, not the worker PR. |
| `corpus/**` | Corpus content is not part of this deterministic harness safety fix. |

If a denylisted file appears necessary, stop and report the blocker in the PR body before proceeding.

## §6 Implementation contract

### §6.1 Compact aliases only

Replace the current route-string alias behavior with compact entity aliases.

Current bad behavior:

```python
_slug_from_route("route:longmont-c1:npc:torbin-jove")
# "route:longmont c1:npc:torbin jove"
```

Required behavior:

```python
compact_aliases_for_record(Captain Lysandra Ironveil)
# includes compact entity handles like "captain lysandra ironveil"
# may include display-name/final-segment variants if useful
# must not include route IDs or route-structural words

compact_aliases_for_record(Torbin Jove)
# includes "torbin jove"
```

The exact helper names may differ, but tests must prove:

- colon-delimited route IDs yield only final entity handles,
- slash-delimited route paths still yield only final entity handles,
- hyphens/underscores normalize to spaces,
- blank malformed route IDs do not produce structural aliases,
- aliases never introduce `route`, `longmont`, `elderwyld`, `npc`, `campaign`, `c1`, or `c2` as alias-derived query tokens.

### §6.2 No global alias injection

Do not append all route-equivalence aliases to every query.

Activation rule for this PR:

- Compute the natural query text from the merged scenario (`query_spec.query` or `question`).
- Tokenize that text with the same broad shape as `_tokenize_query` / `_tokens` (`[a-z0-9]+`, lowercased).
- For each route-equivalence record, compute compact alias/display-name tokens.
- Activate that record only when the query text already contains at least one token from that record.
- When active, append only that record's compact aliases to `query_spec.query_token_aliases`.

Examples:

- A query mentioning `Torbin` may activate the `Torbin Jove` record and add `jove`.
- A query mentioning `Jove` may activate the same record and add `torbin`.
- A query mentioning `Lysandra` or `Captain` may activate `Captain Lysandra Ironveil`.
- A query that does not mention Lysandra/Torbin/Dustwalker must not receive their aliases.

This is intentionally conservative. Do not add first-pass-route activation in this PR. The parent probe showed a naive first-pass-route gate still regressed C1S13 and natural.

### §6.3 Gold-free only

Alias activation must not read or depend on:

- `expected_answer`,
- `must_hit_tokens`,
- `expect_route_substrings`,
- `location_hierarchy_equivalences`,
- `min_context_support_ratio`,
- grader verdicts or failure buckets.

It may use only:

- natural query text,
- loaded route-equivalence records,
- existing non-gold query spec fields needed to run retrieval.

### §6.4 Trace/report observability

Preserve or improve observability so tests and reviewers can see what happened.

At minimum, the existing `full_result.trace.query_tokens` must show only activated compact alias tokens. If a more explicit field is easier, add a deterministic trace/report field such as:

```json
"route_equivalence_aliases_for_ranking": ["torbin jove"]
```

or

```json
"query_token_aliases": ["torbin jove"]
```

Do not add corpus text, gold, or private answer data to the trace.

### §6.5 Expected deterministic readouts

After the safety baseline, the refreshed question-delta summaries should match the parent probe unless implementation details intentionally differ and are justified in the PR body.

Expected safety-baseline readouts:

| Cohort | Expected summary | Expected pass counts |
|---|---|---|
| tight `c1s1_to_c1s3_v1` | `regressed: 0`, `improved: 0`, `unchanged_pass: 44`, `unchanged_fail: 0` | `16 -> 16`, `15 -> 15`, `13 -> 13` |
| natural `natural_v1` | `regressed: 0`, `improved: 0`, `unchanged_pass: 7`, `unchanged_fail: 5` | `7 -> 7` |
| C1S13 `c1s13_v1` | `regressed: 0`, `improved: 0`, `unchanged_pass: 16`, `unchanged_fail: 9` | `16 -> 16` |

If the readouts differ, do not hide it. Report the exact difference and why the implementation still satisfies the safety contract, or stop and ask for review.

## §7 Verification commands

Run all commands and paste outputs verbatim in the PR body.

```bash
# 1) Harness-boundary tests for route-equivalence ranking.
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q

# 2) Cohort runner tests, including safety-baseline summary/artifact checks.
uv run pytest tests/test_cohort_baseline_run.py -q

# 3) Refresh/check route-equivalence producer artifacts remain byte-stable.
uv run python scripts/build_route_equivalence_manifests.py --check

# 4) Regenerate/check tight cohort promoted/default baseline + L3 artifacts.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --write
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-delta
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-question-delta

# 5) Regenerate/check natural cohort promoted/default baseline + L3 artifacts.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json \
  --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json \
  --write
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

# 6) Regenerate/check C1S13 promoted/default baseline + L3 artifacts.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json \
  --write
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

# 7) Print compact safety readouts from refreshed question deltas.
uv run python - <<'PY'
import json
from pathlib import Path
paths = [
    Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json"),
    Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json"),
    Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json"),
]
for p in paths:
    d = json.loads(p.read_text(encoding="utf-8"))
    print(p.name, "summary", d["summary"], "failure", d["failure_diagnostic_summary"])
    for scen in d["scenarios"]:
        print(" ", scen["scenario_id"], scen["baseline_pass_count"], "->", scen["with_equivalence_pass_count"])
    changed = [
        (q["question_id"], q["delta"]["verdict"], q["delta"]["tokens_added_by_equivalences"])
        for scen in d["scenarios"]
        for q in scen["questions"]
        if q["delta"]["verdict"] in {"regressed", "improved"}
    ]
    print(" changed", changed)
PY
```

If the PR regenerates canvases because the JSON artifacts changed, also run:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json \
  --output canvases/cohort-l3-ab-question-deep-dive-natural-v1.canvas.tsx
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json \
  --output canvases/cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx
uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py -q
```

## §8 Reporting contract

PR body must include:

1. `git diff --stat origin/main...HEAD` filtered to §4 paths only.
2. Verbatim output for all §7 commands.
3. A compact readout table for tight, natural, and C1S13:
   - `summary`
   - `failure_diagnostic_summary`
   - baseline pass count vs with-equivalence pass count
   - changed rows (`regressed` / `improved`) after the safety baseline
4. One paragraph explaining what changed:
   - compact aliases only,
   - no structural route tokens,
   - query-text-gated activation,
   - no first-pass-route activation.
5. One paragraph "what stayed unchanged":
   - no gold changed,
   - no cohort manifests changed,
   - no route-equivalence artifacts changed,
   - no ranker/scoring changes in `src/agent/session_memory_query.py`,
   - no corpus content changed.
6. Cost statement: `$0`; all commands are retrieval-only/local deterministic checks with no LLM calls.

## §9 Acceptance rubric

- [ ] Route-equivalence ranking no longer introduces structural alias-derived query tokens (`route`, `longmont`, `elderwyld`, `npc`, `campaign`, `c1`, `c2`) — verified by harness-boundary tests in §7 #1 and printed readouts in §7 #7.
- [ ] Route-equivalence aliases are compact entity handles derived from display names and/or final route segments, not full route IDs — verified by §7 #1.
- [ ] Aliases are not appended globally to every query; an unrelated query receives no Lysandra/Torbin/Dustwalker aliases unless its natural query text mentions that entity — verified by §7 #1 and §7 #7.
- [ ] Alias activation is gold-free: implementation does not read expected answers, must-hit tokens, expected route substrings, hierarchy equivalences, support thresholds, or grader verdicts to decide which aliases to add — verified by source review of `breadcrumb_query_run.py`.
- [ ] Naive first-pass-route activation is not implemented in this PR — verified by source review and PR narrative.
- [ ] Tight cohort has no L3 regressions after refresh (`regressed: 0`, `improved: 0`, `unchanged_pass: 44`, `unchanged_fail: 0`) — verified by §7 #4 and #7.
- [ ] Natural cohort has no L3 regressions after refresh (`regressed: 0`, `improved: 0`, `unchanged_pass: 7`, `unchanged_fail: 5`) — verified by §7 #5 and #7.
- [ ] C1S13 has no L3 regressions after refresh (`regressed: 0`, `improved: 0`, `unchanged_pass: 16`, `unchanged_fail: 9`; pass count `16 -> 16`) — verified by §7 #6 and #7.
- [ ] Route-equivalence producer artifacts remain byte-stable — verified by §7 #3.
- [ ] No files outside §4 are touched — verified by allowlisted diff stat.
- [ ] Cost remains `$0`; no LLM/eval API calls are introduced — verified by §7 command set and PR diff.

## §10 Explicit non-goals

- Do not make equivalence more powerful in this PR. The measured query-text gate is a safety baseline; it removes regressions but also removes observed equivalence wins.
- Do not implement first-pass-route activation. The parent probe showed the naive version still regressed C1S13 and natural.
- Do not tune `_score_record` route-token weights.
- Do not edit gold to make the new readouts look better.
- Do not remove C2 route-equivalence JSONL from manifests.
- Do not conflate this safety baseline with production promotion of alias saturation or broader retrieval acceptance criteria. The parent still needs to judge the next baseline after this lands.
