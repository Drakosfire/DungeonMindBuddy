#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/run_remote_snapshot_from_env.sh [remote_root] [sample_size]
#
# Defaults:
#   remote_root=/media/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/corpus/eldyrwild-markdown
#   sample_size=40

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env.ssh"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: Missing ${ENV_FILE}"
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

if [[ -z "${SSH_HOST:-}" || -z "${SSH_ALIAS:-}" || -z "${SSH_PRIVATE_KEY:-}" ]]; then
  echo "ERROR: .env.ssh must define SSH_HOST, SSH_ALIAS, and SSH_PRIVATE_KEY"
  exit 1
fi

REMOTE_ROOT_DEFAULT="/media/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/corpus/eldyrwild-markdown"
REMOTE_ROOT="${1:-${REMOTE_ROOT_DEFAULT}}"
SAMPLE_SIZE="${2:-40}"

cd "${REPO_ROOT}"
uv run python evals/corpus_remote/run_remote_snapshot_pipeline.py \
  --source-host "dragonsnest" \
  --ssh-host "${SSH_HOST}" \
  --ssh-username "${SSH_ALIAS}" \
  --ssh-password "${SSH_PRIVATE_KEY}" \
  --remote-root "${REMOTE_ROOT}" \
  --sample-size "${SAMPLE_SIZE}"

