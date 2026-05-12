# HANDOFF — C1S13 route evidence + canvas canonization (continuation)

**Status:** ARCHIVED — corpus session-memory promotion completed 2026-05-12; see checklist seventeenth session log and `Docs/CONVENTION-Session-Recap-Breadcrumbs-And-Memory.md`.

| Metric | Before (eval `c1s13_norm_smoke`) | After (corpus `_session_memory`) |
|--------|----------------------------------|----------------------------------|
| `records_with_routes` | 0 | 56 |
| Cohort baseline pass | 0/25 | 16/25 |
| Question-delta `unchanged_fail` | 25 | 7 |

**Created:** 2026-05-12 (UTC, evening session).
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, `M2: in_progress`, `M3: complete`, `M4: not_started`). Promotion to default retrieval **remains blocked** by PR #12 `promotion_gate_candidate.status: none_found`.
**Decision frame the user wants advanced:** *"improve the benchmark, ensure all required routes to pass exist, and further understand what is needed to move the project forward."* The first two are concrete next slices; the third is a fork the agent should bring to the user with evidence in hand, not unilaterally choose.

---

## §0 TL;DR for the next agent (read this first)

1. **There is uncommitted work on `main` that must land before anything else.** Two related but separable PRs:
   - **PR-A: Canvas canonization** — shared template module + skill + rule + new C1S13 holdout deep-dive emitter + tests + sidecar scenario reports. All currently untracked or modified locally.
   - **PR-B: Holdout deep-dive canvas asset** — the generated C1S13 holdout canvas itself (Cursor-managed path), produced by PR-A's emitter.
2. **Root cause of "all C1S13 fail" is NOT the hierarchy gold or the rubric.** Inspection proved: `evals/.../artifacts/c1s13_norm_smoke.records_meta.jsonl` has **0/68 records with routes** because no inline-tagged breadcrumb file (`Session 13 - The Meaty and the Dead.normalized.breadcrumbed.md`) was ever authored. Compare to C1S1 (20/22 with routes) — C1S1 has both `…breadcrumbed.frontmatter_seed.md` *and* `…breadcrumbed.md` (inline-tagged); C1S13 only has the seed. PR #14 generated the records JSONL from a **routeless** input, PR #13 baselined off that, PR #15 corrected hierarchy mappings — none of those moved `unchanged_fail: 25/25` because the routes never existed in the records.
3. **The next slice that actually moves a metric** is to author the missing inline-tagged C1S13 breadcrumb file, regenerate the records JSONL, then refresh the frozen `c1s13_v1` baseline / delta / question-delta and the canvas. That is the "ensuring all required routes to pass exist" deliverable the user named.
4. **Do not** jump to "tune retrieval" or "lower the rubric." See `.cursor/rules/verify-before-debug.mdc` and `.cursor/rules/gold-realignment-vs-deflation.mdc` — both rules apply directly here.

---

## §1 Mission (decomposed)

Three sequenced workstreams, each landable as its own PR:

| # | Slice | Deliverable | Decision-readiness |
|---|---|---|---|
| **W1** | Canvas canonization | Shared module, skill, rule, new emitter, tests; commit-ready locally | **Ready** — tests pass; just needs review + commit |
| **W2** | C1S13 inline-tagged breadcrumb authoring | Author `Session 13 - The Meaty and the Dead.normalized.breadcrumbed.md` from the existing `…frontmatter_seed.md` + `_normalized/` recap; regenerate `c1s13_norm_smoke.records_meta.jsonl`; refresh frozen `c1s13_v1` baseline / scenario delta / question-delta; refresh canvas | **Ready** — root-cause confirmed; mechanical execution pending |
| **W3** | Promotion-gate fork | After W2 has real signal: decide among (a) tighten `promotion_gate_candidate` rule, (b) widen falsification cohorts (C1S4–C1S12, C2S*), (c) further gold/normalization audit | **Bring to user** with measured A/B numbers, do not pre-commit |

Surface W3 to the user with concrete numbers from W2 in hand. Do not unilaterally pick a fork.

---

