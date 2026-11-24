#!/usr/bin/env bash
# Roll out a prebuilt image using the serving Buddy container's Compose configuration.
set -euo pipefail

if [[ $# != 2 || ! $1 =~ ^[0-9a-f]{40}$ || ! $2 =~ ^[0-9a-f]{40}$ || $1 == "$2" ]]; then
  echo "Usage: $0 PRIOR_SHA CANDIDATE_SHA" >&2
  exit 2
fi
old=$1
new=$2
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
container=buddy-buddy-1
env_file=/srv/dungeonmindbuddy/secrets/buddy.env
release_root=$(realpath "$HOME")
if [[ "$PWD" != "$release_root"/buddy-*-releases/"$new" ]]; then
  echo "Run from the candidate's hosted release directory." >&2
  exit 2
fi
# Serialize this rollout and its retention pass against other invocations.
exec 9>"$release_root/.buddy-rollout.lock"
flock -n 9
docker_read() { docker "$@"; }
test "$(docker_read inspect "$container" --format '{{.Config.Image}} {{.State.Health.Status}}')" = "dungeonmindbuddy:$old healthy"
test "$(docker_read inspect "$container" --format '{{index .Config.Labels "com.docker.compose.project.environment_file"}}')" = "$env_file"
old_id=$(docker_read inspect "$container" --format '{{.Image}}')
test "$(docker_read image inspect "dungeonmindbuddy:$old" --format '{{.Id}}')" = "$old_id"
for revision in "$old" "$new"; do
  test "$(docker_read image inspect "dungeonmindbuddy:$revision" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')" = "$revision"
done
new_id=$(docker_read image inspect "dungeonmindbuddy:$new" --format '{{.Id}}')
IFS=, read -ra configs <<< "$(docker_read inspect "$container" --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}')"
prior=(sudo -n /usr/bin/docker compose --project-name buddy --env-file "$env_file")
for cfg in "${configs[@]}"; do prior+=(-f "$cfg"); done
override="$PWD/compose.release.$new.yaml"
printf 'services:\n  buddy:\n    image: dungeonmindbuddy:%s\n' "$new" > "$override"
next=("${prior[@]}" -f "$override")
test "$("${prior[@]}" config --images buddy)" = "dungeonmindbuddy:$old"
test "$("${next[@]}" config --images buddy)" = "dungeonmindbuddy:$new"
config_digest() {
  "$@" config --format json | python3 -c 'import sys,json,hashlib; x=json.load(sys.stdin); x["services"]["buddy"].pop("image"); print(hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest())'
}
test "$(config_digest "${prior[@]}")" = "$(config_digest "${next[@]}")"
"${next[@]}" run --rm --no-deps --pull never -T --entrypoint python buddy -m application_state.cli check
if "${next[@]}" up -d --no-build --pull never --wait --wait-timeout 330 buddy &&
   test "$(docker_read inspect "$container" --format '{{.Image}} {{.State.Health.Status}}')" = "$new_id healthy" &&
   curl -fsS --max-time 10 https://buddy.dungeonmind.net/health/ready; then
  printf '\nSERVING %s %s\n' "$new_id" "$new"
else
  "${prior[@]}" up -d --no-build --pull never --wait --wait-timeout 330 buddy
  exit 1
fi
# Keep the release working directories discoverable by later retention passes.
printf 'old=%s\n' "$old" > "$PWD/buddy-release.previous"
if ! python3 "$script_dir/cleanup_buddy_deploy.py" --project buddy \
  --serving-tag "dungeonmindbuddy:$new" --serving-image "$new_id" \
  --rollback-tag "dungeonmindbuddy:$old" --rollback-image "$old_id" \
  --release-root "$release_root" --apply; then
  echo "Buddy is serving the verified release; post-deploy cleanup needs attention." >&2
fi
