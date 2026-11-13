# Deploy Buddy to buddy.dungeonmind.net

Run from the root of the reviewed Buddy checkout on the selected deployment host. Use one Bash session for the command blocks. Run the public checks from a separate client using the helper from the same reviewed Buddy checkout or a copy of that helper from the release commit. Advance only when the expected result for the current step is recorded.

## 1. Prepare the release record

Record the host and SSH alias, release commit, image ID or registry digest, Compose project, host bind port, approved absolute persistent root, Nginx virtual host, DNS records, certificate owner, and rollback owner. Record the approved DMS test account and expected World, both database owners and migration heads, and the backup and restore evidence. Keep credentials and session cookies in their designated stores.

Run the [host inventory](../Plans/RUNBOOK-HOSTED-read-only-host-inventory.md).

```bash
bash scripts/host_inventory.sh
docker compose version &&
docker buildx version &&
docker info --format '{{.DockerRootDir}}'
```

Require both Compose and Buildx to report versions before proceeding.

Check free space on the Docker filesystem and the persistent data filesystem. Confirm the selected loopback port is available for a first deploy or is owned by the Buddy service for an upgrade. The checked-in defaults are host loopback port 8080 and container port 8000.

## 2. Verify both databases and restore evidence

Use separate PostgreSQL database identities for Buddy application state and DungeonMind WorldGraph. With operator-configured PostgreSQL service aliases named `buddy-app` and `buddy-worldgraph`, verify the targets:

```bash
(
  for db_service in buddy-app buddy-worldgraph; do
    psql "service=$db_service" -X -v ON_ERROR_STOP=1 \
      -c 'SELECT current_database(), current_user;' \
      -c 'SELECT extname, extversion FROM pg_extension ORDER BY extname;' || exit
  done
)
```

Compare the identities, extensions, and current migration revisions with the pinned releases. Check Buddy application state using the [authority recovery runbook](RUNBOOK-application-state-authority-recovery.md). Use the WorldGraph owner's migration and recovery procedure for that database. Record the approved command and expected revision for each authority in the release record.

Restore the application-state dump with its checksum and fingerprint sidecars into a fresh isolated target and require fingerprint parity. Restore the WorldGraph database and associated files into isolated targets and verify the migration revision and a known World read. Verify the matching managed World, artifact, session, and WorldGraph files from backup. Record which backups form a consistent restore set and where the evidence is stored. A first deployment with empty authorities still needs a restore rehearsal.

The release operator records the following for the selected host:

- The WorldGraph restore owner and a reference to their approved procedure.
- The owner and approved recovery procedure for the managed World, artifact,
  session, and WorldGraph files.
- The consistent backup set identifier, isolated restore targets, and evidence
  locations for both database restores and file recovery.

Complete this record and verify the isolated restore results before proceeding
to production migrations or startup.

Test required migrations against the restored copies. Before applying them to production, record whether the previous release can use the resulting schema and data. If it cannot, record the forward repair or coordinated recovery procedure and its owner.

## 3. Build and start on loopback

Provision a protected Compose environment file outside the checkout with the variables required by the [production Compose example](../../deploy/production/compose.production.yaml). Use the approved DMS HTTPS origin, trust `https://buddy.dungeonmind.net`, and configure the approved World assignments and both database URLs. Set `BUDDY_PERSISTENT_ROOT` to the absolute path of the approved durable host directory. Create its `managed`, `artifacts`, `sessions`, and `worldgraph` directories with access for container UID/GID 10001.

```bash
read -r -p 'Approved release commit: ' buddy_release
read -r -p 'Absolute path to the protected Compose environment file: ' buddy_env
read -r -p 'Compose project [buddy]: ' buddy_project
buddy_project=${buddy_project:-buddy}
test -z "$(git status --porcelain)" && \
  test "$(git rev-parse HEAD)" = "$(git rev-parse --verify "$buddy_release^{commit}")" && \
  test -r "$buddy_env"
```

Continue after all three checks succeed. For an upgrade, use the existing Compose project name and keep the previous release’s image and override available.

