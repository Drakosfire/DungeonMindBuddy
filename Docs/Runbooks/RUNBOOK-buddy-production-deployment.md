# Deploy Buddy to buddy.dungeonmind.net

Run from the root of the reviewed Buddy checkout on the selected deployment host. Use one Bash session for the command blocks. Run the public checks from a separate client. Advance only when the expected result for the current step is recorded.

## 1. Prepare the release record

Record the host and SSH alias, release commit, image ID or registry digest, Compose project, host bind port, Nginx virtual host, DNS records, certificate owner, and rollback owner. Record the approved DMS test account and expected World, both database owners and migration heads, and the backup and restore evidence. Keep credentials and session cookies in their designated stores.

Run the [host inventory](../Plans/RUNBOOK-HOSTED-read-only-host-inventory.md).

```bash
bash scripts/host_inventory.sh
docker compose version
docker info --format '{{.DockerRootDir}}'
```

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

Test required migrations against the restored copies. Before applying them to production, record whether the previous release can use the resulting schema and data. If it cannot, record the forward repair or coordinated recovery procedure and its owner.

## 3. Build and start on loopback

Provision a protected Compose environment file outside the checkout with the variables required by the [production Compose example](../../deploy/production/compose.production.yaml). Use the approved DMS HTTPS origin, trust `https://buddy.dungeonmind.net`, and configure the approved World assignments and both database URLs. Set `BUDDY_PERSISTENT_ROOT` to the durable host directory. Create its `managed`, `artifacts`, `sessions`, and `worldgraph` directories with access for container UID/GID 10001.

```bash
read -r -p 'Approved release commit: ' buddy_release
read -r -p 'Absolute path to the protected Compose environment file: ' buddy_env
read -r -p 'Host loopback port from that file [8080]: ' buddy_port
buddy_port=${buddy_port:-8080}
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
  local -a candidate_compose=(docker compose --project-name "$buddy_project" --env-file "$buddy_env"
    -f deploy/production/compose.production.yaml -f "$buddy_override")
  "${candidate_compose[@]}" config --quiet || return
  buddy_compose=("${candidate_compose[@]}")
  printf 'Release image ID %s\n' "$buddy_image_id"
}
prepare_buddy_release
```

Continue only if release preparation succeeds. Save the override with the release record. Apply only the production migrations confirmed in step 2 through their owning procedures. Buddy expects the database to be ready at startup.

```bash
(
  set -e
  "${buddy_compose[@]}" up -d --no-build --pull never --wait --wait-timeout 330 buddy
  buddy_container=$("${buddy_compose[@]}" ps -q buddy)
  actual_image=$(docker inspect "$buddy_container" --format '{{.Image}}')
  test "$actual_image" = "$buddy_image_id"
  actual_binding=$("${buddy_compose[@]}" port buddy 8000)
  test "$actual_binding" = "127.0.0.1:$buddy_port"
  buddy_local="http://127.0.0.1:$buddy_port"
  curl -fsS "$buddy_local/health/live"
  curl -fsS "$buddy_local/health/ready"
  for buddy_path in / /graph; do
    buddy_status=$(curl -fsS -H 'Accept: text/html' -o /dev/null -w '%{http_code}' "$buddy_local$buddy_path")
    printf '%s %s\n' "$buddy_status" "$buddy_path"
    test "$buddy_status" = 200
  done
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

## 4. Verify DNS, TLS, and the proxy

Record the existing Nginx configuration. Install the [streaming proxy fragment](../../deploy/production/nginx-buddy.conf) in the selected Buddy TLS virtual host and match its upstream port to step 3. Use the edge owner's DNS and certificate procedures for records, issuance, and renewal.

```bash
sudo nginx -t && sudo systemctl reload nginx
```

From an external client, compare both DNS address families against the expected edge and verify TLS with normal hostname and certificate validation. An absent AAAA record is acceptable for an IPv4-only edge.

```bash
buddy_domain=buddy.dungeonmind.net
dig +short A "$buddy_domain"
dig +short AAAA "$buddy_domain"
openssl s_client -connect "$buddy_domain:443" -servername "$buddy_domain" \
  -verify_hostname "$buddy_domain" -verify_return_error -brief </dev/null
buddy_url="https://$buddy_domain"
curl -fsS "$buddy_url/health/live"
curl -fsS "$buddy_url/health/ready"
(
  set -e
  for buddy_path in / /graph; do
    buddy_status=$(curl -fsS -H 'Accept: text/html' -o /dev/null -w '%{http_code}' "$buddy_url$buddy_path")
    printf '%s %s\n' "$buddy_status" "$buddy_path"
    test "$buddy_status" = 200
  done
) &&
test "$(curl -sS -o /dev/null -w '%{http_code}' "$buddy_url/api/auth/current-user")" = 401
```

The HTTP checks verify that each path serves the app. Use the browser steps to
verify that each URL renders the intended page.

## 5. Smoke-test real browser authentication and routing

1. Open Buddy in a fresh browser profile and check that `GET /api/auth/current-user` returns `401`.
2. Use Buddy's sign-in entry point. Complete the real DungeonMind Server sign-in and verify the browser returns to Buddy.
3. In the browser network panel, require `200` from `GET /api/auth/current-user` and `GET /api/live/world-containers`. Verify the assigned World appears and access matches the approved assignments.
4. Open the landing page at `/`, select the approved World, and follow its
   Graph link. Verify `/graph` renders the graph and opens object details. Check
   that the viewer offers read controls and that a direct link to an unassigned
   World is denied. Open `/plan`, `/play`, and `/surface` directly and confirm
   they show the hosted unavailable page. Verify the hosted API denies graph
   authoring and recap ingestion. Use the
   [frontend guide](../../apps/live-control-ui/README.md#legacy-surface-board)
   for the local operator Chat smoke.
5. Verify the navbar identifies the signed-in DungeonMind account and keeps World selection in a separate control. Open the account menu and sign out. Reload and require `401` from both endpoints. Record the result and timestamp without saving cookies or credentials.

## 6. Close out or roll back

Record the serving image ID or digest and the results of the restore, edge, and browser checks. If a rollout check fails after the proxy reload, restore the prior proxy configuration or withdraw the route for a first deployment, then run `sudo nginx -t && sudo systemctl reload nginx`.

Restore the prior image with its saved Compose configuration only after verifying compatibility with the current data and schema. If they are incompatible, use the agreed forward repair or coordinated restore for both authorities and their associated files. Rerun the relevant health and authentication checks and record the serving release.
