#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
export TEST_ROOT=$scratch
printf -v candidate '%040d' 1
printf -v rollback '%040d' 2
printf -v candidate_id 'sha256:%064d' 1
printf -v rollback_id 'sha256:%064d' 2
export candidate candidate_id rollback rollback_id
request="$candidate $candidate_id $candidate_id $rollback $rollback_id default"
sed -e "s|^export PATH=.*|export PATH=\"$scratch:\$PATH\"|" \
    -e "s|/run/lock/buddy-production-deploy.lock|$scratch/lock|g" \
    -e "s|/etc/buddy-deploy|$scratch|g" \
    -e "s|/usr/local/sbin/|$scratch/|g" \
    "$source_dir/deploy-buddy-release" > "$scratch/deploy"
cat > "$scratch/docker" <<'MOCK'
#!/usr/bin/env bash
if [[ ${TEST_CANDIDATE:-0} == 1 ]]; then
  printf '%s %s healthy\n' "$candidate" "$candidate_id"
else
  printf '%s %s %s\n' "$rollback" "$rollback_id" "${TEST_HEALTH:-healthy}"
fi
MOCK
cat > "$scratch/stage-buddy-release" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
[[ $BUDDY_DEPLOY_LOCK_HELD == 1 && /proc/self/fd/9 -ef $TEST_ROOT/lock ]]
flock -n 9
if flock -n "$TEST_ROOT/lock" true; then exit 97; fi
printf 'stage\n' >> "$TEST_ROOT/calls"
exit "${TEST_STAGE_EXIT:-0}"
MOCK
sed 's/stage\\n/activate\\n/' "$scratch/stage-buddy-release" > "$scratch/activate-buddy-release"
chmod +x "$scratch/"{docker,stage-buddy-release,activate-buddy-release}

if bash "$scratch/deploy" "$request extra"; then exit 1; fi
if bash "$scratch/deploy" "$request"$'\nextra'; then exit 1; fi
if TEST_HEALTH=unhealthy bash "$scratch/deploy" "$request"; then exit 1; fi
[[ ! -e $scratch/calls ]]
(
  flock -n 8
  if bash "$scratch/deploy" "$request"; then exit 1; fi
) 8>"$scratch/lock"
[[ ! -e $scratch/calls ]]
if TEST_STAGE_EXIT=2 bash "$scratch/deploy" "$request"; then exit 1; fi
[[ $(<"$scratch/calls") == stage ]]
: > "$scratch/calls"
bash "$scratch/deploy" "$request"
[[ $(<"$scratch/calls") == $'stage\nactivate' ]]
if TEST_CANDIDATE=1 bash "$scratch/deploy" "$request"; then exit 1; fi
mkdir "$scratch/releases"
touch "$scratch/releases/$candidate.conf"
: > "$scratch/calls"
TEST_CANDIDATE=1 bash "$scratch/deploy" "$request"
[[ $(<"$scratch/calls") == $'stage\nactivate' ]]
printf '%s\n' 'Restricted request, stale rollback, locking, and stage-before-activate checks passed.'