```bash
unset buddy_compose
prepare_buddy_release() {
  local revision
  revision=$(git rev-parse HEAD) || return
  buddy_tag="dungeonmindbuddy:$revision"
  docker build --target api -f Dockerfile.production -t "$buddy_tag" . || return
  buddy_image_id=$(docker image inspect "$buddy_tag" --format '{{.Id}}') || return
  buddy_override=$(mktemp) || return
  printf 'services:\n  buddy:\n    image: %s\n' "$buddy_tag" > "$buddy_override" || return
  local -a candidate_compose=(env
    -u AUTH_TRUSTED_FRONTEND_ORIGINS
    -u BUDDY_HTTP_BIND_PORT
    -u BUDDY_PERSISTENT_ROOT
    -u DMB_HOSTED_WORLD_ACCESS_JSON
    -u DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL
    -u DUNGEONMIND_SERVER_API_ORIGIN
    -u DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL
    docker compose --project-name "$buddy_project" --env-file "$buddy_env"
    -f deploy/production/compose.production.yaml -f "$buddy_override")
  local configured_image
  configured_image=$("${candidate_compose[@]}" config --images buddy) || return
  if [[ "$configured_image" != "$buddy_tag" ]]; then
    printf 'Compose did not resolve the built Buddy image tag\n' >&2
    return 1
  fi
  buddy_compose=("${candidate_compose[@]}")
  printf 'Release image ID %s\n' "$buddy_image_id"
}
prepare_buddy_release
```

The Compose command clears inherited values for the production file’s
interpolation variables so the protected environment file supplies them.
Continue only if release preparation succeeds. Save the override with the release record. Record the exact checkout commit
and base Compose path, the Compose project name, and the absolute paths to
the saved override and protected environment file. Keep a release-specific
protected copy of the environment file or a reference to an immutable
version in the approved secret store. Record the image tag and verified
image ID together. Keep credential values in the protected store.

Before probing permissions, verify the resolved bind source against the
approved release record. This requires Python 3 on the deployment host.

```bash
unset expected_binding
expected_binding=$(
  set -e -o pipefail
  read -r -p 'Approved absolute persistent root from the release record: ' approved_root
  test "${approved_root:0:1}" = /
  "${buddy_compose[@]}" config --format json | python3 -c '
import json
import sys

service = json.load(sys.stdin)["services"]["buddy"]
volumes = service.get("volumes", [])
mounts = [mount for mount in volumes if mount.get("target") == "/var/lib/buddy"]
if len(mounts) != 1 or mounts[0].get("type") != "bind" or mounts[0].get("source") != sys.argv[1]:
    sys.exit("Resolved Buddy persistent mount does not match the approved path")

ports = service.get("ports", [])
if len(ports) != 1:
    sys.exit("Expected exactly one published Buddy port")
port = ports[0]
published = str(port.get("published", ""))
if (port.get("host_ip") != "127.0.0.1" or port.get("target") != 8000
    or port.get("protocol", "tcp") != "tcp"
    or not published.isascii() or not published.isdecimal()
    or len(published) > 5 or not 1 <= int(published) <= 65535):
    sys.exit("Expected a fixed Buddy loopback TCP binding to container port 8000")
print(f"127.0.0.1:{published}")
' "$approved_root"
)
```

Require the mount and port checks to pass before continuing.

Before applying migrations or starting Buddy, check the configured mount with
the release image's default user. This checks permissions without writing files
or starting the application.

```bash
"${buddy_compose[@]}" run --rm --no-deps --no-build --pull never --entrypoint /bin/sh buddy -ec '
  test "$(id -u):$(id -g)" = 10001:10001
  for directory in managed artifacts sessions worldgraph; do
    path="/var/lib/buddy/$directory"
    if ! { test -d "$path" && test -r "$path" && test -w "$path" && test -x "$path"; }; then
      printf "Buddy release user cannot access %s\n" "$path" >&2
      exit 1
    fi
  done
'
```

Require the access probe to succeed before continuing.

