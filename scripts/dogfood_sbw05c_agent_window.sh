#!/usr/bin/env bash
# SBW05c dogfood — agent-window script + bootstrap
#
# Product expectation (DESIGN §17 truncated to SBW05c):
#   Open Plan → Agent window → design creature → save ThreatDraft →
#   open Statblock tool → generate candidate → edit → validate → …
#
# Reality check (2026-07-24): Hermes/Agent Interaction has no ThreatDraft
# create tool yet. This script prints the agent-window dialogue we expect to
# work, then bootstraps the missing draft (and optionally generates) via Buddy
# HTTP so the Statblock Workbench UI path can be dogfooded.
#
# Prerequisites (3 processes):
#   - DungeonMindServer on STATBLOCKS base URL (local default :7860)
#   - Buddy live_control_server on :8000
#   - live-control-ui Vite on :5173
#
# Usage:
#   ./scripts/dogfood_sbw05c_agent_window.sh                 # print script + create draft
#   ./scripts/dogfood_sbw05c_agent_window.sh --generate      # also generate via live LLM
#   ./scripts/dogfood_sbw05c_agent_window.sh --seed-fixture  # seed typed fixture cand_* (skip LLM)
#   ./scripts/dogfood_sbw05c_agent_window.sh --script-only
#
# Prefer --seed-fixture for the SBW05c edit→validate gate: live generate is
# stochastic (422 validation_failed / timeouts) and is not what SBW05c proves.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUDDY_API="${BUDDY_API:-http://127.0.0.1:8000}"
UI_ORIGIN="${UI_ORIGIN:-http://localhost:5173}"
DO_GENERATE=0
DO_SEED_FIXTURE=0
SCRIPT_ONLY=0
FIXTURE_CAND_ID="${FIXTURE_CAND_ID:-cand_dogfood05c}"

for arg in "$@"; do
  case "$arg" in
    --generate) DO_GENERATE=1 ;;
    --seed-fixture) DO_SEED_FIXTURE=1 ;;
    --script-only) SCRIPT_ONLY=1 ;;
    -h|--help)
      sed -n '1,30p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

if [[ "$DO_GENERATE" -eq 1 && "$DO_SEED_FIXTURE" -eq 1 ]]; then
  echo "ERROR: use either --generate or --seed-fixture, not both" >&2
  exit 2
fi

print_agent_window_script() {
  cat <<EOF
================================================================================
SBW05c — agent-window script (what we expect should work)
================================================================================

0. Stack up
   - DungeonMindServer (statblocks v1 internal API)
   - Buddy:  cd ${ROOT} && uv run uvicorn apps.live_control_server.main:app --reload --port 8000
   - UI:     cd ${ROOT}/apps/live-control-ui && npm run dev
   - Open:   ${UI_ORIGIN}/plan

1. Open the Agent window on Plan
   (Plan Agent Interaction / Hermes — not Graph Review.)

2. Operator → Agent (design beat)
   "Design a CR 3 gate-brute for tonight. Keep it short: name, look, one signature
   attack, one nasty reaction. Do not invent graph canon; this is a ThreatDraft
   concept only."

3. Agent → Operator
   Returns creature prose + generation intent (CR, must_include notes).

4. Operator → Agent (persist beat)  *** PRODUCT EXPECTATION ***
   "Save that as a ThreatDraft and give me the draft_id + version."

   Expected: agent creates ThreatDraft via Buddy tool/API and returns:
     draft_id = <uuid>
     version  = 1

   Gap today: no agent tool for ThreatDraft create. Use this script's bootstrap
   (below) or curl POST ${BUDDY_API}/api/live/threat-drafts until that tool exists.

5. Operator → Agent (or do manually)
   "Open the Statblock tool and generate a candidate from that draft."

   Manual equivalent:
     - Plan toolbox → Statblock
     - Draft ID = <uuid>, Expected version = 1
     - Generate candidate
     - Ignore Graph Review errors (not part of SBW05c)

6. SBW05c merge-gate walkthrough (human in Statblock Workbench)
   [ ] Editor loads in edit mode (session-only working copy)
   [ ] Scalar edit (creature name)
   [ ] Rule-element edit (e.g. attack name/text)
   [ ] Validate working copy → preview receipt + issues
   [ ] Field vs global issues; severities info|warning|error distinct
   [ ] Fix → revalidate
   [ ] Edit again → receipt stale
   [ ] Simulate Server down / STATBLOCKS disabled → validate unavailable, edits kept
   [ ] No Accept / Save / revise controls

7. Done for SBW05c
   Record: draft_id, cand_id, HEAD SHA, checklist results.
   Not in scope: graph publish, immutable revision save, revise/lineage.

================================================================================
EOF
}

print_agent_window_script

if [[ "$SCRIPT_ONLY" -eq 1 ]]; then
  exit 0
fi

echo "Bootstrap: create ThreatDraft via Buddy API (${BUDDY_API})"
echo

if ! curl -sf "${BUDDY_API}/api/live/surface" >/dev/null; then
  echo "ERROR: Buddy API not reachable at ${BUDDY_API}" >&2
  echo "Start: uv run uvicorn apps.live_control_server.main:app --reload --port 8000" >&2
  exit 1
fi

