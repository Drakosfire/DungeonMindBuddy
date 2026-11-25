#!/usr/bin/env bash
set -euo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
export TEST_ROOT=$scratch
printf -v revision '%040d' 1
printf -v rollback '%040d' 2
printf -v digest 'sha256:%064d' 3
printf -v candidate_id 'sha256:%064d' 4
printf -v rollback_id 'sha256:%064d' 5
export revision rollback digest candidate_id rollback_id
mkdir "$scratch/releases" "$scratch/bin"
sed -e "s|/etc/buddy-deploy|$scratch|" \
    -e "s|/run/lock/buddy-production-deploy.lock|$scratch/lock|" \
    "$src/stage-buddy-release" > "$scratch/stage"
cat > "$scratch/bin/stat" <<'STUB'
#!/usr/bin/env bash
printf '0 700\n'
STUB
cat > "$scratch/bin/docker" <<'STUB'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$TEST_ROOT/docker"
case "$*" in
  "image inspect "*":$rollback")
    printf '%s %s\n' "$rollback_id" "$rollback" ;;
  "pull --platform linux/amd64 ghcr.io/drakosfire/dungeonmindbuddy@$digest")
    ;;
  "run --rm --network=none --entrypoint python ghcr.io/drakosfire/dungeonmindbuddy@$digest -c "*)
    [[ ${TEST_NO_DOCUMENT_SEED:-0} != 1 ]] ;;
  "image inspect "*"@$digest")
    if [[ "$*" == *org.dungeonmindbuddy.serving-parent* ]]; then
      printf '%s %s linux/amd64 %s %s\n' "$candidate_id" "$revision" "${TEST_GUEST_BUILD-review=0;page=0;home=}" "${TEST_SERVING_PARENT-<no value>}"
    else
      printf '%s %s linux/amd64 %s\n' "$candidate_id" "$revision" "${TEST_GUEST_BUILD-review=0;page=0;home=}"
    fi ;;
  "image ls "*)
    if [[ -e "$TEST_ROOT/tag" ]]; then printf 'dungeonmindbuddy:%s\n' "$revision"; fi ;;
  "image tag ghcr.io/drakosfire/dungeonmindbuddy@$digest dungeonmindbuddy:$revision")
    printf '%s\n' "$candidate_id" > "$TEST_ROOT/tag" ;;
  "image inspect "*":$revision")
    printf '%s %s\n' "$(cat "$TEST_ROOT/tag")" "$revision" ;;
  *) exit 90 ;;
