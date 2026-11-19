# Historical isolated Graph demo

This lab retains the isolated launcher and loopback HTTP transport used by the
earlier native Graph demonstration. Buddy's product Graph uses its maintained
routes and the shared service/storage in `apps/live_control_server/native_graph_demo/`.
Those production modules stay in place. The isolated HTTP server is no longer
copied into the production image.

## Dependency and support boundary

The launcher deliberately requires these historical dependency revisions:

- DungeonMind: `430c1a6db631d097dfa0a273f8933067f708bc56`.
- WorldKeeper: `ef9c50f2d6aa89a35e9408f83fc4d0ba47825ca2`.

Buddy's current locked DungeonMind revision differs. An ordinary current-lock
environment therefore fails the launcher's exact dependency guard. Relocation
does not qualify a historical environment against today's product service or
establish native create/edit/restart compatibility. Do not weaken the guard or
silently replace the pin to make startup succeed. The cleanup decision is to
retain historical replay and the current protocol/isolation regression fixtures;
[the qualification record #4014](https://github.com/Drakosfire/DungeonMindBuddy/issues/4014) owns that decision and its evidence.

From the repository root, inspect the retained CLI without starting a runtime:

```bash
python3 evals/native_graph_demo/launch.py --help
```

Native replay requires the **complete matched historical checkout** below. Do
not combine today’s relocated launcher or shared product service with old
dependencies: that hybrid remains semantically unqualified. The retained current
lab files support protocol/isolation regression tests, not a current-lock native
launch claim. The checks refuse ambient PostgreSQL settings, foreign state,
unverified source and ambiguous ownership. No shared database fallback exists.
Use the [lab guide](../README.md) for Projects storage and scratch isolation.
For ordinary Buddy use, follow the [local Play runbook](../../Docs/Runbooks/RUNBOOK-local-play-dogfood.md).

## Evidence and recovery

`tests/test_native_graph_demo_http.py` retains the real loopback protocol and
launcher isolation tests. Its fake-service cases do not qualify native semantic
operations. Shared service/storage and index Graph tests remain independent.

The original source locations are recoverable from the exact pre-relocation
Buddy revision `26132b18652ef80b0c311cdfc08a8f6b118ad5b3`:

```bash
git show 26132b18652ef80b0c311cdfc08a8f6b118ad5b3:scripts/native_graph_demo.py
git show 26132b18652ef80b0c311cdfc08a8f6b118ad5b3:apps/live_control_server/native_graph_demo/server.py
```

The [historical handoff](../../Docs/Plans/HANDOFF-SURFACE-native-graph-demo.md)
preserves dated topology and evidence limits. Its old paths and assignments are
historical references, not current launch instructions or active leases.


## Qualified complete historical replay

The create/connect/read/restart proof uses the whole Buddy repository at
`36fce5feb40fe849f6c58254d6e1029c6e0fecef` (the merged native index integration),
Core and WorldKeeper at the pins above, Python 3.13.12, Node 22.23.0/npm 10.9.8,
and the immutable PostgreSQL/pgvector image checked by that launcher's
`--postgres-runtime container` preflight. The image must already be available;
the launcher does not silently pull or substitute one.

Prepare separate, clean Git checkouts at those exact revisions. Do not switch
an active checkout. Set `HISTORICAL_BUDDY`, `HISTORICAL_CORE`, and
`HISTORICAL_PYTHON` to their absolute paths; the last names an existing Python
3.13 interpreter. The following local recipe uses the approved Projects
filesystem and owns all of its generated data. Other executors need their own
explicitly authorized storage policy.

```bash
set -euo pipefail
: "${HISTORICAL_BUDDY:?Set an isolated complete Buddy checkout}"
: "${HISTORICAL_CORE:?Set an isolated complete Core checkout}"
: "${HISTORICAL_PYTHON:?Set an existing Python 3.13 executable}"
test "$(git -C "$HISTORICAL_BUDDY" rev-parse HEAD)" = \
  36fce5feb40fe849f6c58254d6e1029c6e0fecef
test "$(git -C "$HISTORICAL_CORE" rev-parse HEAD)" = \
  430c1a6db631d097dfa0a273f8933067f708bc56
git -C "$HISTORICAL_BUDDY" diff --quiet HEAD
git -C "$HISTORICAL_CORE" diff --quiet HEAD
for historical_path in "$HOME/Projects/.codex" "$HISTORICAL_BUDDY" "$HISTORICAL_CORE"; do
  test "$(findmnt -no UUID -T "$historical_path" | tr -d '[:space:]')" = \
    48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8
done
HISTORICAL_TASK=$(mktemp -d "$HOME/Projects/.codex/buddy-native-history.XXXXXX")
export HISTORICAL_TASK
mkdir -m 700 "$HISTORICAL_TASK/state" "$HISTORICAL_TASK/tmp" \
  "$HISTORICAL_TASK/uv-cache" "$HISTORICAL_TASK/xdg-cache" \
  "$HISTORICAL_TASK/npm-cache" "$HISTORICAL_TASK/node-cache" "$HISTORICAL_TASK/empty"
mkdir -m 700 "$HISTORICAL_TASK/empty/leaf"
export TMPDIR="$HISTORICAL_TASK/tmp" UV_CACHE_DIR="$HISTORICAL_TASK/uv-cache"
export UV_PROJECT_ENVIRONMENT="$HISTORICAL_TASK/python"
export XDG_CACHE_HOME="$HISTORICAL_TASK/xdg-cache" PYTHONDONTWRITEBYTECODE=1
export npm_config_cache="$HISTORICAL_TASK/npm-cache"
export NODE_COMPILE_CACHE="$HISTORICAL_TASK/node-cache"
export NATIVE_DEMO_BUILD_OUTDIR="$HISTORICAL_TASK/assets"
: > "$HISTORICAL_TASK/npmrc"
: > "$HISTORICAL_TASK/global-npmrc"
export npm_config_userconfig="$HISTORICAL_TASK/npmrc"
export npm_config_globalconfig="$HISTORICAL_TASK/global-npmrc"
cd "$HISTORICAL_BUDDY"
python3 scripts/prepare_patched_hermes.py
uv sync --locked --python "$HISTORICAL_PYTHON"
(
  exec {historical_frontend_lock}>>"/tmp/dungeonmind-frontend-verification-$(id -u).lock"
  flock "$historical_frontend_lock"
  cd apps/live-control-ui
  test "$(node --version)" = v22.23.0
  test "$(npm --version)" = 10.9.8
  npm ci --no-audit --no-fund
  node --input-type=module -e "import {build} from './node_modules/vite/dist/node/index.js'; await build({configFile:'native-demo.vite.config.ts',envDir:false});"
)
printf 'Private historical task: %s\n' "$HISTORICAL_TASK"
```

Run the preflight first. Choose a loopback port you own; the default example
uses 4183 and refuses an occupied port before initializing a database.
The clean runtime environment omits ambient database/provider configuration.
`--check` does not initialize or start the database.

```bash
HISTORICAL_PORT=${HISTORICAL_PORT:-4183}
historical_demo() {
  env -i HOME="$HOME" PATH="$PATH" LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
    TMPDIR="$HISTORICAL_TASK/tmp" \
    DMB_DOTENV_ROOT="$HISTORICAL_TASK/empty/leaf" \
    DMB_MODEL_POLICY_ROOT="$HISTORICAL_BUDDY" \
    "$UV_PROJECT_ENVIRONMENT/bin/python" "$HISTORICAL_BUDDY/scripts/native_graph_demo.py" \
    --state-dir "$HISTORICAL_TASK/state" --dungeonmind-source "$HISTORICAL_CORE" \
    --assets "$HISTORICAL_TASK/assets" --postgres-runtime container \
    --port "$HISTORICAL_PORT" "$@"
}
historical_demo --check
historical_demo
```

Open the printed loopback URL. Prepare and explicitly confirm a synthetic
Location, then a supported relationship such as `visits`. Record server readback,
including actual World/entity identities, revision ID, graph SHA and operation
receipts. Use the browser’s existing `/api/graph` and operation network responses
for full identities/hashes; API reads require the normal HTML-bootstrapped
`X-Demo-Capability` header. Keep capability values out of URLs and logs.
Stop with Ctrl-C, verify the launcher and its PostgreSQL actually
stopped, and run `historical_demo` again with the **same private state**. Reopen
and compare those native records. This profile explicitly lacks Event creation,
rename and delete; do not substitute other mutations for unavailable operations.

The qualification created one Location and one relationship, then recovered an
identical full Graph DTO (four objects/five relationships), native identity,
revision/hash and both operation records after real PostgreSQL and Python
shutdown/restart. A new loopback origin also showed the same server readback.
These are historical matched-repository results, not current-lab, hosted-auth,
production-release, or general feature qualification.

Preserve state until shutdown and recovery checks finish. Remove only this
task's stopped, identity-verified container and disposable directories afterward;
never use a global Docker prune or another runtime's paths. Protocol tests and
this historical proof do not qualify today's mixed launcher/service/dependency
combination. Any future current-lock native support needs a separate bounded
Graph assignment and fresh migration, semantic and persistence verification.
