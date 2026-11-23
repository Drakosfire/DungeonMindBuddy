#!/usr/bin/env bash
# Isolated command-contract tests for the production activator.
set -euo pipefail

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
export TEST_ROOT=$scratch
printf -v candidate '%040d' 1
printf -v rollback '%040d' 2
printf -v candidate_id 'sha256:%064d' 1
printf -v rollback_id 'sha256:%064d' 2
export candidate rollback candidate_id rollback_id
printf -v obsolete '%040d' 3
printf -v obsolete_id 'sha256:%064d' 3
printf -v referenced '%040d' 4
printf -v referenced_id 'sha256:%064d' 4
printf -v staged '%040d' 5
printf -v staged_id 'sha256:%064d' 5
printf -v staged_alias '%040d' 6
export obsolete obsolete_id referenced referenced_id
mkdir -p "$scratch/releases" "$scratch/bin"
sed -e "s|/etc/buddy-deploy|$scratch|" \
    -e "s|/run/lock/buddy-production-deploy.lock|$scratch/lock|" \
    -e 's|\$config_dir/serving"|$config_dir/receipt"|' \
    "$source_dir/activate-buddy-release" > "$scratch/activate"
cat > "$scratch/compose.conf" <<'POLICY'
compose=(docker compose)
upstream=http://127.0.0.1:8000
persistent_root=/test/buddy
POLICY
printf 'candidate_tag=dungeonmindbuddy:%s\nrollback_tag=dungeonmindbuddy:%s\nrollback_revision=%s\n' \
  "$candidate" "$rollback" "$rollback" > "$scratch/releases/$candidate.conf"
printf 'candidate_id=%s\nrollback_id=%s\n' "$candidate_id" "$rollback_id" >> "$scratch/releases/$candidate.conf"

cat > "$scratch/bin/stat" <<'STUB'
#!/usr/bin/env bash
[[ $1 == -c && $2 == '%u %a' && $3 == -- ]] || exit 91
printf '%s\n' "$4" >> "$TEST_ROOT/policy-checks"
printf '%s 600\n' "${TEST_OWNER:-0}"
STUB
cat > "$scratch/bin/curl" <<'STUB'
#!/usr/bin/env bash
set -eu
if [[ ${*: -1} == https://buddy.dungeonmind.net/health/ready ]]; then
  printf '%s\n' "$(cat "$TEST_ROOT/serving")" >> "$TEST_ROOT/public-checks"
  [[ ${FAIL_PUBLIC:-0} != 1 || $(cat "$TEST_ROOT/serving") != "$candidate_id" ]] || exit 22
  if [[ $(cat "$TEST_ROOT/serving") == "$candidate_id" ]]; then
    printf '%s' "${PUBLIC_CANDIDATE_STATUS:-200}"
  else
    printf '200'
  fi
fi
if [[ ${FAIL_READY:-0} == 1 && ${*: -1} == */health/ready ]]; then
  [[ $(cat "$TEST_ROOT/serving") != "$candidate_id" ]] || exit 22
fi
STUB
cat > "$scratch/bin/docker" <<'STUB'
#!/usr/bin/env bash
set -eu
case "$1 $2" in
  'image inspect')
    case "${*: -1}" in
      "dungeonmindbuddy:$candidate") printf '%s %s\n' "${CANDIDATE_PIN_OVERRIDE:-$candidate_id}" "$candidate" ;;
      "dungeonmindbuddy:$rollback") printf '%s %s\n' "$rollback_id" "$rollback" ;;
      "dungeonmindbuddy:$obsolete") printf '%s\n' "$obsolete_id" ;;
      *) exit 92 ;;
    esac ;;
  'image ls') printf 'dungeonmindbuddy:%s\n' "$obsolete" ;;
  'image rm')
    [[ "$*" == "image rm --no-prune dungeonmindbuddy:$obsolete" ]] || exit 96
    [[ $(cat "$TEST_ROOT/serving" ) == "$candidate_id" ]] || exit 97
    [[ $(cat "$TEST_ROOT/receipt") == "BUDDY_LIVE $candidate $candidate_id" ]] || exit 98
    if flock -n "$TEST_ROOT/lock" true; then exit 99; fi
    [[ ${FAIL_RETENTION:-0} != 1 ]] || exit 100
    printf '%s\n' "${*: -1}" >> "$TEST_ROOT/removals" ;;
  'ps -aq') printf 'stopped-container\n' ;;
  'compose ps') printf 'buddy-container\n' ;;
  'compose port') printf '127.0.0.1:8000\n' ;;
  'inspect --format')
    if [[ "${*: -1}" == stopped-container ]]; then
      printf '%s\n' "$referenced_id"
    else
      printf '%s healthy /test/buddy\n' "$(cat "$TEST_ROOT/serving")"
    fi ;;
  'compose -f')
    [[ "$*" == 'compose -f - up -d --no-deps --no-build --pull never --wait --wait-timeout 330 buddy' ]] || exit 93
    case "$(cat)" in
      *"image: dungeonmindbuddy:$candidate") id=$candidate_id ;;
      *"image: dungeonmindbuddy:$rollback") id=$rollback_id ;;
      *) exit 94 ;;
    esac
    printf '%s\n' "$id" >> "$TEST_ROOT/activations"
    printf '%s\n' "$id" > "$TEST_ROOT/serving" ;;
  *) exit 95 ;;
