# HANDOFF — Self-continuity: C1S13 equivalence interrogation and vertical-slice baseline

**Created:** 2026-05-13 (UTC).
**Status:** ACTIVE — start a fresh **prime** Cursor agent here. This is not an external-worker PR handoff.
**Parent context:** The current prime agent wrote this after the C1S13 holdout L3 canvas audit and after drafting two tactical external-agent handoffs (`PR #20` canvas presentation and `PR #21` question-delta path provenance).
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, `M1 complete`, `M2 in_progress`, `M3 complete`, `M4 not_started`).

---

## §0 Read This First

The next prime agent's job is **not** to immediately patch the equivalence pipeline. The job is to interrogate why the promoted equivalence default regresses C1S13 and to steer toward a **new trustworthy baseline** that merges the latest retrieval ideas and actually retrieves/answers the vertical-slice questions.

Core goal:

- Keep working toward the vertical slice: a deterministic, reviewable retrieval + answer path that can successfully answer the benchmark questions from discovered corpus context.
- Treat C1S13 as the current falsification holdout, but do not overfit or deflate the rubric.
- Follow `verify-before-debug.mdc`: inspect data/corpus/gold/prompt/grader before code, and treat benchmark/rubric correctness as a first-class question.

Current strongest hypothesis:

- The dominant C1S13 regression is a **manifest/harness scoping bug**, not a ranker bug.
- More specifically: `breadcrumb_query_run._build_equivalence_aliases()` appears to turn every route-equivalence record into unconditional query-token aliases for every question. Because route IDs are colon-delimited (`route:longmont-c1:npc:torbin-jove`) but `_slug_from_route()` only splits on `/`, aliases include the whole route ID. Tokenization then injects structural tokens (`route`, `longmont`, `npc`) plus NPC names (`captain`, `lysandra`, `ironveil`, `torbin`, `jove`, `dustwalker`) into every query.
- This matches the C1S13 question-delta rows: regressed rows show the same added-token set and top hits drifting toward Torbin/Lysandra/Dustwalker-route records.

Do **not** jump from that hypothesis to a code fix. Prove it with controlled retrieval-only experiments first.

---

## §1 Current Re-anchor

Canonical workstream sources:

- `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`
  - Active phase: `B`.
  - Last green artifact: PR #19 cohort default baseline promotion.
  - Open promotion-decision artifact: PR #12 `promotion_gate_candidate.status:none_found` (packaged alias-threshold scan had no candidate — not a failing committed cohort check); C1S13 holdout still has failures under falsification readouts.
  - Next fork in checklist: promotion acceptance criteria vs wider falsification cohorts vs further gold audit/normalization.
- `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`
  - `version: 26`
  - `active_phase: B`
  - `M2: in_progress`, `M3: complete`.
  - `next_gate_command` includes the tight, natural, and C1S13 cohort checks plus deep-dive canvas regeneration commands.
- Git re-anchor at handoff creation:
  - `HEAD d884d9331f654c95cc79a37dae6e45da0f9f68e3`
  - Short: `d884d93 eval: default-equivalence L3 canvases; holdout payload without legacy lane`
  - Branch: `main...origin/main`

Current untracked files at handoff creation:

- `Docs/Plans/HANDOFF-pr20-c1s13-l3-canvas-presentation.md`
- `Docs/Plans/HANDOFF-pr21-c1s13-question-delta-path.md`
- `.cursor/rules/benchmark-review-canvas-style.mdc`
- `.cursor/skills/benchmark-review-canvas/`
- `evals/sentence_routing_retrieval_falsification/artifacts/beat_boundary_experiment_c1s13_summary.json`
- `evals/sentence_routing_retrieval_falsification/artifacts/last_unit_annotations_c1s13_report.json`
- `evals/sentence_routing_retrieval_falsification/benchmark_review_canvas_template.py`
- `tests/test_benchmark_review_canvas_template.py`

Important: do not stage or modify unrelated untracked files unless the user explicitly asks.

---

## §2 Tactical Handoffs Already Written

