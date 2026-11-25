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
export obsolete obsolete_id referenced referenced_id staged_alias staged_id
export buddy_cache=kawf9lmjnqr7xnpceypatjkyx
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
cat > "$scratch/bin/mv" <<'STUB'
#!/usr/bin/env bash
set -eu
/usr/bin/mv "$@"
if [[ ${INTERRUPT_RECEIPT:-0} == 1 ]]; then kill -TERM "$PPID"; fi
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
  'buildx du')
    [[ "$*" == *"--builder default --filter id=$buddy_cache"* ]] || exit 101
    if [[ ! -e "$TEST_ROOT/cache-removed" ]]; then
      printf '%s %s %s %s\n' "$buddy_cache" "${CACHE_SHARED:-false}" "${CACHE_RECLAIMABLE:-true}" \
        "${CACHE_DESCRIPTION:-COPY scripts/prepare_patched_hermes.py}"
    fi ;;
  'buildx prune')
    [[ "$*" == "buildx prune --builder default --force --filter id=$buddy_cache --filter shared!=true --filter description~=prepare_patched_hermes[.]py|patches/hermes-agent" ]] || exit 102
    [[ $(cat "$TEST_ROOT/receipt") == "BUDDY_LIVE $candidate $candidate_id" ]] || exit 103
    if flock -n "$TEST_ROOT/lock" true; then exit 104; fi
    touch "$TEST_ROOT/cache-removed" ;;
  'image inspect')
    case "${*: -1}" in
      "dungeonmindbuddy:$candidate") printf '%s %s\n' "${CANDIDATE_PIN_OVERRIDE:-$candidate_id}" "$candidate" ;;
      "dungeonmindbuddy:$rollback") printf '%s %s\n' "$rollback_id" "$rollback" ;;
      "dungeonmindbuddy:$obsolete")
        if [[ "$4" == *Created* ]]; then
          printf '%s %s %s\n' "$obsolete_id" "$obsolete" "${TEST_IMAGE_CREATED:-2000-01-01T00:00:00Z}"
        else
          printf '%s\n' "$obsolete_id"
        fi ;;
      *) exit 92 ;;
    esac ;;
  'image ls')
    if [[ "$3" == --no-trunc ]]; then
      if [[ ${TEST_AUTO_RETENTION:-0} == 1 ]]; then
        printf 'dungeonmindbuddy:%s %s\n' "$obsolete" "$obsolete_id" \
          "$rollback" "$rollback_id" "$referenced" "$referenced_id" "$staged_alias" "$staged_id"
      fi
    else
      printf 'dungeonmindbuddy:%s\n' "$obsolete"
    fi ;;
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
    elif [[ "${3:-}" == *'.Config.Env'* ]]; then
      if [[ "${GUEST_ENV_MISSING:-0}" != 1 ]]; then
        printf '%s\n' 'DMB_HOSTED_GUEST_GRAPH_ENABLED=1' "DMB_HOSTED_GUEST_BUILD_ENABLED=${TEST_GUEST_BUILD_ENABLED:-0}" "DMB_HOSTED_GUEST_PLAN_ENABLED=${TEST_GUEST_PLAN_ENABLED:-0}" 'DMB_GUEST_GRAPH_SOURCE_SPACE=space:test' 'DMB_GUEST_GRAPH_SOURCE_REVISION=rev:test'
        if [[ "${TEST_LEGACY_ENV:-0}" != 1 ]]; then printf '%s\n' "DMB_HOSTED_GUEST_PLAY_ENABLED=${TEST_GUEST_PLAY_ENABLED:-0}" "DMB_HOSTED_GUEST_MEDIA_ENABLED=${TEST_GUEST_MEDIA_ENABLED:-0}"; fi
        if [[ "${TEST_GUEST_BUDDY_ENABLED:-0}" == 1 ]]; then
          printf '%s\n' "DMB_HOSTED_GUEST_CONVERSATION_ENABLED=${TEST_GUEST_CONVERSATION_ENABLED:-1}" 'DMB_HOSTED_GUEST_TURN_ENABLED=1' 'DMB_HOSTED_GUEST_BUILD_BUDDY_ENABLED=1'
        fi
        if [[ "${TEST_GUEST_PLAY_BUDDY_ENABLED:-0}" == 1 ]]; then printf '%s\n' 'DMB_HOSTED_GUEST_PLAY_BUDDY_ENABLED=1'; fi
        if [[ "${TEST_GUEST_BUILD_PROPOSALS_ENABLED:-0}" == 1 ]]; then printf '%s\n' 'DMB_HOSTED_GUEST_BUILD_PROPOSALS_ENABLED=1'; fi
        if [[ -n "${TEST_DOCUMENT_SHA:-}" ]]; then
          printf '%s\n' 'DMB_GUEST_DOCUMENT_BUNDLE=/run/buddy-guest-documents.json' "DMB_GUEST_DOCUMENT_BUNDLE_SHA256=$TEST_DOCUMENT_SHA"
        fi
      fi
    elif [[ "${3:-}" == *'/run/buddy-guest-documents.json'* ]]; then
      printf '%s false\n' "$TEST_ROOT/guest-document-bundles/$TEST_DOCUMENT_SHA.json"
    else
      printf '%s healthy /test/buddy\n' "$(cat "$TEST_ROOT/serving")"
    fi ;;
  'compose -f')
    [[ "$*" == 'compose -f - up -d --no-deps --no-build --pull never --wait --wait-timeout 330 buddy' ]] || exit 93
    payload=$(cat)
    case "$payload" in
      *"image: dungeonmindbuddy:$candidate"*) id=$candidate_id ;;
      *"image: dungeonmindbuddy:$rollback"*) id=$rollback_id ;;
      *) exit 94 ;;
    esac
    printf '%s\n' "$payload" > "$TEST_ROOT/payload-$id"
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
reset "$rollback_id"
if INTERRUPT_RECEIPT=1 run; then exit 1; fi
[[ $(cat "$scratch/activations") == "$candidate_id" ]]
grep -Fx "BUDDY_LIVE $candidate $candidate_id" "$scratch/receipt"
printf 'candidate_tag=dungeonmindbuddy:%s\ncandidate_id=%s\nrollback_tag=dungeonmindbuddy:%s\nrollback_id=%s\nrollback_revision=%s\n' \
  "$staged" "$staged_id" "$rollback" "$rollback_id" "$rollback" > "$scratch/releases/$staged.conf"
