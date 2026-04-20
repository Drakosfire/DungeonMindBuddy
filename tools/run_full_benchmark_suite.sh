#!/usr/bin/env bash
# Run the benchmark inventory documented in Docs/Design/DESIGN-benchmark-philosophy.md
# plus Lysandra deterministic, NPC voice full manifest, and one Session Recap Scope-B run.
# Requires OPENAI_API_KEY for API-backed steps. Exit 1 if any step fails.
#
# Lysandra gold fingerprint is refreshed when corpus changes; the batch runner skips
# the statblock URL gate for that step only via per-step env (see lysandra_vertical_slice step).
# Mirathorn fact-quality / synthesis and some NPC-voice scenarios can fail on projection
# parity or model intent drift — investigate artifacts under evals/*/output/ and
# evals/npc_voice_vertical_slice/artifacts/.

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAILURES=0
step() {
  local name="$1"
  shift
  echo ""
  echo "================================================================================"
  echo "BENCHMARK: $name"
  echo "================================================================================"
  if "$@"; then
    echo ">>> OK: $name"
  else
    echo ">>> FAIL: $name (exit $?)"
    FAILURES=$((FAILURES + 1))
  fi
}

step "canon_layering/run_benchmarks.py" uv run python evals/canon_layering/run_benchmarks.py
step "mirathorn_vertical_slice/run_step1.py" uv run python evals/mirathorn_vertical_slice/run_step1.py
step "mirathorn_vertical_slice/run_step2.py" uv run python evals/mirathorn_vertical_slice/run_step2.py
step "mirathorn_vertical_slice/run_step3.py" uv run python evals/mirathorn_vertical_slice/run_step3.py
step "lysandra_vertical_slice/run_deterministic_slice.py" \
  env LYSANDRA_SLICE_SKIP_STATBLOCK_URL_GATE=1 uv run python evals/lysandra_vertical_slice/run_deterministic_slice.py

step "llm_ingestion_slice/run_slice.py" uv run python evals/llm_ingestion_slice/run_slice.py
step "mirathorn_vertical_slice/eval_entity_recall.py" uv run python evals/mirathorn_vertical_slice/eval_entity_recall.py
step "mirathorn_vertical_slice/eval_fact_quality.py" uv run python evals/mirathorn_vertical_slice/eval_fact_quality.py
step "mirathorn_vertical_slice/eval_synthesis.py" uv run python evals/mirathorn_vertical_slice/eval_synthesis.py
step "mirathorn_vertical_slice/run_council_room_question_set.py" uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py

step "npc_voice_vertical_slice (manifest --all)" uv run python -m evals.npc_voice_vertical_slice.npc_voice_planner_trace --all

export DUNGEONMIND_PLANNER_ALLOW_WRITES="${DUNGEONMIND_PLANNER_ALLOW_WRITES:-1}"
export PLANNER_REVIEW_MODE="${PLANNER_REVIEW_MODE:-summary}"
step "session_recap_ingest_vertical_slice/step1_recap_ingest_run (single)" \
  uv run python -m evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run -q

echo ""
echo "================================================================================"
if [[ "$FAILURES" -eq 0 ]]; then
  echo "FULL BENCHMARK SUITE: ALL STEPS PASSED"
  exit 0
else
  echo "FULL BENCHMARK SUITE: $FAILURES STEP(S) FAILED"
  exit 1
fi
