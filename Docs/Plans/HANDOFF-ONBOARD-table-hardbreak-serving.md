# ONBOARD: carry the table hard-break fix to serving

Status: ACTIVE for preparation only. The onboarding goal authorizes review,
merge and deployment. This stacked successor carries merged main PR #4563
(`31d4ffa9074a1a1b364e8880126e89ce3faa653a`) on top of the exact unmerged
serving parent PR #4557 at `79d4d606538ed11c3efd99ab910f2d52f3897a49`.
Branch `codex/onboard-table-hardbreak-serving-79d4` uses the existing isolated
build-status-baseline checkout. Parent #4557 merges and activates first; then
re-anchor, rebase if its head changed, verify the actual running parent and
merge and activate this successor. This slice does not lease production runtime
while the parent is active.

The sole product change is the exact protected-table `<br>` compatibility fix
and its owning tests, carried without modification from #4563. Write lease:
the predecessor handoff and code/tests from that cherry-pick, plus this handoff.
No auth, provider, migrations, guest flags, public release content or unrelated
runtime changes. Preserve the guest configuration in the actual serving image.
Review the exact parent-to-head diff independently; run the hosted frontend
verifier and affected backend checks on the combined exact SHA; retain inherited
failures. Before activation verify the parent image, schema, backup and rollback
compatibility, then test the Winter Build request and signed-out guest surface.
Any parent or runtime change requires re-anchoring rather than an overwrite.
