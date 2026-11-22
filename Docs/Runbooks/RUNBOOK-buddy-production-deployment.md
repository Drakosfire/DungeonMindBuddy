# Deploy Buddy to buddy.dungeonmind.net

Run from the root of the reviewed Buddy checkout on the selected deployment host. Use one Bash session for the command blocks. Run the public checks from a separate client using the helper from the same reviewed Buddy checkout or a copy of that helper from the release commit. Advance only when the expected result for the current step is recorded.

Record release-host and public validation outcomes using the [release rehearsal checklist](RELEASE-REHEARSAL-buddy-checklist.md). It summarizes pending evidence and does not replace the steps below.

## Agent-assisted upgrades through SSH

Use the assigned active [deployment handoff](../Plans/HANDOFF-DEPLOY-agent-assisted-ssh-upgrade.md)
for the current release identity, authorization, and unresolved gates.

Use this workflow for an existing hosted installation. The operator owns
production changes. SSH access is temporary and release-scoped. On this host,
the `alan` account can access Docker; Docker access is effectively host-root
access. Treat it as privileged, not as a general agent credential. An agent
may run only the exact read-only probes or exact reviewed-release preparation
command authorized by the active handoff. The agent must not read environment
values, run arbitrary Docker or Compose commands, access database credentials,
or perform production backup, restore, migration, or cutover operations.

The current Buddy production host is `srv586875` and the SSH target is
`alan@191.101.14.169`. Use this target from the deployment workstation.

1. **Establish temporary SSH access.** The operator loads the existing deploy
   key on the workstation with `ssh-add -t 1h ~/.ssh/id_rsa` (substitute the
   configured key path). Never copy the private key into a checkout, chat, or
   server. Use the existing trusted host key. Check noninteractive access with
   `ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=6 -o StrictHostKeyChecking=yes alan@191.101.14.169 'hostname && whoami'`.
   Require output `srv586875` and `alan`; stop if the host or account differs.
   If the agent refuses signing, have the operator refresh the key. Host-key
   errors require verifying the host identity through the established channel.
   The temporary identity is for the explicitly assigned release only; do not
   leave it loaded or reuse it for another task.
2. **Pin and inspect the release.** Fetch the owning remote. Record the exact
   reviewed source SHA and frontend verification result. Inspect the running
   container's image, health, and Compose project labels with `docker inspect
   --format`. Record the app and Graph migration revisions using the read-only
   checks below. Compare the candidate against the serving SHA. For a bounded
   hotfix, transplant the reviewed change onto the serving revision, verify
   the resulting diff, and run the verifier against that exact release SHA.
   For a migration-bearing release, use the backup, rehearsal, and separate
   migration credentials in this runbook.
3. **Stage and build.** Check host capacity first. Use a clean checkout and
   `scripts/prepare_buddy_release_image.sh <release-sha>`. If the server has
   no checkout, stream `git archive <release-sha>` over SSH into a fresh
   release directory and run `docker build --target api -f Dockerfile.production
   --label "org.opencontainers.image.revision=<release-sha>"
   -t "dungeonmindbuddy:<release-sha>" .` there. Inspect the completed image
   ID and revision label. Stage a Compose override that sets only
   `services.buddy.image` to the exact tag. Verify the prior image is still
   available and retain the previous Compose configuration for rollback.
4. **Hand off production commands to the operator.** Send one exact command
   with its expected output, wait for the operator to run it in the cloud
   terminal, and verify that output before giving the next command. Do not
   automate `sudo`, pass a password through SSH, or combine backup, migration,
   and cutover into one opaque command. The operator runs the privileged
   Compose switch in the cloud terminal. Recheck the serving image against
   the recorded expected SHA. Reuse the running container's ordered
   `com.docker.compose.project.config_files`, project name, and protected
   environment file. On the current server that file is
   `/srv/dungeonmindbuddy/secrets/buddy.env`. The operator runs the privileged
   Compose command with those inputs and the new image override last.
   Immediately before cutover, require the mutable tag still resolves to the
   immutable image ID recorded by `prepare_buddy_release`; stop if it differs:
   `test "$(docker image inspect --format '{{.Id}}' "$buddy_tag")" = "$buddy_image_id"`.
   Confirm `config --images buddy` resolves the exact staged tag, then run
   `up -d --no-deps --pull never --wait --wait-timeout 180 buddy`. Afterward,
   verify the running service container against the same image ID and release
   SHA:
   `running_buddy=$("${buddy_compose[@]}" ps -q buddy) && test -n "$running_buddy" && test "$(docker inspect --format '{{.Image}}' "$running_buddy")" = "$buddy_image_id" && test "$(docker inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$running_buddy")" = "$buddy_release"`.
   If either identity differs, stop and follow the rollback procedure. Keep the
   root-owned environment file in place and avoid printing rendered Compose
   config, which can contain secrets. Use narrowly formatted
   `docker inspect --format` queries; never print the container's full
   inspection document or environment.