esac
STUB
chmod +x "$scratch/bin/"*
export PATH="$scratch/bin:$PATH"
record="$scratch/releases/$revision.conf"
run() { bash "$scratch/stage" "$revision" "$digest" "$candidate_id" "$rollback" "$rollback_id" "$@"; }
refuse() {
  if run >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Unexpected staging success' >&2; exit 1; fi
  grep -F -- "$1" "$scratch/stderr"
  [[ ! -s "$scratch/stdout" ]]
}
(
  flock -n 9
  refuse 'another Buddy deploy is active'
  [[ ! -e "$scratch/docker" && ! -e "$record" ]]
) 9>"$scratch/lock"
TEST_GUEST_BUILD= refuse 'registry image does not match'
[[ ! -e "$scratch/tag" && ! -e "$record" ]]
printf '%s\n' "$rollback_id" > "$scratch/tag"
refuse 'candidate tag does not match'
[[ $(cat "$scratch/tag") == "$rollback_id" && ! -e "$record" ]]
rm "$scratch/tag"
run
run
grep -Fx "candidate_id=$candidate_id" "$record"
grep -Fx "rollback_id=$rollback_id" "$record"
grep -Fx "registry_digest=$digest" "$record"
[[ $(grep -c '^image tag ' "$scratch/docker") == 1 ]]
printf '# different approval\n' >> "$record"
refuse 'existing release policy differs'
rm "$record" "$scratch/tag"
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1' run >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Guest image accepted as default' >&2; exit 1; fi
grep -F 'registry image does not match' "$scratch/stderr"
if run invalid-mode >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Invalid mode accepted' >&2; exit 1; fi
grep -F 'invalid staging mode' "$scratch/stderr"
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1' run guest-graph >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Missing baseline accepted' >&2; exit 1; fi
grep -F 'missing guest Graph baseline policy' "$scratch/stderr"
printf 'guest_graph_space=space:test\nguest_graph_revision=rev:test\n' > "$scratch/guest-graph.conf"
TEST_GUEST_BUILD='review=0;page=0;home=;graph=1' run guest-graph
grep -Fx 'guest_graph_enabled=1' "$record"
grep -Fx 'guest_graph_space=space:test' "$record"
grep -Fx 'guest_graph_revision=rev:test' "$record"
printf 'guest_graph_space=space:changed\nguest_graph_revision=rev:test\n' > "$scratch/guest-graph.conf"
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1' run guest-graph >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Retargeted baseline accepted' >&2; exit 1; fi
grep -F 'existing release policy differs' "$scratch/stderr"
printf 'guest_graph_space=space:test\nguest_graph_revision=rev:test\n' > "$scratch/guest-graph.conf"
TEST_GUEST_BUILD='review=0;page=0;home=;graph=1' run guest-graph
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1' TEST_SERVING_PARENT=wrong run guest-graph-serving >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Wrong serving parent accepted' >&2; exit 1; fi
grep -F 'registry image does not match' "$scratch/stderr"
TEST_GUEST_BUILD='review=0;page=0;home=;graph=1' TEST_SERVING_PARENT="$rollback" run guest-graph-serving
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1' TEST_SERVING_PARENT="$rollback" run guest-graph >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Serving image accepted without parent verification' >&2; exit 1; fi
grep -F 'registry image does not match' "$scratch/stderr"
# Guest Build requires a distinct image configuration and a pinned guest Graph baseline.
rm "$record" "$scratch/tag"
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1' run guest-build >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Graph-only image accepted as guest Build' >&2; exit 1; fi
grep -F 'registry image does not match' "$scratch/stderr"
TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' TEST_SERVING_PARENT="$rollback" run guest-build-serving
grep -Fx 'guest_build_enabled=1' "$record"
grep -Fx 'guest_graph_enabled=1' "$record"
TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' TEST_SERVING_PARENT="$rollback" run guest-build-serving
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' TEST_SERVING_PARENT=wrong run guest-build-serving >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Wrong Build serving parent accepted' >&2; exit 1; fi
grep -F 'registry image does not match' "$scratch/stderr"
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' run guest-graph >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Build approval silently downgraded' >&2; exit 1; fi
grep -F 'existing release policy differs' "$scratch/stderr"
rm "$record" "$scratch/tag"
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' run guest-graph >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Build image accepted as Graph-only' >&2; exit 1; fi
grep -F 'registry image does not match' "$scratch/stderr"
TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' run guest-build
grep -Fx 'guest_build_enabled=1' "$record"
rm "$record" "$scratch/tag"
mkdir "$scratch/guest-document-bundles"
printf '%s' '{"version":1,"documents":[{"title":"Source","markdown":"A clue."}]}' > "$scratch/guest-documents-template.json"
template_sha=$(sha256sum "$scratch/guest-documents-template.json" | cut -d' ' -f1)
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' TEST_SERVING_PARENT="$rollback" run guest-build-documents-serving invalid >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Invalid template digest accepted' >&2; exit 1; fi
grep -F 'invalid guest document template digest' "$scratch/stderr"
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' TEST_SERVING_PARENT="$rollback" TEST_NO_DOCUMENT_SEED=1 run guest-build-documents-serving "$template_sha" >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Image without document seeding accepted' >&2; exit 1; fi
grep -F 'candidate image lacks guest document seeding' "$scratch/stderr"
TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' TEST_SERVING_PARENT="$rollback" run guest-build-documents-serving "$template_sha"
bundle_sha=$(sed -n 's/^guest_document_sha=//p' "$record")
[[ "$bundle_sha" =~ ^[0-9a-f]{64}$ && -f "$scratch/guest-document-bundles/$bundle_sha.json" ]]
python3 - "$scratch/guest-document-bundles/$bundle_sha.json" <<'PY'
import json, sys
bundle = json.load(open(sys.argv[1]))
assert bundle['graph_space'] == 'space:test' and bundle['graph_revision'] == 'rev:test'
assert bundle['documents'] == [{'title': 'Source', 'markdown': 'A clue.'}]
PY
TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' TEST_SERVING_PARENT="$rollback" run guest-build-documents-serving "$template_sha"
printf ' ' >> "$scratch/guest-documents-template.json"
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' TEST_SERVING_PARENT="$rollback" run guest-build-documents-serving "$template_sha" >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Changed template accepted' >&2; exit 1; fi
grep -F 'invalid guest document template' "$scratch/stderr"
printf '%s' '{"version":1,"documents":[{"title":"Source","markdown":"A clue."}]}' > "$scratch/guest-documents-template.json"
printf ' ' >> "$scratch/guest-document-bundles/$bundle_sha.json"
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' TEST_SERVING_PARENT="$rollback" run guest-build-documents-serving "$template_sha" >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Changed existing bundle accepted' >&2; exit 1; fi
grep -F 'guest document bundle differs from its digest' "$scratch/stderr"
rm "$scratch/guest-documents-template.json"
ln -s "$scratch/bundle-symlink-target" "$scratch/guest-documents-template.json"
printf '%s' '{}' > "$scratch/bundle-symlink-target"
if TEST_GUEST_BUILD='review=0;page=0;home=;graph=1;build=1' TEST_SERVING_PARENT="$rollback" run guest-build-documents-serving "$template_sha" >"$scratch/stdout" 2>"$scratch/stderr"; then echo 'Symlink template accepted' >&2; exit 1; fi
grep -F 'symlink in deployment policy' "$scratch/stderr"
printf 'Staging, idempotency, conflict, guest mode and lock checks passed.\n'