Apply only the production migrations confirmed in step 2 through their owning procedures. Buddy expects the database to be ready at startup.

```bash
(
  set -e
  : "${expected_binding:?Run the resolved mount and port checks first}"
  "${buddy_compose[@]}" up -d --no-build --pull never --wait --wait-timeout 330 buddy
  buddy_container=$("${buddy_compose[@]}" ps -q buddy)
  actual_image=$(docker inspect "$buddy_container" --format '{{.Image}}')
  test "$actual_image" = "$buddy_image_id"
  read -r -p 'Approved absolute persistent root from the release record: ' approved_root
  test "${approved_root:0:1}" = /
  actual_root=$(docker inspect --format '{{range .Mounts}}{{if and (eq .Type "bind") (eq .Destination "/var/lib/buddy")}}{{.Source}}{{end}}{{end}}' "$buddy_container")
  if [[ "$actual_root" != "$approved_root" ]]; then
    printf 'Buddy persistent mount mismatch: expected %s, found %s\n' "$approved_root" "$actual_root" >&2
    exit 1
  fi
  actual_binding=$("${buddy_compose[@]}" port buddy 8000)
  if [[ ! "$actual_binding" =~ ^127\.0\.0\.1:([1-9][0-9]{0,4})$ ]] || (( BASH_REMATCH[1] > 65535 )); then
    printf 'Expected a single Buddy loopback binding, found %s\n' "$actual_binding" >&2
    exit 1
  fi
  if [[ "$actual_binding" != "$expected_binding" ]]; then
    printf 'Buddy binding changed: expected %s, found %s\n' "$expected_binding" "$actual_binding" >&2
    exit 1
  fi
  buddy_local="http://$actual_binding"
  printf 'Verified Buddy upstream: %s\n' "$buddy_local"
  curl -fsS "$buddy_local/health/live"
  curl -fsS "$buddy_local/health/ready"
  bash scripts/check_hosted_spa.sh "$buddy_local"
  buddy_status=$(curl -sS -o /dev/null -w '%{http_code}' "$buddy_local/api/auth/current-user")
  test "$buddy_status" = 401
)
```

The 330-second wait allows for the 90-second health start period, three
60-second probe intervals, up to 10 seconds per probe, and scheduling margin.
If the wait fails, stop the smoke checks and inspect the service. A container
can remain running after the wait expires.

```bash
"${buddy_compose[@]}" ps -a buddy
"${buddy_compose[@]}" logs --tail 100 buddy
```

Require the expected image ID, a loopback binding, successful health and SPA requests, and a signed-out `401`. If readiness fails, check database connectivity, schema revisions, and directory access before continuing.

Before public cutover, record the running container's log driver and configured
rotation limits. Run this on the deployment host:

```bash
(
  set -e
  buddy_container=$("${buddy_compose[@]}" ps -q buddy)
  test -n "$buddy_container"
  docker inspect --format '{{with .HostConfig.LogConfig}}{{.Type}} max-size={{index .Config "max-size"}} max-file={{index .Config "max-file"}}{{end}}' "$buddy_container"
)
```

For a driver that manages retention outside Docker, verify its policy with the
host operator. An empty limit in this output requires checking the effective
policy. If retention is unbounded, agree on a cap and verify rotation and access
to recent startup logs on a disposable stack before exposing Buddy publicly.

## 4. Verify DNS, TLS, and the proxy

Record the existing Nginx configuration. Install the [streaming proxy fragment](../../deploy/production/nginx-buddy.conf) in the selected Buddy TLS virtual host and match its upstream to the verified URL printed in step 3. Use the edge owner's DNS and certificate procedures for records, issuance, and renewal.

```bash
sudo nginx -t && sudo systemctl reload nginx
```

From an external client, compare both DNS address families against the expected edge and verify TLS with normal hostname and certificate validation. An absent AAAA record is acceptable for an IPv4-only edge.

