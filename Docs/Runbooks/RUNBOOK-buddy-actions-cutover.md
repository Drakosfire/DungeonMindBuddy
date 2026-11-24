# Publish and deploy a Buddy image from GitHub Actions

Use this for a reviewed image-only release on the existing production Compose
configuration. Use the [production runbook](RUNBOOK-buddy-production-deployment.md)
for dependency, schema, proxy and persistent-state changes. For migration 0172,
retain the separate paired backup rehearsal and migration procedure.

## One-time production setup

1. An operator installs the reviewed deploy/production/activate-buddy-release as
   /usr/local/sbin/activate-buddy-release (root:root, mode 0755). Use a dedicated
   buddy-deploy OS account with no password login or Docker membership. Keep its
   SSH authorized-keys file and parent directories under operator control.
   Install only the public half of the Actions key, with this prefix:

   ```text
   restrict,command="/usr/bin/sudo -n /usr/local/sbin/activate-buddy-release \"$SSH_ORIGINAL_COMMAND\""
   ```

   Append the key type and public key on the same line. The forced command only
   accepts a full commit SHA. Use a sudoers drop-in installed with visudo that
   grants that account only the fixed executable:

   ```sudoers
   buddy-deploy ALL=(root) NOPASSWD: /usr/local/sbin/activate-buddy-release
   ```

   Install the reviewed staging command separately for the root operator.
   From a trusted copy of the pinned deployment source, use:

   ```bash
   sudo install -o root -g root -m 0755 deploy/production/activate-buddy-release /usr/local/sbin/activate-buddy-release
   sudo install -o root -g root -m 0755 deploy/production/stage-buddy-release /usr/local/sbin/stage-buddy-release
   sha256sum deploy/production/{activate,stage}-buddy-release /usr/local/sbin/{activate,stage}-buddy-release
   ```

   Verify the paired checksums and preserve the previous activator for host
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
select the authorized snapshot; verify those settings during activation. Derive the expected local image ID from the manifest:

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
branch, its merge is the current branch tip, and its first parent is the
specified serving SHA. It labels the resulting image with that parent. Keep
the serving and rollback image pins unchanged until staging and activation.

Set `registry_digest` to the `sha256:…` portion of that registry reference.
Verify the candidate's compatibility with the current schema and data.
Record the currently serving healthy image as the compatible rollback.
The rollback image must already be tagged and present on the host. Using
the approved values, the root operator stages the image and both pins:

```bash
sudo /usr/local/sbin/stage-buddy-release \
  "$revision" "$registry_digest" "$candidate_image_id" \
  "$rollback_revision" "$rollback_image_id"
```

Before staging either guest mode, install a root-owned, root-only `/etc/buddy-deploy/guest-graph.conf` containing the authorized baseline as shell assignments `guest_graph_space=<space>` and `guest_graph_revision=<revision>`. Use the exact approved identifiers; the helper validates and freezes them in the release record. Changing them cannot retarget an existing staged release. Do not include credentials.

For a main-line guest Graph image, append the literal `guest-graph` argument to
the stage command after installing the reviewed guest-capable stage helper.
For a guest Graph serving overlay, append `guest-graph-serving` instead. That
mode requires the candidate's serving-parent label to equal the rollback source
SHA; ordinary guest mode rejects a labeled serving image. The default
five-argument mode continues to accept only the default build.

The command pulls by registry digest, verifies the candidate and rollback
identities, and creates `/etc/buddy-deploy/releases/<full-candidate-sha>.conf`
under the deployment lock. Confirm the resulting `BUDDY_STAGED` receipt.
Guest records also contain the enabled switch and the two validated baseline identifiers. The activator supplies and verifies them for the candidate only; rollback uses the existing base Compose policy. Release records contain these literal fields:

```bash
candidate_tag=dungeonmindbuddy:<full-candidate-sha>
candidate_id=sha256:<candidate-image-id>
rollback_revision=<full-current-serving-sha>
rollback_tag=dungeonmindbuddy:<full-current-serving-sha>
rollback_id=sha256:<current-serving-image-id>
registry_digest=sha256:<immutable-registry-manifest-digest>
```

## Activate and verify

Dispatch **Deploy Buddy (image only)** from main with the candidate SHA.
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