5. **Verify and settle.** Inspect the running revision and health again
   over SSH, check the public route, and reproduce the release-specific
   behavior in a signed-in browser. If health or the smoke test fails,
   follow the rollback procedure below. Retire old Buddy images only after
   the rollback window and the retention checks in this runbook.

## 1. Prepare the release record

Record the host and SSH alias, release commit, image ID or registry digest, Compose project, host bind port, approved absolute persistent root, Nginx virtual host, DNS records, certificate owner, and rollback owner. Record the approved DMS test account and expected World, both database owners and migration heads, and the backup and restore evidence. Keep credentials and session cookies in their designated stores.

Run the [host inventory](../Plans/RUNBOOK-HOSTED-read-only-host-inventory.md).

```bash
bash scripts/host_inventory.sh
docker compose version --short
docker buildx version
docker info --format '{{.DockerRootDir}}'
```

Require working Docker Compose and Buildx installations before proceeding.

Record disk and RAM minimums in MiB for the release, based on the build and
upgrade rehearsal. Include room for the serving and rollback images in the Docker
minimum and backup and migration headroom in the persistent minimum. Run on the
Linux deployment host with the same default local Docker context used for deployment.

```bash
read -r -p 'Approved absolute persistent root: ' buddy_persistent_root
read -r -p 'Minimum available Docker disk MiB: ' buddy_docker_mib
read -r -p 'Minimum available persistent disk MiB: ' buddy_persistent_mib
read -r -p 'Minimum available RAM MiB: ' buddy_ram_mib
python3 scripts/check_buddy_release_capacity.py --persistent-root "$buddy_persistent_root" \
  --min-docker-mib "$buddy_docker_mib" --min-persistent-mib "$buddy_persistent_mib" \
  --min-ram-mib "$buddy_ram_mib"
```

Continue only on a successful result. If both directories share a filesystem,
the check requires their combined headroom. Confirm the selected loopback port is available for a first deploy or is owned by the Buddy service for an upgrade. The checked-in defaults are host loopback port 8080 and container port 8000.

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

Provision a protected Compose environment file outside the checkout with the variables required by the [production Compose example](../../deploy/production/compose.production.yaml). Use the approved DMS HTTPS origin, trust `https://buddy.dungeonmind.net`, and configure the approved World assignments and both database URLs. Set the private statblock API origin as reachable from the Buddy container and put its internal API key in this same protected file. Host loopback inside the container is the container itself. Set `BUDDY_PERSISTENT_ROOT` to the absolute path of the approved durable host directory. Create its `managed`, `artifacts`, `sessions`, and `worldgraph` directories with access for container UID/GID 10001.