```bash
buddy_domain=buddy.dungeonmind.net
dig +short A "$buddy_domain"
dig +short AAAA "$buddy_domain"
(
  set -e
  buddy_url="https://$buddy_domain"
  curl -fsS "$buddy_url/health/live"
  curl -fsS "$buddy_url/health/ready"
  bash scripts/check_hosted_spa.sh "$buddy_url"
  buddy_status=$(curl -sS -o /dev/null -w '%{http_code}' "$buddy_url/api/auth/current-user")
  test "$buddy_status" = 401
)
```

Probe each published address directly from an external client with connectivity
to its address family. Keep the hostname in the URL so curl sends the correct
TLS server name and validates the certificate against it.

```bash
(
  set -e -o pipefail
  buddy_addresses() {
    local record_type=$1 reply
    reply=$(dig +noall +comments +answer "$record_type" "$buddy_domain") || return 1
    if [[ "$reply" != *"status: NOERROR,"* ]]; then
      printf 'DNS lookup failed for %s %s\n%s\n' "$buddy_domain" "$record_type" "$reply" >&2
      return 1
    fi
    awk -v type="$record_type" '$4 == type {print $5}' <<<"$reply"
  }
  buddy_ipv4=$(buddy_addresses A)
  buddy_ipv6=$(buddy_addresses AAAA)
  if [[ -z "$buddy_ipv4" && -z "$buddy_ipv6" ]]; then
    echo "No A or AAAA records found for $buddy_domain" >&2
    exit 1
  fi
  for buddy_address in $buddy_ipv4 $buddy_ipv6; do
    buddy_target=$buddy_address
    if [[ "$buddy_address" == *:* ]]; then
      buddy_target="[$buddy_address]"
    fi
    echo "Checking HTTPS at $buddy_address"
    curl --noproxy '*' --resolve "$buddy_domain:443:$buddy_target" \
      --connect-timeout 5 --max-time 15 -fsS -o /dev/null \
      "https://$buddy_domain/health/live"
  done
)
```

The HTTP checks verify that each path serves the app. Use the browser steps to
verify that each URL renders the intended page.

## 5. Smoke-test real browser authentication and routing

