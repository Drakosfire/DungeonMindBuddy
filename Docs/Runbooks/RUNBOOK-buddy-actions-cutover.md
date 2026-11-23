# Manually deploy a staged Buddy image from GitHub Actions

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

## Approve and activate one release

Stage the exact reviewed candidate image. Verify its readiness on the current
schema separately, then record the currently serving healthy image as the
compatible rollback. Both images must already exist on the host. Create
/etc/buddy-deploy/releases/<full-candidate-sha>.conf as root:root, mode 0600
with the verified values for this cutover:

```bash
candidate_tag=dungeonmindbuddy:<full-candidate-sha>
candidate_id=sha256:<candidate-image-id>
rollback_revision=<full-current-serving-sha>
rollback_tag=dungeonmindbuddy:<full-current-serving-sha>
rollback_id=sha256:<current-serving-image-id>
```

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