esac
STUB
chmod +x "$scratch/bin/"*
export PATH="$scratch/bin:$PATH"

reset() {
  printf '%s\n' "$1" > "$scratch/serving"
  : > "$scratch/activations"
  : > "$scratch/public-checks"
}
run() {
  bash "$scratch/activate" "$candidate" > "$scratch/stdout" 2> "$scratch/stderr"
}

reset "$rollback_id"
run
grep -Fx "BUDDY_LIVE $candidate $candidate_id" "$scratch/stdout"
[[ $(cat "$scratch/activations") == "$candidate_id" ]]

reset "$candidate_id"
run
[[ ! -s "$scratch/activations" ]]

reset "$rollback_id"
if FAIL_READY=1 run; then exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
[[ $(cat "$scratch/serving") == "$rollback_id" ]]
[[ $(cat "$scratch/activations") == "$candidate_id"$'\n'"$rollback_id" ]]

reset "$rollback_id"
if FAIL_PUBLIC=1 run; then exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
[[ ! -s "$scratch/stdout" ]]
[[ $(cat "$scratch/serving") == "$rollback_id" ]]
[[ $(cat "$scratch/public-checks") == "$candidate_id"$'\n'"$rollback_id" ]]

reset "$rollback_id"
if PUBLIC_CANDIDATE_STATUS=302 run; then exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
[[ ! -s "$scratch/stdout" ]]
[[ $(cat "$scratch/serving") == "$rollback_id" ]]

reset "$candidate_id"
if FAIL_PUBLIC=1 run; then exit 1; fi
grep -F 'already serving candidate did not pass public readiness' "$scratch/stderr"
[[ ! -s "$scratch/stdout" && ! -s "$scratch/activations" ]]

reset "$rollback_id"
if CANDIDATE_PIN_OVERRIDE="$rollback_id" run; then exit 1; fi
grep -F 'staged image does not match' "$scratch/stderr"
if TEST_OWNER=1000 run; then exit 1; fi
grep -F 'deployment policy is not controlled by root' "$scratch/stderr"
(
  flock -n 9
  : > "$scratch/policy-checks"
  if run; then exit 1; fi
  grep -F 'another Buddy deploy is active' "$scratch/stderr"
  [[ ! -s "$scratch/policy-checks" ]]
) 9> "$scratch/lock"
[[ ! -s "$scratch/activations" ]]
printf 'candidate_tag=dungeonmindbuddy:%s\ncandidate_id=%s\nrollback_tag=dungeonmindbuddy:%s\nrollback_id=%s\nrollback_revision=%s\n' \
  "$staged" "$staged_id" "$rollback" "$rollback_id" "$rollback" > "$scratch/releases/$staged.conf"
printf 'dungeonmindbuddy:%s %s\n' \
  "$candidate" "$candidate_id" "$rollback" "$rollback_id" \
  "$referenced" "$referenced_id" "$staged_alias" "$staged_id" \
  "$obsolete" "$obsolete_id" > "$scratch/retire-images"
reset "$rollback_id"
if FAIL_PUBLIC=1 run; then exit 1; fi
[[ ! -e "$scratch/removals" ]]
reset "$rollback_id"
if FAIL_RETENTION=1 run; then exit 1; fi
grep -F 'release is healthy and recorded; image retention did not finish' "$scratch/stderr"
[[ $(cat "$scratch/activations") == "$candidate_id" && ! -e "$scratch/removals" ]]
run
[[ $(cat "$scratch/removals") == "dungeonmindbuddy:$obsolete" ]]
printf 'candidate_id=%s\n' "$obsolete_id" >> "$scratch/releases/$staged.conf"
if run; then exit 1; fi
[[ $(cat "$scratch/removals") == "dungeonmindbuddy:$obsolete" && $(cat "$scratch/serving") == "$candidate_id" ]]
printf 'Activation, no-op, rollback and preflight refusals passed.\n'
