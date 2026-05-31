# HANDOFF: PR97 — Blind Manifest-Backed Query/Admission Context Runner

**Status:** Implementation complete on branch (pending PR)  
**Mission:** First real manifest-backed query/admission slice — blind to gold, question-ID routing, and PR96 dogfood traces.

---

## What landed

| File | Role |
|------|------|
| `src/live_play/manifest_context_query.py` | Core library: intent hints from question text, lane-budget retrieval, admission policy, virtual audit preconditions, context packet construction |
| `tests/test_manifest_context_query.py` | 15 anti-oracle boundary tests |
| `evals/c2_live_prep/run_c2s23_manifest_context_query.py` | Benchmark harness CLI (no gold argument) |
| `evals/c2_live_prep/benchmarks/c2s23_manifest_query_gold.json` | Evaluator-only gold (`dmb_c2s23_manifest_query_gold_v1`) |
| `evals/c2_live_prep/evaluate_c2s23_context_packets.py` | Extended: `--packet-prefix`, `--summary-schema`, new gold fields |
| `evals/c2_live_prep/schemas/enriched_planning_context_packet.schema.json` | Optional `source_excerpt` for authority verdicts |

---

## Verification (§7)

```bash
uv run pytest tests/test_manifest_context_query.py -q
uv run python evals/c2_live_prep/run_c2s23_manifest_context_query.py \
  --questions evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json \
  --manifest evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json \
  --output-dir evals/c2_live_prep/artifacts/runs/2026-05-30
uv run python evals/c2_live_prep/evaluate_c2s23_context_packets.py \
  --gold evals/c2_live_prep/benchmarks/c2s23_manifest_query_gold.json \
  --packet-dir evals/c2_live_prep/artifacts/runs/2026-05-30 \
  --packet-prefix c2s23_manifest_query_context_packet_ \
  --summary evals/c2_live_prep/artifacts/runs/2026-05-30/c2s23_manifest_query_context_summary.json \
  --summary-schema dmb_c2s23_manifest_query_context_run_v1 \
  --output evals/c2_live_prep/artifacts/last_c2s23_manifest_query_context_eval.json
```

**Focused PR97 eval:** 6/6 pass (2026-05-30 artifacts).

---

## Anti-oracle guarantees

- Runner does **not** read `*gold*.json` (tested via `open` monkeypatch).
- Runner does **not** read `c2s23_dogfood_*` trace artifacts (tested).
- `build_query_plan()` depends on question text only — identical plans for same text, different `question_id` (tested).
- Seed `category`, `expected_source_roles`, `answer_requirements` are never consumed for routing/admission.

---

## PR body boilerplate

This PR implements a blind manifest-backed context runner.  
The runner does not read gold.  
The runner does not route by question ID.  
The runner does not consume PR96 dogfood traces.  
The evaluator, separately, scores emitted packets against gold.

**Focused PR97 eval: 6/6 pass**

---

## PR98 follow-on

Integrate `manifest_context_query` into the live planning-turn path so the product planner uses the same query/admission contract proven here.