For PDF extraction, run the GenerationEngine private OCR worker at
`3e4f34ee5e6c99517c0cb7163d782a7695199071` on the approved GPU host. Record
the CUDA environment, GPU UUID, checkpoint revision and checksums, and private
route owner. Verify the pinned checkpoint before loading its executable model
code. Keep the OCR listener on loopback and use a private authenticated tunnel
or TLS termination on a private network. In the protected Compose file, set
`BUDDY_OCR_REMOTE_URL` to the container-reachable `/ocr` endpoint and
`BUDDY_OCR_REMOTE_TOKEN` to the token provisioned on the worker. For an
`http://` endpoint use an encrypted tunnel for off-host traffic. The Buddy host
can run without CUDA.

For the workstation pilot, have the tailnet owner grant only the cloud
Buddy host access to TCP port 18798 on the GPU workstation. Check effective
policy for broader grants before publishing the listener. Start the worker
under the workstation service account using the pinned CUDA Python environment
and checkpoint. Supply `GENERATIONENGINE_OCR_TOKEN` from its protected service
environment. Verify the worker listens on `127.0.0.1:8798`.

On the GPU workstation, the administrator configures [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).

```bash
sudo tailscale serve --bg --tcp=18798 tcp://127.0.0.1:8798
tailscale serve status
```

Use `http://<gpu-workstation-tailnet-address>:18798/ocr` in Buddy's
protected environment. Verify that the candidate container can complete the
OCR probe below and that an unauthorized tailnet node cannot reach port 18798.
Use the worker's JSON HTTP status, elapsed milliseconds, and bytes read to
monitor volume, failures, and latency in the restricted service journal.
Record the worker revision, route owner, and credential reference without
copying the token into the release record. To withdraw the route without
touching other Serve listeners, run `sudo tailscale serve --tcp=18798 off`
on the workstation and verify that the candidate can no longer reach it.


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
  buddy_image_id=$(bash scripts/prepare_buddy_release_image.sh "$buddy_release") || return
  buddy_override=$(mktemp) || return
  printf 'services:\n  buddy:\n    image: %s\n' "$buddy_tag" > "$buddy_override" || return
  local -a candidate_compose=(env
    -u AUTH_TRUSTED_FRONTEND_ORIGINS
    -u OPENAI_API_KEY
    -u BUDDY_HTTP_BIND_PORT
    -u BUDDY_OCR_REMOTE_URL
    -u BUDDY_OCR_REMOTE_TOKEN
    -u BUDDY_OCR_RUNTIME_ROOT
    -u BUDDY_OCR_GPU_ID
    -u BUDDY_PERSISTENT_ROOT
    -u DMB_HOSTED_WORLD_ACCESS_JSON
    -u DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL
    -u DUNGEONMIND_SERVER_API_ORIGIN
    -u DUNGEONMIND_STATBLOCKS_BASE_URL
    -u DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY
    -u DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL
    docker compose --project-name "$buddy_project" --env-file "$buddy_env"
    -f deploy/production/compose.production.yaml
    -f deploy/production/compose.logging.yaml -f "$buddy_override")
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

Image preparation builds a missing release image and reuses an existing image
only when its revision label matches the full approved SHA. A conflicting tag
stops preparation without replacing the image. Compare the returned image ID
with the saved release record on reruns. Run one preparation at a time in the
deployment Docker context.

The logging override explicitly selects `json-file` with `max-size=10m` and
`max-file=3`, retaining approximately 30 MB of container stdout/stderr per
container rather than inheriting an uncapped daemon default. This budget does
not cover application files, image layers, build caches, or other containers.
If the release needs another budget or a centrally managed driver, record it
and set the logging configuration in the saved release override. Verify the
effective configuration below; existing containers keep their previous policy
until recreated. Do not recreate the serving container just to test rotation.

The Compose command clears inherited values for the production file’s
interpolation variables so the protected environment file supplies them.
Continue only if release preparation succeeds. Save the override with the release record. Record the exact checkout commit
and both versioned Compose paths, the Compose project name, and the absolute paths to
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

Before applying production migrations, compare the aliases from step 2
with the actual connections from the release image. Run this from the host
where the aliases were verified, using TCP aliases. A mismatch stops the release. If a proxy or
replica changes the reported server address, have the database owner verify
and document the mapping before proceeding.

