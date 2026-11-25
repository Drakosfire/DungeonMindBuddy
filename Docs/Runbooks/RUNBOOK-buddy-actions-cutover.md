# Publish and deploy a Buddy image from GitHub Actions

Use this for a reviewed image-only release on the existing production Compose
configuration. Use the [production runbook](RUNBOOK-buddy-production-deployment.md)
for dependency, schema, proxy and persistent-state changes. For migration 0172,
retain the separate paired backup rehearsal and migration procedure.

## Routine image update

For an existing host with unchanged deployment configuration and compatible
data and schema, use [Publish and approve one release](#publish-and-approve-one-release)
and the activation steps below. Confirm the observed serving parent, pin the
candidate and compatible rollback image, keep the existing protected staging
and activation steps, confirm readiness, and smoke the changed workflow where
applicable. Use the one-time setup only when provisioning or changing that setup.
Reuse evidence for unchanged behavior on a serving port. Compare the effective
code and release settings and check differences that can affect the change.

Use the [production runbook](RUNBOOK-buddy-production-deployment.md) for first
deployment or for the affected boundary when changing database or persistent
state, dependencies that affect deployment, permissions, proxy, or recovery
compatibility. Record pending evidence and its owner at the delivery gate
where it applies.

## Submit parallel release work

Agents can review, test, and publish candidates in parallel. Submit each
approved candidate to the deployment workflow below with its immutable registry
digest, exact image ID, expected serving revision and image ID, and release
mode. Use the published run's digest and check the current serving receipt
before dispatch. Track the candidate SHA in the [deployment workflow's run
list](https://github.com/Drakosfire/DungeonMindBuddy/actions/workflows/deploy-buddy.yml).

GitHub runs one deployment at a time and allows up to 100 pending runs. It
orders the queue by when requests start waiting for the concurrency group.
One run owns staging, activation, public checks, and the resulting receipt.
The host deployment lock also protects against simultaneous host commands.

If another release changes the expected serving revision or image ID, the
host rejects the queued request before staging. Check the new serving receipt,
requalify rollback compatibility, and submit fresh pins. For a serving overlay,
its owner must also rebuild and publish against the new serving parent.
The queue continues with the next request. Inspect each run for its own
`BUDDY_STAGED`, `BUDDY_LIVE`, and public readiness results.

## One-time production setup

1. An operator installs the reviewed deploy/production/deploy-buddy-release as
   /usr/local/sbin/deploy-buddy-release (root:root, mode 0755). Use a dedicated
   buddy-deploy OS account with no password login or Docker membership. Keep its
   SSH authorized-keys file and parent directories under operator control.
   Install only the public half of the Actions key, with this prefix:

   ```text
   restrict,command="/usr/bin/sudo -n /usr/local/sbin/deploy-buddy-release \"$SSH_ORIGINAL_COMMAND\""
   ```

   Append the key type and public key on the same line. The forced command only
   accepts one fixed-format request with immutable candidate and rollback pins. Use a sudoers drop-in installed with visudo that
   grants that account only the fixed executable:

   ```sudoers
   buddy-deploy ALL=(root) NOPASSWD: /usr/local/sbin/deploy-buddy-release
   ```

   Replace the prior activation-only sudoers grant and forced command. Install the reviewed dispatcher and both helpers from the same revision.
   From a trusted copy of the pinned deployment source, use:

   ```bash
   sudo install -o root -g root -m 0755 deploy/production/activate-buddy-release /usr/local/sbin/activate-buddy-release
   sudo install -o root -g root -m 0755 deploy/production/stage-buddy-release /usr/local/sbin/stage-buddy-release
   sudo install -o root -g root -m 0755 deploy/production/deploy-buddy-release /usr/local/sbin/deploy-buddy-release
   sha256sum deploy/production/{activate,stage,deploy}-buddy-release /usr/local/sbin/{activate,stage,deploy}-buddy-release
   ```

   Verify the installed checksums and preserve the previous activator for host
   recovery. Install during a coordinated maintenance window with no other
   Buddy deployment running.

2. Create /etc/buddy-deploy and its releases subdirectory as root:root with
   mode 0700. Install compose.conf as root:root, mode 0600. This Bash file
   fixes the Docker context, project, project directory, protected env file
   and existing Compose files. All referenced files and their parent
   directories must be writable only by trusted production operators.
   Use the exact serving configuration, leaving off the release-specific image
   override. If that override changes anything besides the image, incorporate
   its non-image settings in the trusted base first. Keep every argument
   absolute where it denotes a file or directory.

   ```bash
   compose=(/usr/bin/docker --context default compose --project-name buddy
     --project-directory /path/to/current/launch-directory
     --env-file /path/to/current/compose.env
     -f /path/to/current/compose.production.yaml
     -f /path/to/current/compose.host.yaml)
   upstream=http://127.0.0.1:8080
   persistent_root=/srv/dungeonmindbuddy
   ```

   Use the actual production loopback port and bind mount, and keep the
   current container's protected environment file selection. Never store
   application secrets in either deployment policy file.

3. Create the GitHub environment buddy-production and restrict deployments to
   main. Manual dispatch starts the job. The server-side release record below
   provides operator authorization and binds the exact candidate and rollback.
   Set BUDDY_DEPLOY_HOST to the SSH hostname or IP and BUDDY_DEPLOY_KNOWN_HOSTS
   to the independently verified host-key line for that exact name. Set the
   environment secret BUDDY_DEPLOY_KEY to the dedicated private key.

4. Restrict the separate `buddy-image-release` environment to the `main`
   branch and set its `BUDDY_IMAGE_PUBLICATION_ENABLED` variable to `true`.
   This environment needs no production SSH key.

## Publish and approve one release

Run **Publish Buddy release image** on GitHub Actions from `main`, with the
full reviewed first-parent commit as `revision`. Copy the immutable registry
reference from the successful run summary. The image uses the default guest
build configuration unless `hosted_guest_graph` is explicitly selected. The
selected build uses a separate registry tag and records `graph=1` in its guest
configuration label. This build option alone does not enable the backend or
select the authorized snapshot; verify those settings during activation. For the guest Build editor, also select `hosted_guest_build=true`; it requires guest Graph, uses a distinct image tag, and records `graph=1;build=1` in the guest configuration label. Both flags default off. Derive the expected local image ID from the manifest:

```bash
candidate_image_id=$(docker buildx imagetools inspect --raw "$registry_ref" |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["config"]["digest"])')
registry_digest=${registry_ref##*@}
```

For a guest Graph serving overlay, first merge its reviewed PR into the exact
serving branch. Set the protected `buddy-image-release` environment variable
`BUDDY_SERVING_RELEASE_BRANCH` to that branch. Dispatch the publisher from
`main` with `hosted_guest_graph=true`, the merged PR number in `serving_pr`,
its merge SHA in `revision`, and the currently serving source SHA in
`serving_parent`. The publisher verifies the PR is merged to that configured
branch and its merge is the current branch tip. The specified live serving
SHA must either be its first parent or an ancestor of that parent with an
identical Git tree. The image label records the exact specified live SHA, which
must also match the rollback source used in staging. Keep the serving and
rollback image pins unchanged until staging and activation.

Set `registry_digest` to the `sha256:…` portion of that registry reference.
Verify the candidate's compatibility with the current schema and data.
Record the currently serving healthy image as the compatible rollback.
The rollback image must already be tagged and present on the host.
Dispatch **Deploy Buddy (image only)** from main using the approved values:

```bash
gh workflow run deploy-buddy.yml --ref main \
  -f revision="$revision" -f registry_digest="$registry_digest" \
  -f candidate_id="$candidate_image_id" -f rollback_revision="$rollback_revision" \
  -f rollback_id="$rollback_image_id" -f release_mode="${release_mode:-default}" \
  -f document_digest="${document_digest:-}"
```

The production operator authorizes the exact request before dispatch. The
`buddy-production` environment restricts the workflow to main. The dispatcher
checks the healthy serving rollback, stages, and activates under a single lock.
Confirm both `BUDDY_STAGED` and `BUDDY_LIVE` with the candidate image ID.

Until the production operator replaces the activation-only forced command,
continue staging as root and dispatch with the revision alone. After the
forced command changes, the dispatcher requires all candidate and rollback pins.

Before staging either guest mode, install a root-owned, root-only `/etc/buddy-deploy/guest-graph.conf` containing the authorized baseline as shell assignments `guest_graph_space=<space>` and `guest_graph_revision=<revision>`. Use the exact approved identifiers; the helper validates and freezes them in the release record. Changing them cannot retarget an existing staged release. Do not include credentials.

For a main-line guest Graph image, choose `guest-graph` as the workflow release mode.
For a guest Graph serving overlay, choose `guest-graph-serving` instead. That
mode requires the candidate's serving-parent label to equal the rollback source
SHA; ordinary guest mode rejects a labeled serving image. The default
release mode continues to accept only the default build.

The command pulls by registry digest, verifies the candidate and rollback
identities, and creates `/etc/buddy-deploy/releases/<full-candidate-sha>.conf`
under the deployment lock. Confirm the resulting `BUDDY_STAGED` receipt.
Guest records also contain the enabled switch and the two validated baseline identifiers. For a guest Build image, use `guest-build` for a main-line release or `guest-build-serving` for a serving overlay. The stage helper requires the Build-specific image label and records `guest_build_enabled=1`; the activator sets and verifies the Build runtime switch only for the candidate. Rollback uses the existing base Compose configuration. The activator supplies and verifies them for the candidate only; rollback uses the existing base Compose policy. Release records contain these literal fields:

For the merged guest Buddy discussion capability, select `hosted_guest_buddy=true`
alongside guest Graph, Build, Plan, Play, and media when publishing the reviewed
serving image. Use `guest-buddy-documents-serving` for staging, with the document
template digest as the workflow document digest. The image identity includes `buddy=1`;
the stage record binds it to the candidate and activation checks all three guest
conversation switches. This does not enable guest Buddy effects or establish a
live-provider test. Existing release modes remain available with Buddy off.

To include guest Play discussion, also select `hosted_guest_play_buddy=true`.
Use `guest-play-buddy-documents-serving` when staging; it requires the distinct
`play-buddy=1` image identity and records the candidate-only Play Buddy switch.
An earlier Buddy-only image cannot be staged as a Play Buddy release.

For guest Build proposals, also select `hosted_guest_build_proposals=true` and
stage with `guest-build-proposals-documents-serving` and the same document
template digest as the workflow document digest. Its distinct `build-proposals=1` image
identity and staged setting enable the candidate's existing Build proposal flow.
A Play Buddy-only image is rejected for this mode. Rollback uses the base
Compose policy; this switch alone does not establish production acceptance.

For a serving release that includes approved guest source pages, install a root-owned
`/etc/buddy-deploy/guest-documents-template.json` and a root-owned
`/etc/buddy-deploy/guest-document-bundles` directory. The template is UTF-8 JSON
with `version: 1` and a `documents` list of `{title, markdown}` objects. Compute
its lowercase SHA-256 and pass it as the workflow document digest, after the literal mode
`guest-build-documents-serving`. Stage binds the template to the existing approved
Graph policy, stores a content-addressed read-only bundle, and records its digest.
Keep that artifact for provenance and rollback. A changed template or existing
release record is rejected. Activation verifies the bundle digest and mounts only
that bundle read-only for the candidate; rollback does not inherit the mount.

```bash
candidate_tag=dungeonmindbuddy:<full-candidate-sha>
candidate_id=sha256:<candidate-image-id>
rollback_revision=<full-current-serving-sha>
rollback_tag=dungeonmindbuddy:<full-current-serving-sha>
rollback_id=sha256:<current-serving-image-id>
registry_digest=sha256:<immutable-registry-manifest-digest>
```

## Activate and verify

Dispatch **Deploy Buddy (image only)** from main with the candidate and rollback pins above.
It waits for the fixed Buddy service to become ready, with pulling and building
disabled. It checks the serving image, health, data mount and loopback binding.
If the candidate fails, it attempts to restore the verified prior image and
reports the failure even when rollback succeeds. If rollback fails, follow the
production runbook. Use the release log's BUDDY_LIVE line to confirm the image
identity, then verify the public HTTPS readiness and signed-out auth response.
Only one deploy may run at a time. Do not run a manual Compose cutover
concurrently with this workflow. Remove stale approvals once their activation
window closes.

## Retire obsolete image tags

After confirming public HTTPS readiness, the activator records the serving
revision and image ID in `/etc/buddy-deploy/serving` and emits the same
`BUDDY_LIVE` receipt. It then applies any root-owned
`/etc/buddy-deploy/retire-images` list while still holding the deployment lock.
An absent list disables image removal.

The operator writes one approved obsolete tag and full Docker image ID per
line, separated by one space. Use only `dungeonmindbuddy:<full-sha>` tags.
Update the list and retire expired release approvals under
`/run/lock/buddy-production-deploy.lock`. Retained release approvals must
use the literal assignments shown above or be written by the staging
command. Malformed approvals or a changed image ID stop retention.

The serving and rollback images, retained approval pins, and all running and
stopped container image IDs are protected. A cleanup failure leaves the
healthy release serving. Correct the retirement policy and repeat the same
activation to retry cleanup. Check the serving receipt before deciding
whether recovery is needed.

## Retire obsolete build cache

For the shared default BuildKit builder, the operator can add a root-owned
`/etc/buddy-deploy/retire-cache` file under the same lock. Put one approved
full cache ID per line. Use the builder's disk-usage report to confirm each
record belongs to Buddy and is obsolete. The activator only prunes approved
records that still match the Buddy Hermes setup or patch instructions and
report as non-shared and reclaimable. It verifies each ID is gone afterward.
An absent list disables cache removal. Cache failure leaves the healthy
release serving and can be retried through the same activation.
