# Buddy release rehearsal checklist

The [deployment runbook](RUNBOOK-buddy-production-deployment.md) owns commands, required safety gates and stop conditions. Use this checklist to record the pending on-host and public rehearsal evidence for the selected release. The release record owns outcomes; [Buddy #3560](https://github.com/Drakosfire/DungeonMindBuddy/issues/3560) tracks public DNS and hosted Graph/browser acceptance. Local synthetic evidence is not hosted acceptance. No deployment is authorized by this document.

## Preflight and build

- **Builder capability — recorded build verified:** the deployment owner built and locally loaded release `9b30bb78e` using the production Dockerfile/api target and full-SHA tag/revision label. The build log and inspected tag agree on image `2f86ffbde204…`; host Compose 2.32.4/Buildx 0.30.1 and the default docker driver were observed. Keep the runbook’s builder preflight and image-ID/revision guard for each selected release. This does not qualify the later serving image or replay the protected preparation wrapper. [Builder disposition](../../Backlog-DONE.md) · [Owning release record #3560](https://github.com/Drakosfire/DungeonMindBuddy/issues/3560).
- **Context/capacity rehearsal (still pending):** record target Buildx/BuildKit versions, compare fresh archive versus disposable used-checkout context bytes and cold/incremental build timings, preserve the required statblock fixture, and verify seeded UI-local files and `graph_data` do not expand the production context. Tie the approved image identity to those measurements; the successful build above does not replace this comparison. [Prior context](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L86).
- Match APP-STATE and WorldGraph database identities before any migrations. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L97).
- Restore both databases and files from one approved backup set into isolated targets. Record the backup identity, state fingerprint, known World and revision, file parity, and owner procedures. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L98).
- Confirm approved absolute bind roots, missing-source rejection, and UID/GID 10001 read/write access with the approved image. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L100).
- Verify inherited Compose variables cannot override protected mount and port bindings; exercise default and custom Nginx port routing. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L99).
- Inventory Compose callers and pin current and rollback image identities before changing the base image default. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L119).
- Verify cold startup and persistent readiness failure fit the 330-second bound on the target Compose version; verify failed-wait inspection. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L89).
- Measure log retention on the approved host daemon against its agreed budget; track the decision in [#3538](https://github.com/Drakosfire/DungeonMindBuddy/issues/3538). [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L121).

## Proxy and browser

- Check external DNS, TLS, and HTTPS separately for every published address family before cutover. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L95).
- Measure effective cache headers and cold/repeat transfers for HTML, stable and fingerprinted assets across rollout. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L92).
- Inventory effective proxy callers; if enabling an Agent streaming profile, separately witness a scoped incremental SSE path. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L120).
- Verify loopback and public SPA artifacts and signed-in Graph navigation. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L101).
- Confirm installed source evidence class identity, real DungeonMind sign-in, native PostgreSQL Graph read, and sign-out. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L87).
- Verify direct hosted route availability/denial on the actual release, including the locally tested routes and their documented profile. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L96).
- Record signed-out, signed-in and post-logout session behavior with a dedicated test account and its World. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L103).

## Recovery and closeout

- Exercise the compatible rollback on isolated databases and record prior image, health and proxy proof. Exercise the incompatible-schema stop decision without changing the serving container. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L123).
- Name restart ownership and rehearse recovery; record approved image, persistent mount, loopback binding, and readiness. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L124).
- After the rollback window, measure approved retired-image cleanup with the builder owner; do not delete from this checklist alone. [Prior evidence](https://github.com/Drakosfire/DungeonMindBuddy/blob/6b2d4844fd4e0045f55042c3c88dce5c00be583b/Backlog.md#L122).
