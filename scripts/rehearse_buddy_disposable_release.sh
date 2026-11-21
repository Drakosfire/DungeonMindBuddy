#!/usr/bin/env bash
# Rehearse the real Buddy production images, never a live deployment target.
set -euo pipefail

candidate=${1:-}
prior=${2:-}
if [[ $# != 2 || ! "$candidate" =~ ^[0-9a-f]{40}$ || ! "$prior" =~ ^[0-9a-f]{40}$ || "$candidate" == "$prior" ]]; then
  echo 'Supply distinct candidate and earlier full commit SHAs.' >&2
  exit 2
fi
repo=$(git rev-parse --show-toplevel)
cd "$repo"
if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
  [[ "${GITHUB_REPOSITORY:-}" == Drakosfire/DungeonMindBuddy && "${GITHUB_REF:-}" == refs/heads/main ]]
  trusted=$(git rev-parse HEAD)
  [[ "$trusted" == "${GITHUB_SHA:-}" ]]
else
  trusted=$(git rev-parse refs/remotes/origin/main)
fi
if [[ "$(git cat-file -t "$candidate")" != commit || "$(git cat-file -t "$prior")" != commit ]] ||
  ! git merge-base --is-ancestor "$candidate" "$trusted" ||
  ! git merge-base --is-ancestor "$prior" "$candidate"; then
  echo 'Both commits must belong to the initiating main history, prior before candidate.' >&2
  exit 2
fi

# The only Docker daemon allowed is this fresh hosted runner (or the designated
# local rehearsal daemon). Never inherit a remote daemon address or context.
unset DOCKER_HOST DOCKER_CONTEXT
docker_cmd=(docker --context default)
[[ "$("${docker_cmd[@]}" context inspect default -f '{{.Endpoints.docker.Host}}')" == unix:///var/run/docker.sock ]]
workspace=$(mktemp -d "${BUDDY_REHEARSAL_ROOT:?Set a task-owned rehearsal root}/buddy-disposable.XXXXXXXX")
slug="buddy-disposable-${workspace##*.}"
slug=${slug,,}
db="$slug-db"
service="$slug-app"
label=org.dungeonmind.rehearsal
pg_image='pgvector/pgvector:0.8.6-pg16@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b'
app_dsn=postgresql://rehearsal_app@127.0.0.1:5432/rehearsal_app
fault=postgresql://rehearsal_app@127.0.0.1:1/rehearsal_app
graph_dsn=postgresql://rehearsal_graph@127.0.0.1:5432/rehearsal_graph

remove_container() {
  local owner
  owner=$("${docker_cmd[@]}" container inspect -f '{{index .Config.Labels "org.dungeonmind.rehearsal"}}' "$1" 2>/dev/null || true)
  if [[ "$owner" == "$slug" ]]; then
    "${docker_cmd[@]}" container rm --force "$1" >/dev/null
  elif [[ -n "$owner" ]]; then
    echo 'Refusing to remove a container not owned by this rehearsal.' >&2
    return 1
  fi
}
cleanup() {
  local status=$?
  trap - EXIT
  remove_container "$service" || status=1
  remove_container "$db" || status=1
  for ref in "$slug:prior" "$slug:candidate"; do
    if "${docker_cmd[@]}" image inspect "$ref" >/dev/null 2>&1; then
      "${docker_cmd[@]}" image rm --no-prune "$ref" >/dev/null || status=1
    fi
  done
  rm -rf -- "$workspace" || status=1
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

build() {
  local sha=$1 role=$2 tree="$workspace/$2"
  mkdir "$tree"
  git archive "$sha" | tar -x -C "$tree"
  "${docker_cmd[@]}" buildx build --target api -f "$tree/Dockerfile.production" \
    --label "org.opencontainers.image.revision=$sha" -t "$slug:$role" --load "$tree" >&2
}
image() {
  local id
  id=$("${docker_cmd[@]}" image inspect -f '{{.Id}}' "$slug:$2")
  [[ "$("${docker_cmd[@]}" image inspect -f '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$id")" == "$1" ]]
  printf '%s\n' "$id"
}
build "$prior" prior
build "$candidate" candidate
prior_id=$(image "$prior" prior)
candidate_id=$(image "$candidate" candidate)
[[ "$prior_id" != "$candidate_id" ]]

core=$(python3 - "$workspace/candidate/uv.lock" <<'PY'
import re
import sys
import tomllib

with open(sys.argv[1], "rb") as stream:
    lock = tomllib.load(stream)
(core,) = [entry["source"]["git"] for entry in lock["package"] if entry["name"] == "dungeonmind"]
ref = re.fullmatch(r"https://github\.com/Drakosfire/DungeonMind\.git\?rev=([0-9a-f]{40})#\1", core)
if not ref:
    raise SystemExit("Expected an exact DungeonMind git lock")
print(ref[1])
PY
)
mkdir "$workspace/core"
git -C "$workspace/core" init --quiet
git -C "$workspace/core" fetch --quiet --no-tags https://github.com/Drakosfire/DungeonMind.git "$core"
[[ "$(git -C "$workspace/core" rev-parse FETCH_HEAD)" == "$core" ]]
mkdir "$workspace/migrations"
git -C "$workspace/core" archive "$core" alembic.ini migrations | tar -x -C "$workspace/migrations"

"${docker_cmd[@]}" image pull "$pg_image" >&2
"${docker_cmd[@]}" run -d --pull never --name "$db" --label "$label=$slug" --network none \
  --tmpfs /var/lib/postgresql/data:rw,size=256m --memory 768m \
  -e POSTGRES_HOST_AUTH_METHOD=trust "$pg_image" >/dev/null
[[ "$("${docker_cmd[@]}" container inspect -f '{{.HostConfig.NetworkMode}} {{json .HostConfig.PortBindings}}' "$db")" == 'none {}' ]]
for i in $(seq 1 30); do
  "${docker_cmd[@]}" exec "$db" pg_isready -h 127.0.0.1 -U postgres >/dev/null 2>&1 && break
  sleep 1
done
"${docker_cmd[@]}" exec -i "$db" psql -h 127.0.0.1 -U postgres -v ON_ERROR_STOP=1 >&2 <<'SQL'
CREATE ROLE rehearsal_app LOGIN;
CREATE ROLE rehearsal_graph LOGIN;
CREATE DATABASE rehearsal_app OWNER rehearsal_app;
CREATE DATABASE rehearsal_graph OWNER rehearsal_graph;
\c rehearsal_graph postgres
CREATE EXTENSION vector;
SQL
net="container:$db"
"${docker_cmd[@]}" run --rm --pull never --network "$net" -e "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL=$app_dsn" \
  --entrypoint python "$candidate_id" -m application_state.cli upgrade >&2
"${docker_cmd[@]}" run --rm --pull never --network "$net" -e "DUNGEONMIND_DATABASE_URL=$graph_dsn" \
  --mount "type=bind,source=$workspace/migrations,target=/core,readonly" --workdir /core \
  --entrypoint alembic "$candidate_id" upgrade head >&2

schema() {
  "${docker_cmd[@]}" exec "$db" psql -v ON_ERROR_STOP=1 -h 127.0.0.1 -U rehearsal_app -d rehearsal_app \
    -Atc 'select current_database(),current_user,version_num from application_state.schema_migrations'
  "${docker_cmd[@]}" exec "$db" psql -v ON_ERROR_STOP=1 -h 127.0.0.1 -U rehearsal_graph -d rehearsal_graph \
    -Atc 'select current_database(),current_user,version_num from dungeonmind.alembic_version'
}
before=$(schema)
jq -nc --arg core "$core" --arg authorities "$before" --arg prior "$prior" --arg candidate "$candidate" \
  '{core:$core,authorities:($authorities|split("\n")),prior_commit:$prior,candidate_commit:$candidate}'

start() {
  "${docker_cmd[@]}" run -d --pull never --name "$service" --label "$label=$slug" --network "$net" \
    --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 --memory 1g \
    --tmpfs /tmp:rw,size=128m,mode=1777 \
    --tmpfs /var/lib/preview-managed:uid=10001,gid=10001,mode=0700 \
    --tmpfs /var/lib/preview-artifacts:uid=10001,gid=10001,mode=0700 \
    --tmpfs /var/lib/preview-sessions:uid=10001,gid=10001,mode=0700 \
    --tmpfs /var/lib/preview-worldgraph:uid=10001,gid=10001,mode=0700 \
    -e DMB_MANAGED_WORLD_DATA_ROOT=/var/lib/preview-managed \
    -e DMB_ARTIFACT_DATA_ROOT=/var/lib/preview-artifacts \
    -e DUNGEONMIND_LIVE_SESSION_DIR=/var/lib/preview-sessions \
    -e DUNGEONMIND_WORLD_GRAPH_ROOT=/var/lib/preview-worldgraph \
    -e DUNGEONMIND_SERVER_API_ORIGIN=https://preview-dms.invalid \
    -e AUTH_TRUSTED_FRONTEND_ORIGINS=https://buddy.dungeonmind.net \
    -e 'DMB_HOSTED_WORLD_ACCESS_JSON={"synthetic-preview":["synthetic-subject"]}' \
    -e "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL=$2" \
    -e "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL=$graph_dsn" "$1" >/dev/null
  [[ "$("${docker_cmd[@]}" container inspect -f '{{.Image}}' "$service")" == "$1" ]]
}
probe() {
  local observed
  for i in $(seq 1 30); do
    if observed=$("${docker_cmd[@]}" exec -i "$service" python - "$1" "$2" 2>"$workspace/last-probe-error" <<'PY'
import json
import re
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

def get(path, accept="application/json"):
    try:
        reply = urlopen(
            Request(f"http://127.0.0.1:8000{path}", headers={"Accept": accept}),
            timeout=5,
        )
    except HTTPError as error:
        reply = error
    with reply:
        return reply.status, reply.headers.get_content_type(), reply.read()

phase, expected = sys.argv[1], int(sys.argv[2])
live, _, live_body = get("/health/live")
ready, _, ready_body = get("/health/ready")
html, content_type, html_body = get("/graph", "text/html")
asset = re.search(rb'<script[^>]*src="(/assets/[A-Za-z0-9_.-]+\.js)"', html_body)
auth, _, _ = get("/api/auth/session")
assert live == 200 and json.loads(live_body)["status"] == "live"
assert ready == expected, (ready, ready_body)
if ready == 503:
    assert json.loads(ready_body)["code"] == "runtime_preflight_failed"
assert (html, content_type) == (200, "text/html") and asset
asset_status, asset_type, _ = get(asset[1].decode("ascii"))
assert asset_status == 200 and asset_type in {"text/javascript", "application/javascript"}
assert auth == 401
print(json.dumps(dict(phase=phase, live=live, ready=ready, readiness=json.loads(ready_body),
                      graph_html=html, javascript=asset_status, session=auth), sort_keys=True))
PY
    ); then
      jq -c --arg image "$("${docker_cmd[@]}" container inspect -f '{{.Image}}' "$service")" '. + {image:$image}' <<<"$observed"
      return 0
    fi
    sleep 1
  done
  cat "$workspace/last-probe-error" >&2
  "${docker_cmd[@]}" logs --tail 30 "$service" >&2
  return 1
}

start "$prior_id" "$app_dsn"
probe prior_initial 200
remove_container "$service"
start "$candidate_id" "$app_dsn"
probe candidate_compatible 200
remove_container "$service"
start "$candidate_id" "$fault"
probe candidate_injected_failure 503
remove_container "$service"
start "$prior_id" "$app_dsn"
probe prior_restored 200
[[ "$(schema)" == "$before" ]]
jq -nc '{database_schema_unchanged:true}'
