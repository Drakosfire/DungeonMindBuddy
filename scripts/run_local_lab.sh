#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || ! "$1" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "Usage: $0 <task-slug> <command> [arguments...]" >&2
  exit 2
fi

projects="$HOME/Projects"
expected_uuid="48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8"
task_root="$projects/.codex/$1"
shift

verify_directory() {
  local path="$1" parent
  if [[ "$(realpath -m -- "$path")" != "$path" ]]; then
    echo "Buddy lab path must stay under Projects without symlink redirects: $path" >&2
    exit 1
  fi
  parent="$path"
  while [[ ! -e "$parent" ]]; do
    parent="$(dirname -- "$parent")"
  done
  if [[ ! -d "$parent" || ! -w "$parent" ||
        "$(findmnt -T "$parent" -nr -o UUID | awk NF | sort -u)" != "$expected_uuid" ]]; then
    echo "Buddy labs require writable Projects storage ($expected_uuid): $parent" >&2
    exit 1
  fi
}

export TMPDIR="$task_root/scratch"
export UV_CACHE_DIR="$task_root/cache/uv"
export UV_PROJECT_ENVIRONMENT="$task_root/cache/venv"
for path in "$TMPDIR" "$UV_CACHE_DIR" "$UV_PROJECT_ENVIRONMENT"; do
  verify_directory "$path"
done
mkdir -p -- "$TMPDIR" "$UV_CACHE_DIR"
exec "$@"
