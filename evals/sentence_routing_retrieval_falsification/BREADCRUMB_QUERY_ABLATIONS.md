# Breadcrumb query ablations (operator checklist)

All commands assume repo root and `uv`. Index build is **zero API cost** after breadcrumbs exist.

## Baselines

1. **No index** — unset `DUNGEONMIND_SESSION_MEMORY_RECORDS_JSONL`. Planner keeps corpus tree + read tools only.
2. **Candidate index** — set JSONL from normalized breadcrumbs:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --breadcrumb-md "evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md" \
  --corpus-root corpus/eldyrwild-markdown \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/local/session20_query_report.json

export DUNGEONMIND_SESSION_MEMORY_RECORDS_JSONL="$(pwd)/evals/sentence_routing_retrieval_falsification/artifacts/runs/local/session20_query_report_records_meta.jsonl"
```

(`breadcrumb_query_run` writes `<report_stem>_records_meta.json` plus a sibling `.jsonl` next to the report.)

3. **Capsule off vs on**

```bash
unset DUNGEONMIND_PLANNER_MEMORY_CAPSULE_PATH
export DUNGEONMIND_PLANNER_MEMORY_CAPSULE_PATH="$(pwd)/evals/sentence_routing_retrieval_falsification/fixtures/longmont_c2_memory_capsule.md"
```

Clear `out/planner_eval_cache/` bucket after toggling capsule or JSONL so cached instructions refresh.

## Deterministic grading (no LLM)

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --records-jsonl "$DUNGEONMIND_SESSION_MEMORY_RECORDS_JSONL" \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_closed_loop_v1.json
```

## Promotion gate

Promotion requires measured improvement on **query recall** or **read-path efficiency** without **unsupported claims** in live traces — single-trial LLM passes are not sufficient (`verify-before-debug.mdc`).

**Cost:** Index build/query itself is `$0`; planner cohorts still incur model cost — compare `scenario_estimated_cost_usd` per run vs baseline cohort mean (`cost-as-signal.mdc`).