```bash
(
  set -e
  identity_sql="SELECT json_build_array(current_database(), current_user,
    host(inet_server_addr()), inet_server_port(),
    (SELECT oid FROM pg_database WHERE datname = current_database()))::text"
  for db_service in buddy-app buddy-worldgraph; do
    case "$db_service" in
      buddy-app) db_variable=DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL ;;
      buddy-worldgraph) db_variable=DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL ;;
    esac
    expected=$(psql "service=$db_service" -XAt -v ON_ERROR_STOP=1 -c "$identity_sql")
    actual=$("${buddy_compose[@]}" run --rm --no-deps --pull never -T \
      --entrypoint python buddy -c '
import os
import sys

import psycopg

try:
    with psycopg.connect(os.environ[sys.argv[1]], connect_timeout=5) as connection:
        print(connection.execute(sys.argv[2]).fetchone()[0])
except (KeyError, psycopg.Error, ValueError):
    sys.exit("Could not read the release database identity")
' "$db_variable" "$identity_sql")
    if [[ -z "$expected" || "$expected" != "$actual" ]]; then
      printf 'Database identity mismatch for %s\n' "$db_service" >&2
      exit 1
    fi
    printf 'Verified database identity for %s\n' "$db_service"
  done
)
```

Before applying migrations or starting Buddy, check the configured mount with
the release image's default user. This checks permissions without writing files
or starting the application.

```bash
"${buddy_compose[@]}" run --rm --no-deps --pull never --entrypoint /bin/sh buddy -ec '
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

If the mount probe succeeds but prompt capture reports
`prompt_evidence_unavailable` or `prompt_evidence_directory_not_private`,
inspect the existing `artifacts/out/agent_request_evidence` path under
`BUDDY_PERSISTENT_ROOT`. Buddy opens the artifact root and each of those
subdirectories without following symlinks. The final directory must be
owned by UID 10001 and have mode `0700`. On a fresh mount Buddy creates
the missing subdirectories when it first stores prompt evidence.

Probe the private statblock provider from a one-off candidate container before
migrating or replacing the serving container. The client uses the protected
settings and emits only the probe outcome.

```bash
"${buddy_compose[@]}" run --rm --no-deps --no-build -T buddy python - <<'PYTHON'
from apps.live_control_server.integrations.dungeonmind_statblocks.client import build_statblock_v1_client

try:
    client = build_statblock_v1_client()
    try:
        report = client.get_readiness()
        capabilities = set(client.get_health().capabilities)
    finally:
        client.close()
except Exception:
    raise SystemExit("Private statblock provider probe failed")
if report.status != "ready" or not report.read_routes_enabled:
    raise SystemExit("Private statblock provider is not ready for saved revisions")
if not {"statblock_create", "statblock_revision_append"} <= capabilities:
    raise SystemExit("Private statblock provider is missing required write capabilities")
print("Private statblock provider ready")
PYTHON
```

Continue only when the candidate-container probe succeeds.

Run an actual OCR probe from the candidate container before migrations or
cutover. This exercises the container route, bearer credential, checkpoint,
and GPU on the OCR host.

```bash
"${buddy_compose[@]}" run --rm --no-deps --no-build -T buddy python - <<'PYTHON'
from io import BytesIO
from PIL import Image, ImageDraw
from apps.live_control_server.services.build_pdf_ocr import read_crop_png

image = Image.new("RGB", (512, 160), "white")
caption = Image.new("RGB", (128, 40), "white")
ImageDraw.Draw(caption).text((8, 12), "DUNGEON BUDDY", fill="black")
image.paste(caption.resize(image.size, Image.Resampling.NEAREST))
capture = BytesIO()
image.save(capture, format="PNG")
try:
    result = read_crop_png(capture.getvalue())
except Exception:
    raise SystemExit("Private OCR inference failed in the candidate container")