printf 'guest_graph_enabled=1\nguest_graph_space=space:test\nguest_graph_revision=rev:test\n' >> "$scratch/releases/$staged.conf"
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
rm "$scratch/retire-images"
sed -i '$d' "$scratch/releases/$staged.conf"
rm "$scratch/removals"
reset "$candidate_id"
TEST_AUTO_RETENTION=1 TEST_IMAGE_CREATED=2099-01-01T00:00:00Z run
[[ ! -e "$scratch/removals" ]]
TEST_AUTO_RETENTION=1 bash "$scratch/activate" "$candidate" --preview-images > "$scratch/stdout"
grep -Fx "BUDDY_IMAGE_ELIGIBLE dungeonmindbuddy:$obsolete $obsolete_id" "$scratch/stdout"
[[ ! -e "$scratch/removals" && ! -s "$scratch/activations" ]]
TEST_AUTO_RETENTION=1 bash "$scratch/activate" "$candidate" --prune-images > "$scratch/stdout"
grep -Fx "BUDDY_IMAGE_RETIRED dungeonmindbuddy:$obsolete $obsolete_id" "$scratch/stdout"
[[ $(cat "$scratch/removals") == "dungeonmindbuddy:$obsolete" && ! -s "$scratch/activations" ]]
rm "$scratch/removals"
reset "$rollback_id"
TEST_AUTO_RETENTION=1 run
[[ $(cat "$scratch/removals") == "dungeonmindbuddy:$obsolete" ]]

