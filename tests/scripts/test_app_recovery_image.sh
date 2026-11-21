#!/usr/bin/env bash
# Synthetic recovery image contract; requires disposable local Docker resources.
set -euo pipefail
image=${1:?recovery image required}
runtime=${2:?matching runtime image required}
root=${3:?existing task-owned scratch directory required}
test -d "$root"
work=$(mktemp -d "$root/app-recovery.XXXXXXXX")
chmod 777 "$work"
net="app-recovery-test-$$-$(date +%s)"
container=''
cleanup() {
  if [[ -n "$container" ]]; then docker rm -f "$container" >/dev/null 2>&1 || true; fi
  docker network rm "$net" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker network create --internal "$net" >/dev/null
container=$(docker run -d --network "$net" --network-alias db --label buddy.test.owner=app-recovery-contract -e POSTGRES_PASSWORD=local-fixture pgvector/pgvector:0.8.6-pg16)
for _ in $(seq 1 30); do docker exec "$container" pg_isready -U postgres >/dev/null 2>&1 && break; sleep 1; done
docker exec "$container" pg_isready -U postgres >/dev/null
for name in source restore corrupt; do
  docker exec "$container" psql -U postgres -c "CREATE DATABASE dungeonbuddy_app_state_test_$name" >/dev/null
done
source_dsn='postgresql://postgres:local-fixture@db:5432/dungeonbuddy_app_state_test_source'
target_dsn='postgresql://postgres:local-fixture@db:5432/dungeonbuddy_app_state_test_restore'
corrupt_dsn='postgresql://postgres:local-fixture@db:5432/dungeonbuddy_app_state_test_corrupt'
docker run --rm --network "$net" -e DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL="$source_dsn" --entrypoint python "$runtime" -m application_state.cli upgrade >/dev/null
docker run --rm --network "$net" -e DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL="$source_dsn" --entrypoint python "$runtime" -c 'from application_state.content.service import create_plan; create_plan(title="Recovery test",campaign_id="test-world",target_session=1,target_relpath="Plans/Test.md")'
docker run --rm --network "$net" -v "$work:/backup" "$image" backup --source-dsn "$source_dsn" --out /backup/test.dump > "$work/backup.log"
docker run --rm --network "$net" -v "$work:/backup:ro" "$image" restore --source-dsn "$source_dsn" --target-dsn "$target_dsn" --backup /backup/test.dump > "$work/restore.log"
grep -q 'READY: backup SHA-256 verified; restored fingerprint matches expected' "$work/restore.log"
cp "$work/test.dump" "$work/corrupt.dump"
cp "$work/test.dump.sha256" "$work/corrupt.dump.sha256"
cp "$work/test.dump.fingerprint.json" "$work/corrupt.dump.fingerprint.json"
printf 'corruption' >> "$work/corrupt.dump"
set +e
docker run --rm --network "$net" -v "$work:/backup:ro" "$image" restore --target-dsn "$corrupt_dsn" --backup /backup/corrupt.dump > "$work/corrupt.log" 2>&1
corrupt_exit=$?
docker run --rm --network "$net" -v "$work:/backup:ro" "$image" restore --target-dsn "$target_dsn" --backup /backup/test.dump > "$work/nonempty.log" 2>&1
nonempty_exit=$?
set -e
[[ "$corrupt_exit" == 2 && "$nonempty_exit" == 2 ]]
grep -q 'SHA-256 mismatch' "$work/corrupt.log"
grep -qi 'already\|non.empty' "$work/nonempty.log"
printf 'PASS: restore parity, corrupt dump refusal, nonempty target refusal; evidence=%s\n' "$work"