Two separable external-agent handoffs now exist. They are tactical cleanup/support work, not the main prime-agent interrogation.

1. `Docs/Plans/HANDOFF-pr20-c1s13-l3-canvas-presentation.md`
   - Presentation-only.
   - Goal: make `cohort-l3-ab-question-deep-dive-c1s13-v1.canvas.tsx` actually render headline counts, failure buckets, support deltas, compact baseline-vs-default must-hit comparison, and open `unchanged_fail` rows.
   - Strict allowlist: shared L3 canvas emitter, its tests, and three generated canvases.
   - Does not touch retrieval, gold, artifacts, or scorer logic.

2. `Docs/Plans/HANDOFF-pr21-c1s13-question-delta-path.md`
   - Data-provenance-only.
   - Goal: fix `cohort_l3_ab_question_delta_c1s13_v1.json` so `scenario_level_delta_path` points at `cohort_l3_ab_delta_c1s13_v1.json` instead of the tight-cohort `cohort_l3_ab_delta_c1s1_to_c1s3_v1.json`.
   - Preferred robust fix: use manifest-specific effective delta path selection when `--delta` was not explicitly supplied.
   - Strict allowlist: `cohort_baseline_run.py`, `tests/test_cohort_baseline_run.py`, and the one C1S13 question-delta artifact.

These can be dispatched later via the external-agent PR loop. They should not distract from the substantive interrogation below.

---

## §3 Verified Evidence

### C1S13 holdout summary

Source: `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json`

Top-level readout:

```json
{
  "question_count": 25,
  "summary": {
    "regressed": 4,
    "improved": 2,
    "unchanged_pass": 12,
    "unchanged_fail": 7
  },
  "failure_diagnostic_summary": {
    "passed": 12,
    "equivalence_helped": 2,
    "ranking_regression": 8,
    "missing_lexical_handle": 0,
    "retriever_support_gap": 3,
    "gold_or_rubric_gap": 0
  }
}
```

Per-scenario:

- `scenario_id: c1s13`
- `baseline_pass_count: 16`
- `with_equivalence_pass_count: 14`

Interpretation:

- The promoted default equivalence lane is **-2 net pass** versus the legacy baseline on C1S13.
- The largest diagnostic bucket is `ranking_regression: 8`.
- Do not over-call `unchanged_fail`: `cohorts/c1s13_v1.json` explicitly warns that some `unchanged_fail` rows may reflect gold-quality artifacts pending hierarchy-content audit.
- The `regressed` rows are stronger evidence because they compare two deterministic retrieval lanes against the same gold and show equivalence made passing rows fail.

### C1S13 manifest caveat

Source: `evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json`

Key fields:

- `cohort_id: c1s13_v1`
- `notes`: C1S13 unchanged_fail rows may represent gold-quality artifacts; do not treat unchanged_fail as confirmed retrieval regressions in isolation.
- `route_equivalence_jsonl` includes **both**:
  - `route_equivalence_longmont_c1_v1.jsonl`
  - `route_equivalence_longmont_c2_v1.jsonl`
- The scenario records source is the corpus session-memory file for Session 13.

### Route-equivalence manifest shape

C1 route equivalence file:

- `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl`
- Contains two records:
  - `Captain Lysandra Ironveil`
  - `Torbin Jove`

C2 route equivalence file:

- `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl`
- Contains three records:
  - `Captain Lysandra Ironveil`
  - `Dustwalker`
  - `Torbin Jove`

Both files use route IDs shaped like:

```json
"from_route_id": "route:longmont-c1:npc:torbin-jove",
"to_route_id": "route:elderwyld:npc:torbin-jove"
```

### Alias-building mechanism

Source: `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`

Observed code shape:

