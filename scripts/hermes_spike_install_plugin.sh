#!/usr/bin/env bash
# Symlink the repo-local dungeonbuddy Hermes plugin into HERMES_HOME and enable it.
# Usage (from repo root):
#   export HERMES_HOME="$PWD/.hermes-runtime"
#   export DUNGEONBUDDY_REPO="$PWD"
#   export DUNGEONBUDDY_CORPUS_ROOT="$PWD/corpus"
#   ./scripts/hermes_spike_install_plugin.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$ROOT/.hermes-runtime}"
PLUGIN_SRC="$ROOT/integrations/hermes/plugins/dungeonbuddy"
PLUGIN_DST="$HERMES_HOME/plugins/dungeonbuddy"

if ! command -v hermes >/dev/null 2>&1; then
  echo "hermes not on PATH; install Hermes first (see integrations/hermes/README.md)." >&2
  exit 2
fi

mkdir -p "$HERMES_HOME/plugins"
ln -sfn "$PLUGIN_SRC" "$PLUGIN_DST"
echo "Linked: $PLUGIN_DST -> $PLUGIN_SRC"
hermes plugins enable dungeonbuddy
echo "Enabled plugin: dungeonbuddy (HERMES_HOME=$HERMES_HOME)"