## §2 Why this slice (context for the successor)

### Workstream history (relevant subset; full ledger in PLAN `external_pull_requests[]`)

- **PR #12** (alias-saturation diagnostic) → committed combined cohort verdict `regressed:2 improved:1 unchanged_pass:49 unchanged_fail:4` at `question_count: 56`; `promotion_gate_candidate.status: none_found` under packaged rule. Promotion to default retrieval is blocked by this readout.
- **PR #13** (C1 holdout `c1s13_v1`) → baselined the holdout cohort against the routeless records JSONL; landed `question_count: 25`, `unchanged_fail: 25` "as expected per caveat in cohort manifest" (`notes` field flags the gold-quality risk explicitly).
- **PR #14** (records prerequisite) → committed `c1s13_norm_smoke.records_meta.{jsonl,json}` with `records_with_routes: 0` so PR #13 could generate frozen outputs at all. The §6 implementation contract did not require routes to be populated — this was unblock-only.
- **PR #15** (hierarchy gold audit) → corrected Wolf/Mossglade `location_hierarchy_equivalences` mis-mappings in `breadcrumb_query_natural_c1s13_v1.json`. Improved rubric trustworthiness; **did not** move `unchanged_fail` saturation, because the rows were already failing on `missing_expected_route_hit` rather than on hierarchy mismatch.

### What this session diagnosed (evidence-backed)

User asked "Do we not have a Wolf Hub and token?" Manual audit confirmed:

- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/wolf/` exists (Wolf hub present, route token resolvable).
- The **records** are what the retriever scores against. With `routes: []` on every record, no `expect_route_substrings` from gold can be matched — every row trips `missing_expected_route_hit` regardless of which entity the question names.
- The C1S1/C1S2/C1S3 pattern is to author a `Session N - <title>.breadcrumbed.md` inline-tagged file (e.g. `[PC][Longmont Campaign/Campaign 1/PCs/karsemine/]`, `[Location][…/stonebridge/]`) immediately after each table-significant span. `breadcrumb_normalize.py` reads that file and emits one record per `SentenceUnit` with merged routes.
- For C1S13, only `Session 13 - The Meaty and the Dead.normalized.breadcrumbed.frontmatter_seed.md` exists — a YAML-only seed listing entities. There is no `…normalized.breadcrumbed.md` (inline-tagged) for the actual recap prose.

This is the dominant failure mode (per `.cursor/rules/verify-before-debug.mdc` deliberation rubric). The PR #15 hierarchy edit was a real rubric-quality fix but addressed an **adjacent** failure mode. Remaining failure modes after W2: alias-handling at retrieval, equivalence-ranking effect on holdout signal, and scenario coverage gaps — all measurable only once routes exist.

### Why "ensure routes exist" not "patch retrieval"

Per `.cursor/rules/gold-realignment-vs-deflation.mdc` and `engineering-principles.mdc` Principle 2: lowering the rubric or tuning retrieval to make routeless inputs pass would teach the system the wrong contract (and fail in production where real records have routes). Authoring the inline-tagged breadcrumb file is the **structural** fix; it closes a class of failures, not an instance.

---

## §3 Authoritative inputs (read these in order, before writing any code)

### Always-on rules (already in context, but re-anchor)

1. `.cursor/rules/verify-before-debug.mdc` — diagnose before patching; this slice is the textbook case.
2. `.cursor/rules/gold-realignment-vs-deflation.mdc` — do not soften the rubric to mask routeless inputs.
3. `.cursor/rules/external-agent-pr-loop.mdc` (invariants) and `.cursor/skills/external-agent-pr-loop/SKILL.md` (runbook) — only relevant if you decide to dispatch a Codex worker for any sub-slice (probably not for W2; possibly for W1 if you want a clean commit-and-PR pass).
4. `.cursor/rules/cost-as-signal.mdc` — every cohort run must surface cost; `c1s13_v1` is `retrieval_only`, expect `$0`, but say so explicitly.

### Plan + checklist

5. `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` — `execution_state` block, `external_pull_requests[]` ledger (read PR #12, #13, #14, #15 entries before reasoning about the gate).
6. `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` — Reanchor block, Phase A/B/C/D status, "Last green artifact" path.
7. `Backlog.md` — `[IDEA] C1S13 hierarchy content audit` (now partially closed by PR #15) and the surrounding alias-saturation discussion.

### Corpus + benchmark layout

8. `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md` — the prose source of truth (untagged).
9. `evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.normalized.breadcrumbed.frontmatter_seed.md` — entity index already authored; W2 extends this into a full inline-tagged file.
10. `evals/sentence_routing_retrieval_falsification/manual_labels/Session 1 - Recap 3-27-24.breadcrumbed.md` — the canonical pattern for an inline-tagged breadcrumb file. Use as the structural template.
11. `evals/sentence_routing_retrieval_falsification/breadcrumb_normalize.py` — the parser/normalizer that consumes the breadcrumb file and emits records JSONL. Read `extract_records` and `_extract_record` to understand exactly what tag forms are admissible (`ALLOWED_TAG_TYPES` from `breadcrumb_smoke.py`).
12. `evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json` — the holdout cohort manifest pointing at the records JSONL.
13. `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json` — gold scenarios (post-PR #15 hierarchy fix). Authoritative source of `must_hit_tokens` and `expect_route_substrings` to satisfy.

### Canvas canonization (W1 deliverables, currently uncommitted)

14. `.cursor/skills/benchmark-review-canvas/SKILL.md` — the canon style document.
15. `.cursor/rules/benchmark-review-canvas-style.mdc` — workspace rule pointing back at the skill.
16. `evals/sentence_routing_retrieval_falsification/benchmark_review_canvas_template.py` — shared TSX fragments and Python helpers (do not duplicate inside emitters).
17. `evals/sentence_routing_retrieval_falsification/c1s13_holdout_l3_deep_dive_canvas_emit.py` — the new emitter; refactored to consume #16.
18. `tests/test_c1s13_holdout_l3_deep_dive_canvas_emit.py` and `tests/test_benchmark_review_canvas_template.py` — passing locally as of this handoff.

### Cohort runner CLI surface (read once before W2's regeneration step)

19. `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` — `--mode both`, `--write-delta`, `--check-delta`, `--write-question-delta`, `--check-question-delta`. Driven by manifest path; reruns are byte-stable when records JSONL is byte-stable.
20. `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` — `--use-route-equivalence-for-ranking`; the flag the cohort runner toggles between the two modes.

---

## §4 Files in scope (allowlist) per slice

### W1 — canvas canonization (ready to commit)

| Action | Path | Purpose |
|---|---|---|
| Create | `.cursor/skills/benchmark-review-canvas/SKILL.md` | Canon style doc for benchmark review canvases |
| Create | `.cursor/rules/benchmark-review-canvas-style.mdc` | Workspace rule pointing at the skill |
| Create | `evals/sentence_routing_retrieval_falsification/benchmark_review_canvas_template.py` | Shared TSX fragments + Python helpers |
| Create | `evals/sentence_routing_retrieval_falsification/c1s13_holdout_l3_deep_dive_canvas_emit.py` | New holdout deep-dive emitter (style-canon) |
| Create | `tests/test_c1s13_holdout_l3_deep_dive_canvas_emit.py` | Unit test for the emitter |
| Create | `tests/test_benchmark_review_canvas_template.py` | Unit test for the shared template module |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_scenario_report_c1s13_v1_baseline.json` | Sidecar scenario report consumed by the emitter for retrieved-context display |
| Create | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_scenario_report_c1s13_v1_equivalence.json` | Sidecar (equivalence mode) |
| Modify (already on disk) | `~/.cursor/projects/<workspace-slug>/canvases/c1s13-holdout-l3-question-deep-dive.canvas.tsx` | Generated canvas asset (Cursor-managed path) |

> Expected diff stat shape for W1: ~6 source files + 2 sidecar JSON + 1 generated canvas. The generated canvas asset lives outside the repo but is part of the verification surface (it must regenerate cleanly from the emitter).

### W2 — C1S13 route evidence (the actual fix)

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.normalized.breadcrumbed.md` | Inline-tagged breadcrumb file authored on top of the `_normalized/` recap |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.jsonl` | Regenerated from the new breadcrumb file (now with `routes` populated) |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.json` | Regenerated companion summary; expect `records_with_routes: >0` |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json` | Refreshed frozen baseline (will not be byte-stable; that's the point) |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json` | Refreshed scenario delta |
| Modify | `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json` | Refreshed question delta — primary metric for "did W2 work" |
| Modify | sidecar scenario reports (W1's two files) | Regenerated under the new records JSONL |
| Modify | the C1S13 holdout deep-dive canvas | Regenerated (`uv run python -m evals.sentence_routing_retrieval_falsification.c1s13_holdout_l3_deep_dive_canvas_emit`) |
| Optional Modify | `Docs/INDEX-Recap-Normalization.md` | Add a row under "Routing-only refresh baseline" documenting the new C1S13 status |

### W3 — promotion fork (do not pre-commit; surface evidence)

No file allowlist; this is a decision document deliverable. Output: a 1-page memo summarizing post-W2 numbers and the three-fork decision tree, posted to the user.

---

## §5 Files explicitly OUT OF SCOPE (denylist)

Across all three slices unless the agent and user agree to expand:

| Path | Why this campaign must not touch it |
|---|---|
| `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Retrieval/ranking behavior changes would confound the W2 attribution. |
| `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Same — runner is the measurement instrument. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_normalize.py` | The parser is the contract; changing it changes record semantics across all cohorts. |
| `src/lexicon_phase_b/**` | Lexicon producer is upstream of records; out of scope for this campaign. |
| `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json` | PR #15 already corrected hierarchy. Further rubric edits without W2 numbers risk masking signal. |
| `corpus/eldyrwild-markdown/**` | The recap prose is canonical; do not "fix" it. The breadcrumb file is a derivative artifact (per its frontmatter `source_boundary` clause). |
| `src/prompts/**` | Prompt edits are out of scope for the entire Phase B/C campaign. |
| `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (during work) | The doc-sync subagent updates this **after** each merge. Don't edit mid-slice; edit on Stage 4b. |
| `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` (during work) | Same. |

---

## §6 Implementation contract

### W1 — canonization

The work is already done locally. The successor's job is review + commit. No new code. Commands the successor runs:

1. Read the canonization files (§3 #14–#18). Confirm tests still pass (`uv run pytest tests/test_c1s13_holdout_l3_deep_dive_canvas_emit.py tests/test_benchmark_review_canvas_template.py -q`). Locally as of this handoff: `4 passed in 0.04s`.
2. Skim the generated canvas at `~/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/c1s13-holdout-l3-question-deep-dive.canvas.tsx` to confirm the user-visible style matches the C1S2 review canvas (this is the user's stated benchmark — "in this style" was the original ask).
3. Decide commit boundary: one commit for canonization (skill + rule + template), one for the new emitter + tests + sidecars. Or one combined commit if the user prefers. **Ask the user before committing.**

### W2 — author the C1S13 inline-tagged breadcrumb file

This is the substantive engineering work.

#### Step W2.1 — author the `…normalized.breadcrumbed.md`

- Source body: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md` (frontmatter + prose).
- Frontmatter: copy the existing `…normalized.breadcrumbed.frontmatter_seed.md` shape verbatim. The seed already has `entity_index` for the six PCs and the location candidates relevant to S13.
- Body: insert inline tags immediately after each table-significant span. Read `Session 1 - Recap 3-27-24.breadcrumbed.md` as the canonical example of placement (`[PC][hub_route]`, `[NPC][…]`, `[Location][…]`, `[Party][…]`, `[NewHubCandidate][proposed_route]`).
- Tag types: bounded by `ALLOWED_TAG_TYPES` in `breadcrumb_smoke.py`. Use `NewHubCandidate` for any S13 entity that doesn't have an existing hub (e.g. `basement_morgue` per the seed's rationale).
- Selectivity per the existing seed's `breadcrumb_semantics.selectivity_rule`: tag table-significant actions, discoveries, relationship beats, location-state changes, reputation beats, collective decisions, affected groups, and unresolved durable entities. Do not tag every mere mention.
- Multi-hub spans: append multiple tags to the same span (e.g. a sentence about "Bonogo and Baergrom dump out hundreds of pounds of meat on the street" tags both PCs and the location).
- Source-boundary rule (per the seed's `breadcrumb_semantics`): the tagged file is derivative; do not rewrite recap prose to match tags.

#### Step W2.2 — regenerate records JSONL

There is no committed CLI script that takes a breadcrumb file path and emits the `*_norm_smoke.records_meta.jsonl` file (PR #14 was input-only and committed the artifacts directly). Two options:

- **Preferred:** find/build a small one-shot script that calls `breadcrumb_normalize.extract_records(...)` on the new file and writes both JSONL + JSON summary using the same shape as `c1s1_norm_smoke.records_meta.{jsonl,json}` (the `metadata_record_count`/`unit_count`/`records_with_routes` keys are the contract). Read `breadcrumb_normalize.extract_records` and the existing C1S1 JSONL/JSON pair to derive the script. Likely 30–60 lines.
- **Alternative:** run an existing test/cohort fixture that produces records and capture the output. Search `tests/test_breadcrumb_natural_query.py` and `tests/test_breadcrumb_tagging_*` for the closest pattern.

Either way, the outcome is `records_with_routes` strictly `> 0`, ideally on the same order as C1S1 (~90% of units carry at least one route).

#### Step W2.3 — refresh frozen `c1s13_v1` artifacts

Use the existing CLI:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --mode both \
  --write evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json \
  --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json \
  --write-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json \
  --write-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json
```

Verify with the matching `--check`/`--check-delta`/`--check-question-delta` modes.

#### Step W2.4 — regenerate sidecar scenario reports + canvas

The new emitter writes the canvas; the sidecar JSONs were captured earlier this session by `_refresh_scenario_reports` inside the emitter. After W2.3, rerun the emitter; sidecars regenerate and canvas reflects new routes.

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.c1s13_holdout_l3_deep_dive_canvas_emit
```

#### Step W2.5 — interpret

Expected outcomes after W2.3:
- `records_with_routes` jumps from `0` to roughly `45–65` (matching ~70–90% of 68 units, mirroring C1S1's `20/22`).
- Question-delta `summary` shifts away from `unchanged_fail: 25` — exact distribution unknown until measured.
- A meaningful number of scenarios should now PASS in baseline mode (because routes finally exist for the retriever to surface). The A/B equivalence delta becomes interpretable for the first time on the holdout.

If `records_with_routes > 0` but `unchanged_fail` stays high, the next failure mode is real (alias coverage, route-substring shape, retrieval ranking). That's the W3 surface.

### W3 — promotion fork

After W2 lands, recompute the combined gate readout (tight + natural + holdout) using the existing `cohort_l3_alias_saturation_canvas_emit` machinery (PR #12) and surface to the user. Do not flip `--use-route-equivalence-for-ranking` to default without an explicit user decision.

---

## §7 Verification commands (per slice)

The successor pastes outputs back to the user (or into the PR body, if dispatched).

### W1 verification

```bash
# Canvas style tests still green.
uv run pytest tests/test_c1s13_holdout_l3_deep_dive_canvas_emit.py tests/test_benchmark_review_canvas_template.py -q

# Emitter regenerates the canvas under the Cursor path (idempotent on stable input).
uv run python -m evals.sentence_routing_retrieval_falsification.c1s13_holdout_l3_deep_dive_canvas_emit

# Confirm the existing cohort canvas emitters didn't regress alongside the canonization.
uv run pytest tests/test_cohort_l3_question_deep_dive_canvas_emit.py tests/test_cohort_l3_alias_saturation_canvas_emit.py tests/test_cursor_canvas_paths.py -q
```

### W2 verification

```bash
# After W2.2 regenerates records JSONL: routes are populated.
uv run python -c "import json; from pathlib import Path; \
  rows=[json.loads(l) for l in Path('evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.jsonl').read_text().splitlines() if l.strip()]; \
  with_routes=[r for r in rows if r.get('routes')]; \
  print(f'rows={len(rows)} records_with_routes={len(with_routes)} sample_route={(with_routes[0][\"routes\"][0][\"normalized_route\"] if with_routes else None)}')"

# Companion summary asserts records_with_routes > 0.
uv run python -c "import json; d=json.load(open('evals/sentence_routing_retrieval_falsification/artifacts/c1s13_norm_smoke.records_meta.json')); \
  assert d['records_with_routes'] > 0, d; print(d)"

# After W2.3: frozen artifacts re-check cleanly.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_c1s13_v1.json --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_delta_c1s13_v1.json --check-delta
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json

# Headline question-delta readout — the primary "did W2 work" metric.
uv run python -c "import json; d=json.load(open('evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json')); \
  print('question_count', d.get('question_count')); print('summary', d.get('summary'))"

# Adjacent regressions: tight + natural + alias-saturation lanes still green.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-delta
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check-question-delta
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/natural_v1.json \
  --baseline evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_baseline_natural_v1.json --check
uv run pytest tests/test_cohort_baseline_run.py tests/lexicon_phase_b/ tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q
```

### W3 verification

```bash
# Refresh the alias-saturation canvas under the new combined readout.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_alias_saturation_canvas_emit \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json

# Read the combined verdict + promotion gate status.
uv run python -c "import json; \
  files=['evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json', \
         'evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json', \
         'evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json']; \
  print([(f.split('/')[-1], json.load(open(f)).get('summary')) for f in files])"
```

---

## §8 Reporting contract

Per slice the successor produces:

1. **W1 / W2 PR bodies** must include `git diff --stat` filtered to the §4 allowlist; verbatim §7 output (with `passed_count` for pytest blocks); a one-paragraph "what stayed unchanged" (other cohort lanes byte-stable; retrieval code unchanged).
2. **Cost line** per `.cursor/rules/cost-as-signal.mdc`: each `cohort_baseline_run` invocation reports `Cost: $0` (retrieval-only) — say so explicitly in the PR body, do not omit because it's zero.
3. **W2 specifically** must include a "before/after" table:

   | Metric | Pre-W2 (post-PR #15) | Post-W2 |
   |---|---|---|
   | `records_with_routes` | `0` | `<measured>` |
   | `cohort_l3_ab_question_delta_c1s13_v1.summary` | `regressed:0 improved:0 unchanged_pass:0 unchanged_fail:25` | `<measured>` |
   | `cohort_baseline_c1s13_v1.aggregate.all_ok_count` (baseline mode) | `0` | `<measured>` |
   | `cohort_baseline_c1s13_v1.aggregate.all_ok_count` (with-equivalence) | `0` | `<measured>` |
4. **W3** is a memo, not a PR. Surface to the user; recommend the next slice with reasons grounded in the post-W2 numbers.

---

## §9 Acceptance rubric

### W1

- [ ] All four canonization tests pass (`test_c1s13_holdout_l3_deep_dive_canvas_emit.py`, `test_benchmark_review_canvas_template.py`, plus the two existing emitter tests still green).
- [ ] `c1s13_holdout_l3_deep_dive_canvas_emit.py` imports from `benchmark_review_canvas_template` and contains no duplicated helper bodies (`_compact_hits`, `_clip_context`, etc.) — verified by `rg "def _compact_hits|def _clip_context|def _missed_detail_rows" evals/sentence_routing_retrieval_falsification/c1s13_holdout_l3_deep_dive_canvas_emit.py` returning empty.
- [ ] Generated canvas at `~/.cursor/projects/<slug>/canvases/c1s13-holdout-l3-question-deep-dive.canvas.tsx` regenerates byte-stably from a clean checkout (idempotency).
- [ ] Skill + rule files match the format conventions used by sibling skills/rules (frontmatter shape; description string).

### W2

- [ ] `records_with_routes` strictly `> 0` after regeneration.
- [ ] `cohort_baseline_c1s13_v1.json` has `aggregate.llm_enabled: false`, `aggregate.retrieval_only: true`, and a non-trivially-changed payload vs. the pre-W2 frozen file (this is intentional; PR description must call it out).
- [ ] Question-delta `summary` no longer reads `unchanged_fail: 25` — exact direction is the measurement.
- [ ] Adjacent cohort lanes (`c1s1_to_c1s3`, `natural_v1`, alias-saturation) remain byte-stable.
- [ ] No edits to `breadcrumb_query_run.py`, `breadcrumb_normalize.py`, `cohort_baseline_run.py`, `src/lexicon_phase_b/**`, gold files, or prompts.
- [ ] PR body includes the §8 before/after table with measured numbers.

### W3

- [ ] Combined cohort verdict (tight + natural + holdout) is computed and surfaced.
- [ ] `promotion_gate_candidate.status` recomputed and quoted verbatim.
- [ ] Three-fork memo handed back to user; agent does not flip the default-equivalence-ranking flag without an explicit user yes.

---

## §10 Decision forks the successor should bring to the user

Do not silently choose. After W2 numbers are in, surface these explicitly:

1. **Tighten the promotion gate rule.** `promotion_gate_candidate` currently looks for an alias-count threshold separating regressions from improvements. If post-W2 holdout shows even modest `improved`/`regressed` movement, the rule may finally have a candidate. If it doesn't, the rule itself may need to expand its consideration set (e.g. include retrieval recall as a dimension).
2. **Widen falsification cohorts.** C1S4–C1S12 and selected C2 sessions have `_normalized/` recaps but no breadcrumb files. Widening would replicate the W2 mechanical work across multiple sessions; high cost, but produces the cohort breadth the PLAN's M4 demo target needs.
3. **Further gold/normalization audit.** PR #15 closed Wolf/Mossglade. Other location-context scenarios in `breadcrumb_query_natural_c1s13_v1.json` and the parallel files for tight/natural cohorts may have similar copy-paste smell. Lower-leverage than #1 or #2 unless a specific audit finding lands.

The user has phrased the trade-off implicitly as *"further understanding what is needed to move the project forward"* — they want the data to inform the choice, not a pre-cooked recommendation.

---

## §11 Out-of-band notes / known traps

- **There is no `--regenerate-records` CLI in the repo today.** PR #14 committed records JSONL directly. W2.2 needs a small one-shot script. Do not treat this as a blocker; build the script (~30–60 lines) using `breadcrumb_normalize.extract_records` and the C1S1 file pair as the shape contract. Capture as a `[READY]` Backlog entry afterward — this CLI is reusable for C1S4–C1S12 widening (W3 fork #2).
- **The `_normalized/` recap is the canonical body.** PR #14's seed already pointed at the `_normalized/` path. The new breadcrumb file must point its `source_recap_path` at the `_normalized/` recap, not the original `Session 13 - The Meaty and the Dead.md` (per `Docs/INDEX-Recap-Normalization.md` § "Routing-only refresh baseline").
- **Inline-tag whitespace alignment is strict.** `breadcrumb_normalize` raises `BreadcrumbNormalizeError` when the tag-stripped body drifts from the canonical recap body (whitespace + light punctuation normalization aside). Do not edit the recap body when authoring the breadcrumb file.
- **Cost expectation.** Every `cohort_baseline_run` invocation in this campaign is `--retrieval-only` and lands `$0`. Surface explicitly per `.cursor/rules/cost-as-signal.mdc`.
- **Self-review fallback.** PRs in this repo are typically self-reviewed; APPROVE demotes to COMMENTED. The `scripts/review_external_pr.py` machinery handles this automatically. Do not panic when the GitHub UI shows COMMENTED instead of APPROVED.
- **Atomic doc-sync after each merge.** Per `.cursor/rules/external-agent-pr-loop.mdc`, after each W1/W2 PR merges, the next single unit of work updates `Docs/Plans/PLAN-…md` `external_pull_requests[]`, the CHECKLIST Reanchor block + Session log, and archives this handoff (or splits it into per-slice archived handoffs). The doc-sync subagent pattern is canonical (see SKILL §4).
- **Generated canvas asset.** The C1S13 holdout deep-dive canvas lives at `~/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/c1s13-holdout-l3-question-deep-dive.canvas.tsx`. It is **not** in the repo; it is a Cursor-managed asset. The W1 emitter writes it on every run; do not commit to repo `canvases/`.
- **Stage-B bucket canvas modifications.** The local diff includes `.cursor/rules/stage-b-bucket-canvas-sync.mdc` and several `canvases/*` modifications unrelated to this campaign. Inspect and decide whether to commit alongside W1 or stash/revert before opening the PR. **Likely revert** — they're collateral from prior sessions.

---

## §12 First five actions for the successor

1. **Re-anchor.** Read `.cursor/rules/anchor.mdc` (on-demand), then read the PLAN `execution_state` and CHECKLIST Reanchor block. Confirm `Last green artifact` matches what's on `main` (`git rev-parse HEAD` → `27b3eea7…` after PR #15).
2. **Audit local changes.** `git status -s` and read every uncommitted/untracked file under `evals/`, `tests/`, `.cursor/skills/`, `.cursor/rules/`. Sort into "W1 keep", "W1 revert", "unrelated stash". The `canvases/*` modifications are almost certainly the latter.
3. **Verify W1 tests are green.** `uv run pytest tests/test_c1s13_holdout_l3_deep_dive_canvas_emit.py tests/test_benchmark_review_canvas_template.py tests/test_cohort_l3_question_deep_dive_canvas_emit.py tests/test_cohort_l3_alias_saturation_canvas_emit.py tests/test_cursor_canvas_paths.py -q`. Expect all green.
4. **Show the user the W1 commit boundary proposal.** Get a yes before committing the canonization. Use the `stage-and-commit` subagent (`.cursor/skills` if installed) or compose by hand.
5. **Move into W2.** Author the inline-tagged C1S13 breadcrumb file, then build the records-regenerate script, then run W2.3, then read out W2.5 numbers to the user.

---

## §13 Quick-reference: what changed this session (for context only)

This session diagnosed the C1S13 saturation, built the canvas canonization, authored the new C1S13 holdout deep-dive emitter, and surfaced the root-cause finding to the user. Specifically:

- Built `c1s13_holdout_l3_deep_dive_canvas_emit.py` in the C1S2 review style; iterated based on user feedback on UI (font sizes, Stat misuse) and content (added expected/retrieved context blocks, explicit "missed" breakout tables, and an explanatory callout for the `1.0 context_must_hit ratio + missing_expected_route_hit` paradox).
- Diagnosed root cause: `c1s13_norm_smoke.records_meta.jsonl` has `records_with_routes: 0` because no inline-tagged breadcrumb file was authored for C1S13. Confirmed by reading the C1S1 pattern (`Session 1 - Recap 3-27-24.breadcrumbed.md`) and contrasting with C1S13's seed-only `…normalized.breadcrumbed.frontmatter_seed.md`.
- Canonized the canvas style: `benchmark_review_canvas_template.py` (shared TSX + helpers), `.cursor/skills/benchmark-review-canvas/SKILL.md` (canon doc), `.cursor/rules/benchmark-review-canvas-style.mdc` (workspace rule). Refactored the new emitter to consume the shared module.
- Added unit tests for both the emitter and the shared template module; both passing.
- Captured sidecar scenario reports (`cohort_l3_ab_scenario_report_c1s13_v1_{baseline,equivalence}.json`) — these are an emitter side-effect from `_refresh_scenario_reports` and need to be either committed (W1 §4) or treated as ephemeral. **Successor should decide.** Recommend committing because the canvas references their content.

This handoff supersedes the in-conversation summary that lives in `<conversation_summary>` for the previous agent. Treat **this file** as the authoritative continuation surface.

---

**End of handoff.** Start with §0 TL;DR and §12 First five actions; everything else is reference material to consult as you proceed.