```python
def _slug_from_route(route_id: str) -> str:
    part = route_id.rstrip("/").split("/")[-1].strip()
    return re.sub(r"[_-]+", " ", part).strip().lower()

def _build_equivalence_aliases(records: list[Any]) -> list[str]:
    seen: set[str] = set()
    aliases: list[str] = []
    for record in records:
        for route_id in (str(record.from_route_id), str(record.to_route_id)):
            slug = _slug_from_route(route_id)
            if slug and slug not in seen:
                seen.add(slug)
                aliases.append(slug)
    return aliases
```

Risk:

- `_slug_from_route()` splits only on `/`.
- Current route IDs are colon-delimited, so for `route:longmont-c1:npc:torbin-jove` the "slug" becomes the whole route ID normalized to `route:longmont c1:npc:torbin jove`.
- `src/agent/session_memory_query.py::_tokenize_query()` then tokenizes aliases into query tokens and appends them to every query's token set.

Observed alias expansion from the two JSONL files:

```text
route_equivalence_longmont_c1_v1.jsonl records 2 aliases [
  'route:longmont c1:npc:captain lysandra ironveil',
  'route:elderwyld:npc:captain lysandra ironveil',
  'route:longmont c1:npc:torbin jove',
  'route:elderwyld:npc:torbin jove'
]
route_equivalence_longmont_c2_v1.jsonl records 3 aliases [
  'route:longmont c2:npc:captain lysandra ironveil',
  'route:elderwyld:npc:captain lysandra ironveil',
  'route:longmont c2:npc:dustwalker',
  'route:elderwyld:npc:dustwalker',
  'route:longmont c2:npc:torbin jove',
  'route:elderwyld:npc:torbin jove'
]
```

This explains the repeated `tokens_added_by_equivalences` pattern in C1S13:

```text
captain, dustwalker, elderwyld, ironveil, jove, longmont, lysandra, npc, route, torbin
```

### Scoring mechanism

Source: `src/agent/session_memory_query.py`

Relevant behavior:

- `_tokenize_query()` appends all `query_token_aliases` tokens to the natural query tokens.
- `_score_record()` adds:
  - `+1` when a token appears in lexical text (`lexical_token:<token>`)
  - `+3` when a token appears in normalized routes (`route_token:<token>`)

Implication:

- Structural tokens like `route`, `longmont`, and `npc` are especially dangerous because route matches are weighted 3x lexical matches.
- A general `npc` / `longmont` route token can lift irrelevant NPC-route rows across many questions.

### Failure examples to keep in mind

From the compact summary command:

```text
covert_ops_meat_check regressed ranking_regression
  reasons ['equivalence_lost_required_must_hits', 'verdict_regressed']
  support_delta -0.4

stormspire_activity_arrival improved equivalence_helped
  reasons ['equivalence_mode_passed']
  support_delta 0.75

sleep_spell_chain_mechanical_prep regressed ranking_regression
  reasons ['equivalence_lost_context_support_ratio', 'equivalence_lost_required_must_hits', 'equivalence_lost_route_substrings', 'verdict_regressed']
  support_delta -0.7143
```

Interpretation:

- Equivalences can help when the natural query already strongly anchors to the right route/scene.
- Equivalences hurt when unconditional NPC/structural tokens outrank the actual scene evidence.

---

## §4 Current Working Hypotheses

### H1 — Most likely: alias builder parses route IDs incorrectly

`_slug_from_route()` assumes slash paths but receives colon route IDs. This injects structural tokens into every equivalence-augmented query.

Falsification:

- If a temporary alias-builder variant that extracts only the final route segment (`torbin-jove` -> `torbin jove`) removes most C1S13 ranking regressions without hurting tight/natural cohorts, H1 is strongly supported.

### H2 — Also likely: aliases are globally applied instead of query-gated

Even if `_slug_from_route()` is fixed, aliases for every route-equivalence record are still appended to every query in a manifest. C1S13 uses both C1 and C2 equivalence JSONL files; C2-only `Dustwalker` can enter C1 queries.

Falsification:

- If final-segment-only aliases still regress C1S13, test query-gated aliases:
  - only add aliases when the natural question already mentions a related display-name token, route substring, or gold-free first-pass signal.
  - Do **not** use expected answer, must-hit tokens, or expected routes to gate aliases; that would leak gold into retrieval.