1. Open Buddy in a fresh browser profile and check that the startup request `GET /api/auth/session` returns `401`.
2. Use Buddy's sign-in entry point. Complete the real DungeonMind Server sign-in and verify the browser returns to Buddy.
3. In the browser network panel, require `200` from `GET /api/auth/session` and `GET /api/live/world-containers`. Verify the assigned World appears and access matches the approved assignments.
4. Open the landing page at `/`, select the approved World, and follow its
   Graph link. Verify `/graph` renders the graph and opens object details. Check
   that the viewer offers read controls and that a direct link to an unassigned
   World is denied. Open `/plan`, `/play`, `/surface`, `/build`, `/ingest`, and
   `/combat` directly and confirm they show the hosted unavailable page. Verify the hosted API denies graph
   authoring and recap ingestion. Use the
   [frontend guide](../../apps/live-control-ui/README.md#legacy-surface-board)
   for the local operator Chat smoke.
5. Verify the navbar identifies the signed-in DungeonMind account and keeps World selection in a separate control. Open the account menu and sign out. Confirm `POST /api/auth/logout` succeeds, then reload and require `401` from `GET /api/auth/session`. Probe `GET /api/live/world-containers` directly from the signed-out browser and require `401`; the UI may skip this request. Record the result and timestamp without saving cookies or credentials.

## 6. Close out or roll back

Record the serving image ID or digest and the results of the restore, edge, and browser checks. If a rollout check fails after the proxy reload, restore the prior proxy configuration or withdraw the route for a first deployment, then run `sudo nginx -t && sudo systemctl reload nginx`.

Restore the prior image with its saved Compose configuration only after verifying compatibility with the current data and schema. If they are incompatible, use the agreed forward repair or coordinated restore for both authorities and their associated files. Rerun the relevant health and authentication checks and record the serving release.

For a compatible image rollback, run this from the prior release's reviewed
checkout. Use its saved project name, protected environment file, image
override, image tag, and image ID from the release record. Use the same Docker context as the prior release.

```bash
(
  set -e
  read -r -p 'Prior release commit SHA: ' prior_commit
  read -r -p 'Prior Compose project: ' prior_project
  read -r -p 'Absolute path to prior protected environment file: ' prior_env
  read -r -p 'Absolute path to prior image override: ' prior_override
  read -r -p 'Prior image tag: ' prior_tag
  read -r -p 'Prior image ID: ' prior_id
  test "$(git rev-parse HEAD)" = "$prior_commit"
  test -z "$(git status --porcelain)"
  test -n "$prior_project"
  test "${prior_env:0:1}" = / && test -r "$prior_env" || exit 1
  test "${prior_override:0:1}" = / && test -r "$prior_override" || exit 1
  test -n "$prior_tag"
  test -n "$prior_id"
  prior_compose=(env
    -u AUTH_TRUSTED_FRONTEND_ORIGINS
    -u BUDDY_HTTP_BIND_PORT
    -u BUDDY_PERSISTENT_ROOT
    -u DMB_HOSTED_WORLD_ACCESS_JSON
    -u DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL
    -u DUNGEONMIND_SERVER_API_ORIGIN
    -u DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL
    docker compose --project-name "$prior_project" --env-file "$prior_env"
    -f deploy/production/compose.production.yaml -f "$prior_override")
  configured_image=$("${prior_compose[@]}" config --images buddy)
  test "$configured_image" = "$prior_tag"
  local_image=$(docker image inspect "$prior_tag" --format '{{.Id}}')
  test "$local_image" = "$prior_id"
  "${prior_compose[@]}" up -d --no-build --pull never --wait --wait-timeout 330 buddy
  prior_container=$("${prior_compose[@]}" ps -q buddy)
  actual_image=$(docker inspect "$prior_container" --format '{{.Image}}')
  test "$actual_image" = "$prior_id"
)
```

If this block fails, inspect the prior service before proceeding. After it
passes, use the prior release's smoke procedure with the restored proxy.

### Hand off restart ownership

Before closing the release, record who restarts Buddy after a Docker daemon or
host reboot and which service unit or operator procedure they use. The example
Compose service has no restart policy. If the host already manages Buddy
through a service unit, verify that the unit uses the saved release checkout,
Compose project, and protected configuration.

The restart owner rehearses recovery on an isolated stack before relying on
the procedure. After restarting, verify the serving image ID, approved
persistent mount, loopback binding, and readiness. Record the result with the
release evidence.

### Retire superseded release images

After the rollback window closes, the release operator inventories Buddy tags
and records Docker disk use before and after removing any approved retired tag.
Docker reports shared layers separately, so use the observed change in disk use
when recording recovered space.

```bash
docker image ls dungeonmindbuddy --no-trunc
docker system df -v
```

Compare the inventory with the serving and rollback image IDs in the release
records. Retain both images and their release-scoped configuration. For each
retired tag, run the following in the deployment Docker context during a window
with no concurrent release changes. Enter the full image IDs from the verified
records.

```bash
(
  set -e
  read -r -p 'Retired Buddy image tag: ' retired_tag
  read -r -p 'Serving image ID: ' serving_id
  read -r -p 'Rollback image ID: ' rollback_id
  [[ "$retired_tag" =~ ^dungeonmindbuddy:[0-9a-f]{40}$ ]]
  [[ "$serving_id" =~ ^sha256:[0-9a-f]{64}$ ]]
  [[ "$rollback_id" =~ ^sha256:[0-9a-f]{64}$ ]]
  retired_id=$(docker image inspect --format '{{.Id}}' "$retired_tag")
  test "$retired_id" != "$serving_id"
  test "$retired_id" != "$rollback_id"
  containers=$(docker ps -aq --filter "ancestor=$retired_id")
  test -z "$containers"
  docker image rm "$retired_tag"
)
```

Repeat the inventory afterward and record the removed tag and measured change.
Build cache retention belongs to the operator of the builder. Use a dedicated
Buddy builder or coordinate retention with the owners of a shared builder.
