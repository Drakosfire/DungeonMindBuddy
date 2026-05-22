#!/usr/bin/env bash
set -euo pipefail

# Run the C1S4 Step 2C benchmark, generate the Step 2D canvas payload,
# copy the repo-local canvas shell into Cursor's managed canvas directory,
# and patch the generated data block so Cursor can render the current canvas.
#
# Usage:
#   bash scripts/c1s4_update_expected_context_canvas.sh
#
# Optional environment overrides:
#   REPORT_OUT=/tmp/my_report.json \
#   PAYLOAD_OUT=/tmp/my_payload.json \
#   CANVAS_PATH=/absolute/path/to/c1s4-expected-context-benchmark.canvas.tsx \
#   PRESERVE_CANVAS_SHELL=1 \
#   bash scripts/c1s4_update_expected_context_canvas.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

REPORT_OUT="${REPORT_OUT:-/tmp/c1s4_lane_aware_step2c_multimode_report.json}"
PAYLOAD_OUT="${PAYLOAD_OUT:-/tmp/c1s4_expected_context_canvas_payload.json}"
CANVAS_NAME="${CANVAS_NAME:-c1s4-expected-context-benchmark.canvas.tsx}"
GOLD_PATH="${GOLD_PATH:-evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json}"
TEMPLATE_PATH="${TEMPLATE_PATH:-evals/c1s4_preplanning_vertical_slice/canvas_templates/c1s4_expected_context_benchmark.canvas.tsx}"

if [[ ! -f "$GOLD_PATH" ]]; then
  echo "Missing gold file: $GOLD_PATH" >&2
  exit 1
fi

if [[ ! -f "$TEMPLATE_PATH" ]]; then
  echo "Missing canvas template: $TEMPLATE_PATH" >&2
  exit 1
fi

if [[ -z "${CANVAS_PATH:-}" ]]; then
  CANVAS_PATH="$(uv run python - <<'PY'
from evals.sentence_routing_retrieval_falsification.cursor_canvas_paths import default_cursor_canvas_path
print(default_cursor_canvas_path("c1s4-expected-context-benchmark.canvas.tsx"))
PY
)"
fi

mkdir -p "$(dirname "$REPORT_OUT")"
mkdir -p "$(dirname "$PAYLOAD_OUT")"
mkdir -p "$(dirname "$CANVAS_PATH")"

echo "==> Repo root: $REPO_ROOT"
echo "==> Report out: $REPORT_OUT"
echo "==> Payload out: $PAYLOAD_OUT"
echo "==> Canvas path: $CANVAS_PATH"

if [[ "${PRESERVE_CANVAS_SHELL:-0}" == "1" && -f "$CANVAS_PATH" ]]; then
  echo "==> Preserving existing canvas shell: $CANVAS_PATH"
else
  echo "==> Installing canvas shell from template"
  cp "$TEMPLATE_PATH" "$CANVAS_PATH"
fi

echo "==> Running Step 2C multimode benchmark"
uv run python evals/c1s4_preplanning_vertical_slice/step2c_expected_context_benchmark.py \
  --all-modes \
  --output-json "$REPORT_OUT"

echo "==> Updating Cursor canvas generated data block"
uv run python -m evals.c1s4_preplanning_vertical_slice.step2d_expected_context_canvas_emit \
  --report "$REPORT_OUT" \
  --gold "$GOLD_PATH" \
  --payload-out "$PAYLOAD_OUT" \
  --canvas-tsx "$CANVAS_PATH"

echo "==> Verifying canvas generated block is up to date"
uv run python -m evals.c1s4_preplanning_vertical_slice.step2d_expected_context_canvas_emit \
  --report "$REPORT_OUT" \
  --gold "$GOLD_PATH" \
  --payload-out "$PAYLOAD_OUT" \
  --canvas-tsx "$CANVAS_PATH" \
  --check

echo
printf 'Done.\n'
printf 'Report:  %s\n' "$REPORT_OUT"
printf 'Payload: %s\n' "$PAYLOAD_OUT"
printf 'Canvas:  %s\n' "$CANVAS_PATH"
echo
echo "Open the Canvas path in Cursor (beside chat)."
echo "Use mode + question filters; inspect PR66 planner affordance diagnostics before per-question cards."
echo "Useful sanity grep:"
echo "  grep -n \"PlannerAffordanceDiagnosticsPanel\\|SupportFieldPolicyPanel\\|Rendered LLM context\" \"$CANVAS_PATH\" | head -20"