CREATE_PAYLOAD='{
  "world_id": "world_eldyrwild",
  "campaign_id": "campaign_longmont_c2",
  "focus": { "session": 23, "prep_label": "sbw05c-dogfood" },
  "name": "SBW05c Dogfood Brute",
  "description": "Gate-brute for SBW05c preview-validate dogfood. Stocky ironhide enforcer with a crushing greatclub and a nasty opportunity reaction. Concept-only ThreatDraft; not graph canon.",
  "threat_kind": "creature",
  "intended_roles": ["brute", "gate-guard"],
  "tags": ["sbw05c", "dogfood"],
  "generation_intent": {
    "ruleset": { "system": "dnd5e", "edition": "2024" },
    "target_cr": "3",
    "must_include": ["greatclub attack", "opportunity reaction"],
    "must_avoid": ["legendary actions"]
  },
  "encounter_context": {
    "party_level": 5,
    "party_size": 4,
    "terrain_notes": ["stone gate", "narrow approach"]
  },
  "graph_context_snapshot": {
    "graph_revision_id": "rev_dogfood_sbw05c",
    "selected_node_ids": ["node_dogfood_placeholder"],
    "admitted_source_anchor_ids": ["anchor_dogfood_placeholder"]
  },
  "created_by": "gm-dogfood"
}'

CREATE_RESP="$(curl -sf "${BUDDY_API}/api/live/threat-drafts" \
  -H 'Content-Type: application/json' \
  -d "${CREATE_PAYLOAD}")"

DRAFT_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["draft_id"])' <<<"${CREATE_RESP}")"
DRAFT_VERSION="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])' <<<"${CREATE_RESP}")"

echo "Created ThreatDraft"
echo "  draft_id: ${DRAFT_ID}"
echo "  version:  ${DRAFT_VERSION}"
echo

CAND_ID=""
if [[ "$DO_SEED_FIXTURE" -eq 1 ]]; then
  echo "Seeding typed fixture candidate into Buddy cache (skips live LLM generate)…"
  CAND_ID="$(
    cd "${ROOT}" && uv run python - <<PY
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    GeneratedStatblockCandidateV1,
)
from apps.live_control_server.services.statblock_candidate_cache import (
    store_candidate_payload,
)

root = Path(${ROOT@Q})
fixture = json.loads(
    (root / "tests/fixtures/statblocks/v1/candidate-response.json").read_text()
)
fixture["candidate_id"] = ${FIXTURE_CAND_ID@Q}
now = datetime.now(timezone.utc)
fixture["created_at"] = now.isoformat().replace("+00:00", "Z")
fixture["expires_at"] = (now + timedelta(days=30)).isoformat().replace("+00:00", "Z")
candidate = GeneratedStatblockCandidateV1.model_validate(fixture)
store_candidate_payload(root, candidate)
print(candidate.candidate_id)
PY
  )"
  echo "  cand_id: ${CAND_ID}"
  echo "  (definition: Ironhide Brute from tests/fixtures/statblocks/v1/candidate-response.json)"
  echo
elif [[ "$DO_GENERATE" -eq 1 ]]; then
  echo "Generating candidate from draft (requires DungeonMindServer + DUNGEONMIND_STATBLOCKS_*)…"
  GEN_RESP="$(curl -sf "${BUDDY_API}/api/live/threat-drafts/${DRAFT_ID}/candidates:generate" \
    -H 'Content-Type: application/json' \
    -d "{\"expected_draft_version\": ${DRAFT_VERSION}}" || true)"
  if [[ -z "${GEN_RESP}" ]]; then
    echo "ERROR: generate failed. Check Server + DUNGEONMIND_STATBLOCKS_* env, then either:" >&2
    echo "  re-run with --seed-fixture (preferred for SBW05c), or --generate again." >&2
    exit 1
  fi
  CAND_ID="$(python3 -c 'import json,sys
d=json.load(sys.stdin)
c=(d.get("candidate") or {})
print(c.get("candidate_id") or "")' <<<"${GEN_RESP}")"
  OUTCOME="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("outcome",""))' <<<"${GEN_RESP}")"
  echo "  outcome: ${OUTCOME}"
  echo "  cand_id: ${CAND_ID:-"(none)"}"
  if [[ -z "${CAND_ID}" ]]; then
    echo "Generate did not return a candidate_id. Full response:" >&2
    echo "${GEN_RESP}" >&2
    echo >&2
    echo "Tip: live generate is stochastic. Prefer:" >&2
    echo "  ./scripts/dogfood_sbw05c_agent_window.sh --seed-fixture" >&2
    exit 1
  fi
  echo
fi

cat <<EOF
--------------------------------------------------------------------------------
Next (UI)
--------------------------------------------------------------------------------
1. Open ${UI_ORIGIN}/plan
2. Plan toolbox → Statblock   (skip Graph Review)
3. $(if [[ -n "${CAND_ID}" ]]; then
     echo "Candidate ID = ${CAND_ID} → Load candidate"
   else
     echo "Draft ID = ${DRAFT_ID}, Expected version = ${DRAFT_VERSION} → Generate candidate"
     echo "   (or re-run this script with --seed-fixture to skip flaky LLM generate)"
   fi)
4. Run the SBW05c checklist printed above.
   Validate still needs DungeonMindServer + DUNGEONMIND_STATBLOCKS_* even with --seed-fixture.

Deep link:
  ${UI_ORIGIN}/plan?candidateId=${CAND_ID:-cand_…}
--------------------------------------------------------------------------------
EOF