if "DUNGEONBUDDY" not in "".join(c for c in result["text"].upper() if c.isalpha()):
    raise SystemExit("Private OCR did not recognize the release probe text")
print("Private OCR inference ready")
PYTHON
```

Continue only after the probe recognizes the text. Keep the private route and worker release references in the release record for recovery.

Set `OPENAI_API_KEY` in the protected Compose file. Verify the extraction model
from the candidate using only this synthetic text. A structured incomplete
result is expected for a source with no statistics.

```bash
"${buddy_compose[@]}" run --rm --no-deps --no-build -T buddy python - <<'PYTHON'
import asyncio
from apps.live_control_server.services.build_pdf_statblock_extraction import extract_statblock

try:
    result = asyncio.run(extract_statblock(["Synthetic release probe. No creature statistics are present."]))
except Exception:
    raise SystemExit("Structured statblock extraction provider probe failed")
if result.status != "incomplete":
    raise SystemExit("Structured extraction did not report missing source evidence")
print("Structured extraction provider ready")
PYTHON
```

Continue only after the provider returns the expected structured result.

Apply only the production migrations confirmed in step 2 through their owning procedures. Buddy expects the database to be ready at startup.


The image healthcheck probes `/health/live` with a three-second HTTP timeout.
Production Compose overrides it with `/health/ready` and a five-second HTTP
timeout. Readiness includes dependency checks.

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
  curl --connect-timeout 5 --max-time 15 -fsS "$buddy_local/health/live"
  curl --connect-timeout 5 --max-time 15 -fsS "$buddy_local/health/ready"
  bash scripts/check_hosted_spa.sh "$buddy_local"
  buddy_status=$(curl --connect-timeout 5 --max-time 15 -sS -o /dev/null -w '%{http_code}' "$buddy_local/api/auth/current-user")
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

Require the running policy to match the release record (by default,
`json-file max-size=10m max-file=3`). Verify rotation and access to recent
diagnostics with a disposable container using that policy, not the serving
container. Keep [#3538](https://github.com/Drakosfire/DungeonMindBuddy/issues/3538)
open until the selected host's effective policy and rotation evidence are recorded.

For a driver that manages retention outside Docker, verify its policy with the
host operator. An empty limit in this output requires checking the effective
policy. If retention is unbounded, agree on a cap and verify rotation and access
to recent startup logs on a disposable stack before exposing Buddy publicly.

## 4. Verify DNS, TLS, and the proxy

Record the existing Nginx configuration. Install the [hosted proxy fragment](../../deploy/production/nginx-buddy.conf) in the selected Buddy TLS virtual host and match all upstream directives to the verified URL printed in step 3. Use the edge owner's DNS and certificate procedures for records, issuance, and renewal.

After the canonical Buddy host passes sign-in and Build verification, configure DNS and TLS for `dungeonbuddy.net` using the edge owner's procedures. In its dedicated TLS server block, include [the vanity redirect fragment](../../deploy/production/nginx-buddy-vanity.conf). Run `nginx -t` before reloading. Verify the first response without following the redirect.

```bash
curl -sSI 'https://dungeonbuddy.net/build?world=pilot'
```

Expect HTTP 302 and `Location: https://buddy.dungeonmind.net/build?world=pilot`. Open the vanity URL in a signed-out browser and verify that DungeonMind Auth returns the pilot to the same Build deep link. To roll back the entry point, restore the previous vanity virtual host configuration, run `nginx -t`, and reload.