### H3 — Less likely as primary: ranker weighting is bad

Route-token weighting (`+3`) amplifies the pollution, but the root issue appears to be the token set being polluted. Do not tune weights until H1/H2 are measured.

### H4 — Gold/rubric still matters for `unchanged_fail`

The manifest explicitly warns not to over-interpret `unchanged_fail`. However, the `regressed` rows remain meaningful without gold deflation because they compare two retrieval lanes on the same rubric.

---

## §5 Immediate Next Actions for Fresh Prime Agent

### 1. Confirm the re-anchor

Run:

```bash
git status --short --branch
git rev-parse HEAD
git show -s --format='%h %s' HEAD
```

Then read:

- `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` Reanchor block.
- `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` frontmatter + `execution_state`.
- This handoff.

### 2. Do a targeted code/data read

Read these exact surfaces:

- `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`
  - `_slug_from_route`
  - `_build_equivalence_aliases`
  - the `if args.use_route_equivalence_for_ranking` block that appends aliases.
- `src/agent/session_memory_query.py`
  - `_tokenize_query`
  - `_score_record`
- `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl`
- `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl`
- `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json`

### 3. Build a measurement before any code change

Use `/tmp` fixtures or a temporary manifest; do not edit committed artifacts yet.

Suggested experiments:

1. **Baseline reproduction**
   - Confirm current committed readout:
     - `baseline_pass_count: 16`
     - `with_equivalence_pass_count: 14`
     - `ranking_regression: 8`

2. **C1-only equivalence manifest**
   - Copy `cohorts/c1s13_v1.json` to `/tmp/c1s13_c1_only.json`.
   - Remove the C2 route-equivalence JSONL from `route_equivalence_jsonl`.
   - Run `cohort_baseline_run --manifest /tmp/c1s13_c1_only.json --mode both --write-question-delta /tmp/c1s13_c1_only_qdelta.json`.
   - Compare summary + failure buckets.
   - Purpose: measure how much damage comes from cross-campaign C2 records (`Dustwalker`, C2 Lysandra/Torbin).

3. **Final-segment alias JSONL**
   - Create a temporary copy of the route-equivalence JSONL where `from_route_id` / `to_route_id` are still valid records but the harness variant cannot be changed without code. Instead, the cleaner way may be to write a tiny temporary runner or monkeypatch test around `_build_equivalence_aliases()`.
   - If choosing code, do it in a throwaway branch or temp patch, run C1S13 and tight/natural checks, then inspect before committing.
   - Desired alias tokens after fix should look like `captain`, `lysandra`, `ironveil`, `torbin`, `jove`, `dustwalker` — **not** `route`, `longmont`, `npc`, `elderwyld`.

4. **Query-gated alias experiment**
   - Only after H1 is measured.
   - Gate aliases using information available from the natural query or first-pass retrieval, not gold.

### 4. Compare results with a small report

For each experiment, report:

- `summary`
- `failure_diagnostic_summary`
- `baseline_pass_count`
- `with_equivalence_pass_count`
- list of rows whose verdict changed
- cost (`$0` expected; retrieval-only)

Do not claim "fixed" until tight, natural, and C1S13 are all checked.

### 5. Decide the next implementation handoff

Only after measurement:

- If H1 is confirmed: write a tight external-agent handoff to fix `_slug_from_route()` / alias extraction and add tests that assert no structural route tokens (`route`, `longmont`, `npc`) are introduced by equivalence aliases.
- If H2 is confirmed: write a design/handoff for gold-free query-gated equivalence aliases.
- If neither moves C1S13: return to verify-before-debug order and inspect gold/rubric/records again before touching ranking.

---

## §6 Suggested Commands

Alias inspection:

```bash
uv run python - <<'PY'
import json, re
from pathlib import Path

def current_slug(route_id: str) -> str:
    part = route_id.rstrip("/").split("/")[-1].strip()
    return re.sub(r"[_-]+", " ", part).strip().lower()

for rel in [
    "route_equivalence_longmont_c1_v1.jsonl",
    "route_equivalence_longmont_c2_v1.jsonl",
]:
    p = Path("evals/sentence_routing_retrieval_falsification/artifacts/lexicon") / rel
    recs = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    aliases = []
    seen = set()
    for r in recs:
        for rid in (r["from_route_id"], r["to_route_id"]):
            slug = current_slug(rid)
            if slug not in seen:
                seen.add(slug)
                aliases.append(slug)
    print(rel, "records", len(recs))
    for alias in aliases:
        print("  ", alias)
PY
```

C1S13 summary:

```bash
uv run python - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json").read_text())
print("summary", d["summary"])
print("failure_diagnostic_summary", d["failure_diagnostic_summary"])
for s in d["scenarios"]:
    print("scenario", s["scenario_id"], "baseline_pass", s["baseline_pass_count"], "with_equivalence_pass", s["with_equivalence_pass_count"])
for scen in d["scenarios"]:
    for row in scen["questions"]:
        if row["delta"]["verdict"] != "unchanged_pass":
            print(row["question_id"], row["delta"]["verdict"], row["failure_diagnostic"]["bucket"], row["failure_diagnostic"]["reasons"], "support_delta", row["delta"]["support_ratio_delta"])
PY
```

Full invariant gate from PLAN is long. Use focused retrieval-only commands during interrogation, then rerun the PLAN gate before making any claim that a baseline is ready.

---

## §7 Risks and Guardrails

- **Do not over-trust PR #19's default flip.** It made the cohort runner default equivalence-augmented, but C1S13 now shows -2 net pass versus legacy.
- **Do not over-call C1S13 unchanged_fail.** The manifest says those may include gold-quality artifacts. Use regressed rows as the strongest signal.
- **Do not tune ranker weights first.** The alias token set is visibly polluted; fix/gate inputs before touching scoring.
- **Do not use gold to gate retrieval aliases.** Any alias gating must be based on natural question text or first-pass retrieval, not expected answer/must-hit/expected routes.
- **Do not edit corpus/gold/committed artifacts during interrogation.** Use `/tmp` fixtures until the mechanism is measured.
- **Do not let tactical handoffs replace prime judgment.** PR #20 and PR #21 are useful cleanup, but the core decision is how to build the next baseline that actually retrieves/answers.

---

## §8 What "Good Progress" Looks Like

The next prime agent should aim to produce one of:

1. A measured diagnosis report showing which alias-scoping hypothesis is true, with C1S13/tight/natural readouts and cost.
2. A narrow implementation handoff for an external agent that fixes the confirmed mechanism with tests at the harness boundary.
3. A reasoned stop-and-reconsider note if the data contradicts the alias-scoping hypothesis.

Do not ship a new baseline merely because one cohort improves. A credible new baseline should:

- improve or at least not regress tight cohort,
- improve or at least not regress natural cohort,
- recover C1S13 regressed rows or explain why the remaining failures are rubric/gold issues,
- preserve retrieval-only determinism and disk artifacts,
- keep cost at $0 for these deterministic checks.

---

## §9 Open Questions

1. Should C1S13 manifest include C2 route-equivalence JSONL at all, or was that included to test cross-campaign/world fallback behavior? Measure before deciding.
2. Should route-equivalence aliases be global per manifest, or only activated when the question/first-pass evidence references the entity?
3. Should `authority_effect: routing_only` imply a narrower ranking surface than "append every route slug to every query"?
4. Was PR #19's default-equivalence promotion intended to be gated by C1S13, or only by tight/natural? The current evidence suggests promotion may be premature if C1S13 is part of the acceptance gate.
5. After alias scoping is fixed, do the remaining `unchanged_fail` rows point to gold/rubric issues, missing corpus routes, or retrieval support gaps?

---

## §10 Cost

All evidence gathered for this handoff was local artifact/code inspection and retrieval-only summary commands. No LLM/eval API calls were run. Cost: `$0`.