printf '%s\n' "$buddy_cache" > "$scratch/retire-cache"
reset "$rollback_id"
if FAIL_PUBLIC=1 run; then exit 1; fi
[[ ! -e "$scratch/cache-removed" ]]
reset "$rollback_id"
if CACHE_SHARED=true run; then exit 1; fi
grep -F 'release is healthy and recorded; build cache retention did not finish' "$scratch/stderr"
[[ $(cat "$scratch/activations") == "$candidate_id" && ! -e "$scratch/cache-removed" ]]
if CACHE_RECLAIMABLE=false run; then exit 1; fi
if CACHE_DESCRIPTION='unrelated cache' run; then exit 1; fi
[[ ! -e "$scratch/cache-removed" ]]
run
[[ -e "$scratch/cache-removed" ]]
run
# A staged guest candidate gets its pinned baseline; rollback does not inherit it.
printf 'guest_graph_enabled=1\nguest_graph_space=space:test\nguest_graph_revision=rev:test\n' >> "$scratch/releases/$candidate.conf"
reset "$rollback_id"
run
grep -F 'DMB_HOSTED_GUEST_GRAPH_ENABLED: "1"' "$scratch/payload-$candidate_id"
grep -F 'DMB_GUEST_GRAPH_SOURCE_SPACE: "space:test"' "$scratch/payload-$candidate_id"
grep -F 'DMB_GUEST_GRAPH_SOURCE_REVISION: "rev:test"' "$scratch/payload-$candidate_id"
reset "$rollback_id"
if GUEST_ENV_MISSING=1 run; then echo 'Candidate missing guest settings accepted' >&2; exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
if grep -F 'DMB_HOSTED_GUEST_GRAPH_ENABLED' "$scratch/payload-$rollback_id"; then echo 'Rollback inherited candidate settings' >&2; exit 1; fi
# Build is candidate-only, checked at runtime, and requires Graph.
printf 'guest_build_enabled=1\n' >> "$scratch/releases/$candidate.conf"
reset "$rollback_id"
TEST_GUEST_BUILD_ENABLED=1 run
grep -F 'DMB_HOSTED_GUEST_BUILD_ENABLED: "1"' "$scratch/payload-$candidate_id"
reset "$rollback_id"
if TEST_GUEST_BUILD_ENABLED=0 run; then echo 'Candidate missing guest Build switch accepted' >&2; exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
if grep -F 'DMB_HOSTED_GUEST_BUILD_ENABLED' "$scratch/payload-$rollback_id"; then echo 'Rollback inherited guest Build' >&2; exit 1; fi
mkdir "$scratch/guest-document-bundles"
printf '%s' '{"version":1,"graph_space":"space:test","graph_revision":"rev:test","documents":[{"title":"Source","markdown":"A clue."}]}' > "$scratch/bundle"
TEST_DOCUMENT_SHA=$(sha256sum "$scratch/bundle" | cut -d' ' -f1)
export TEST_DOCUMENT_SHA
cp "$scratch/bundle" "$scratch/guest-document-bundles/$TEST_DOCUMENT_SHA.json"
printf 'guest_document_sha=%s\n' "$TEST_DOCUMENT_SHA" >> "$scratch/releases/$candidate.conf"
reset "$rollback_id"
TEST_GUEST_BUILD_ENABLED=1 run
grep -F "DMB_GUEST_DOCUMENT_BUNDLE_SHA256: \"$TEST_DOCUMENT_SHA\"" "$scratch/payload-$candidate_id"
grep -F '/run/buddy-guest-documents.json:ro' "$scratch/payload-$candidate_id"
printf 'guest_plan_enabled=1\n' >> "$scratch/releases/$candidate.conf"
reset "$rollback_id"
TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 run
grep -F 'DMB_HOSTED_GUEST_PLAN_ENABLED: "1"' "$scratch/payload-$candidate_id"
printf 'guest_play_enabled=1\nguest_media_enabled=1\n' >> "$scratch/releases/$candidate.conf"
reset "$rollback_id"
TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 TEST_GUEST_PLAY_ENABLED=1 TEST_GUEST_MEDIA_ENABLED=1 run
grep -F 'DMB_HOSTED_GUEST_PLAY_ENABLED: "1"' "$scratch/payload-$candidate_id"
grep -F 'DMB_HOSTED_GUEST_MEDIA_ENABLED: "1"' "$scratch/payload-$candidate_id"
reset "$rollback_id"
if TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 TEST_GUEST_PLAY_ENABLED=0 TEST_GUEST_MEDIA_ENABLED=1 run; then echo 'Missing Play switch accepted' >&2; exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
reset "$rollback_id"
if TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 TEST_GUEST_PLAY_ENABLED=1 TEST_GUEST_MEDIA_ENABLED=0 run; then echo 'Missing media switch accepted' >&2; exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
printf 'guest_buddy_enabled=1\n' >> "$scratch/releases/$candidate.conf"
reset "$rollback_id"
TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 TEST_GUEST_PLAY_ENABLED=1 TEST_GUEST_MEDIA_ENABLED=1 TEST_GUEST_BUDDY_ENABLED=1 run
grep -F 'DMB_HOSTED_GUEST_BUILD_BUDDY_ENABLED: "1"' "$scratch/payload-$candidate_id"
reset "$rollback_id"
if TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 TEST_GUEST_PLAY_ENABLED=1 TEST_GUEST_MEDIA_ENABLED=1 TEST_GUEST_BUDDY_ENABLED=1 TEST_GUEST_CONVERSATION_ENABLED=0 run; then echo 'Missing guest conversation switch accepted' >&2; exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
! grep -q 'DMB_HOSTED_GUEST_BUILD_BUDDY_ENABLED' "$scratch/payload-$rollback_id"
printf 'guest_play_buddy_enabled=1\n' >> "$scratch/releases/$candidate.conf"
reset "$rollback_id"
TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 TEST_GUEST_PLAY_ENABLED=1 TEST_GUEST_MEDIA_ENABLED=1 TEST_GUEST_BUDDY_ENABLED=1 TEST_GUEST_PLAY_BUDDY_ENABLED=1 run
grep -F 'DMB_HOSTED_GUEST_PLAY_BUDDY_ENABLED: "1"' "$scratch/payload-$candidate_id"
reset "$rollback_id"
if TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 TEST_GUEST_PLAY_ENABLED=1 TEST_GUEST_MEDIA_ENABLED=1 TEST_GUEST_BUDDY_ENABLED=1 run; then echo 'Missing Play Buddy switch accepted' >&2; exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
! grep -q 'DMB_HOSTED_GUEST_PLAY_BUDDY_ENABLED' "$scratch/payload-$rollback_id"
printf 'guest_build_proposals_enabled=1\n' >> "$scratch/releases/$candidate.conf"
reset "$rollback_id"
TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 TEST_GUEST_PLAY_ENABLED=1 TEST_GUEST_MEDIA_ENABLED=1 TEST_GUEST_BUDDY_ENABLED=1 TEST_GUEST_PLAY_BUDDY_ENABLED=1 TEST_GUEST_BUILD_PROPOSALS_ENABLED=1 run
grep -F 'DMB_HOSTED_GUEST_BUILD_PROPOSALS_ENABLED: "1"' "$scratch/payload-$candidate_id"
reset "$rollback_id"
if TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 TEST_GUEST_PLAY_ENABLED=1 TEST_GUEST_MEDIA_ENABLED=1 TEST_GUEST_BUDDY_ENABLED=1 TEST_GUEST_PLAY_BUDDY_ENABLED=1 run; then echo 'Missing Build proposals switch accepted' >&2; exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
! grep -q 'DMB_HOSTED_GUEST_BUILD_PROPOSALS_ENABLED' "$scratch/payload-$rollback_id"
sed -i '/^guest_play_buddy_enabled=/d' "$scratch/releases/$candidate.conf"
reset "$rollback_id"
if TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 TEST_GUEST_PLAY_ENABLED=1 TEST_GUEST_MEDIA_ENABLED=1 TEST_GUEST_BUDDY_ENABLED=1 run; then echo 'Build proposals accepted without Play Buddy' >&2; exit 1; fi
grep -F 'guest Build proposals require guest Play Buddy' "$scratch/stderr"
printf 'guest_play_buddy_enabled=1\n' >> "$scratch/releases/$candidate.conf"
sed -i '/^guest_build_proposals_enabled=/d' "$scratch/releases/$candidate.conf"
sed -i '/^guest_play_buddy_enabled=/d' "$scratch/releases/$candidate.conf"
sed -i '/^guest_buddy_enabled=/d' "$scratch/releases/$candidate.conf"
sed -i '/^guest_plan_enabled=/d' "$scratch/releases/$candidate.conf"
reset "$rollback_id"
if run; then echo 'Play without Plan accepted' >&2; exit 1; fi
grep -F 'guest Play requires guest Plan' "$scratch/stderr"
printf 'guest_plan_enabled=1\n' >> "$scratch/releases/$candidate.conf"
sed -i '/^guest_play_enabled=/d; /^guest_media_enabled=/d' "$scratch/releases/$candidate.conf"
reset "$rollback_id"
TEST_LEGACY_ENV=1 TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=1 run
reset "$rollback_id"
if TEST_GUEST_BUILD_ENABLED=1 TEST_GUEST_PLAN_ENABLED=0 run; then echo 'Candidate missing guest Plan switch accepted' >&2; exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
sed -i '/^guest_plan_enabled=/d' "$scratch/releases/$candidate.conf"
reset "$rollback_id"
if TEST_GUEST_BUILD_ENABLED=1 FAIL_PUBLIC=1 run; then echo 'Failed guest release accepted' >&2; exit 1; fi
grep -Fx "BUDDY_ROLLED_BACK $rollback $rollback_id" "$scratch/stderr"
if grep -F 'buddy-guest-documents.json' "$scratch/payload-$rollback_id"; then echo 'Rollback inherited guest document bundle' >&2; exit 1; fi
printf ' ' >> "$scratch/guest-document-bundles/$TEST_DOCUMENT_SHA.json"
if TEST_GUEST_BUILD_ENABLED=1 run; then echo 'Changed document bundle accepted' >&2; exit 1; fi
grep -F 'guest document bundle digest mismatch' "$scratch/stderr"
sed -i '/^guest_document_sha=/d' "$scratch/releases/$candidate.conf"
sed -i '/^guest_graph_enabled=/d' "$scratch/releases/$candidate.conf"
if TEST_GUEST_BUILD_ENABLED=1 run; then echo 'Guest Build without Graph accepted' >&2; exit 1; fi
grep -F 'guest Build requires guest Graph' "$scratch/stderr"
printf 'Activation, no-op, rollback, image, guest baseline and cache retention checks passed.\n'