The hosted profile serves authentication, the SPA, and explicitly authorized
World-scoped API routes. Buddy's application policy determines which operations
are admitted; the proxy does not impose a read-only release scope. It buffers
requests and responses, leaves proxy caching
disabled, and uses 60-second upstream read and send timeouts. Before replacing
an existing location, have the edge owner inspect the effective configuration
and confirm which callers it serves. The exact PDF admission route permits
32 MiB at the edge, matching the application limit, and streams the request to
Buddy so the application can check access before consuming the body. Verify
upload through the TLS virtual host with a PDF larger than 1 MiB. The PDF review
extraction, validation, acceptance, and publication routes allow 600 seconds
between upstream reads so OCR and provider calls can finish. Verify extraction
and publication through the TLS route as part of release rehearsal.
A deployment that enables streamed Agent
turns needs a separately scoped location for the streaming endpoint and a smoke
test that confirms incremental events arrive through the proxy.

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
  curl --connect-timeout 5 --max-time 15 -fsS "$buddy_url/health/live"
  curl --connect-timeout 5 --max-time 15 -fsS "$buddy_url/health/ready"
  bash scripts/check_hosted_spa.sh "$buddy_url"
  buddy_status=$(curl --connect-timeout 5 --max-time 15 -sS -o /dev/null -w '%{http_code}' "$buddy_url/api/auth/current-user")
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
   World is denied. Follow World-scoped links to `/plan`, `/play`, `/build`,
   `/ingest`, `/combat`, and `/statblock`, retaining the selected World in each
   URL. A bare workspace URL without an admitted World should ask the user to
   choose one. These workspaces no longer share a blanket hosted-unavailable
   page; opening a workspace does not establish that every operation is enabled.

   Check the reviewed release's `HOSTED_WORLD_SCOPE_RESOLVERS` in
   [the API entry point](../../apps/live_control_server/main.py) and the
   [hosted request boundary](../../apps/live_control_server/services/hosted_auth.py)
   for the exact method/path policy. Registered operations still require their
   World/resource authorization and handler checks; authenticated requests to
   unregistered API routes remain denied. Qualify any write workflow separately
   against its approved disposable World and provider target, rather than
   requiring all authoring or recap ingestion to fail.

   `/surface` remains the legacy board. Use the
   [frontend guide](../../apps/live-control-ui/README.md#legacy-surface-board)
   for its local operator Chat smoke; a hosted board shell is not proof of that
   legacy workflow.
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
  prior_logging=()
  if [[ -f deploy/production/compose.logging.yaml ]]; then
    prior_logging=(-f deploy/production/compose.logging.yaml)
  fi
  prior_compose=(env
    -u AUTH_TRUSTED_FRONTEND_ORIGINS
    -u OPENAI_API_KEY
    -u BUDDY_HTTP_BIND_PORT
    -u BUDDY_OCR_REMOTE_URL
    -u BUDDY_OCR_REMOTE_TOKEN
    -u BUDDY_OCR_RUNTIME_ROOT
    -u BUDDY_OCR_GPU_ID
    -u BUDDY_PERSISTENT_ROOT
    -u DMB_HOSTED_WORLD_ACCESS_JSON
    -u DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL
    -u DUNGEONMIND_SERVER_API_ORIGIN
    -u DUNGEONMIND_STATBLOCKS_BASE_URL
    -u DUNGEONMIND_STATBLOCKS_INTERNAL_API_KEY
    -u DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL
    docker compose --project-name "$prior_project" --env-file "$prior_env"
    -f deploy/production/compose.production.yaml "${prior_logging[@]}" -f "$prior_override")
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
approved retired tag, run the retirement command in the deployment Docker
context with no concurrent release changes. Use the verified image IDs and run
it first without `--apply` to see the candidate and its stopped containers.

```bash
read -r -p 'Retired Buddy image tag: ' retired_tag
read -r -p 'Serving image ID: ' serving_id
read -r -p 'Rollback image ID: ' rollback_id
python3 scripts/retire_buddy_release.py --project "$buddy_project" \
  --retired-tag "$retired_tag" --serving-image "$serving_id" \
  --rollback-image "$rollback_id"
```

After verifying the candidate, repeat with `--apply`. The command removes only
the named release tag and stopped containers from the matching Buddy service.
Repeat it to verify that the retired tag is gone. Record the before and after
Docker disk use and available RAM. Shared image layers may remain in use.
Build cache retention belongs to the operator of the builder. Use a dedicated
Buddy builder or coordinate retention with the owners of a shared builder.
