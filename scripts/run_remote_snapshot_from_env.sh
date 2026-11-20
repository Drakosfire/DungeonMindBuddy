#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/run_remote_snapshot_from_env.sh [remote_root] [sample_size]
#
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env.ssh"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: Missing ${ENV_FILE}"
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

REMOTE_ROOT="${1:-${CORPUS_REMOTE_ROOT:-}}"
SAMPLE_SIZE="${2:-40}"
: "${SSH_HOST:?Set SSH_HOST in .env.ssh}"
: "${SSH_ALIAS:?Set SSH_ALIAS in .env.ssh}"
: "${CORPUS_SOURCE_HOST:?Set CORPUS_SOURCE_HOST in .env.ssh}"
: "${REMOTE_ROOT:?Pass remote_root or set CORPUS_REMOTE_ROOT in .env.ssh}"

# Preserve the existing wrapper's password input while keeping it out of argv.
export CORPUS_SSH_PASSWORD="${CORPUS_SSH_PASSWORD:-${SSH_PRIVATE_KEY:-}}"

cd "${REPO_ROOT}"
uv run python evals/corpus_remote/run_remote_snapshot_pipeline.py \
  --source-host "${CORPUS_SOURCE_HOST}" \
  --ssh-host "${SSH_HOST}" \
  --ssh-username "${SSH_ALIAS}" \
  --remote-root "${REMOTE_ROOT}" \
  --sample-size "${SAMPLE_SIZE}"

