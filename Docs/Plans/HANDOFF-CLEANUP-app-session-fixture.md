# CLEANUP: App session-view fixture

Status: ACTIVE. The standing cleanup goal authorizes implementation, independent
review and merge. One serial PR, base
`84e1b88f1fea95a5b3e7d99cc9c715618f38b4e0`, branch
`codex/app-surface-session-fixture`, existing bounded-production-logs checkout.

## Boundary

Write lease: this handoff and `apps/live-control-ui/src/App.test.tsx`, only the
aggregate session-view mock/setup and an owning request assertion. Preserve all
existing test bodies, inspector interaction and assertions. No runtime, routing,
classification, dependencies, providers, database or deployed state changes.
No ports or services allocated. Evidence stays outside the source checkout.

The current failing inspector case never loads its Surface: LiveControlApp calls
`getSurfaceSessionViews`, while the fixture mocks only the separate old reads.
Its retained exact-main failure contains the unintended relative network fetch.
Supply the actual aggregate response shape; do not fake the inspector or relax
its visible behavior. If another failure remains, retain it as red and assess
the owning boundary before expanding this slice.

## Coordination and verification

All 59 open PRs were checked. #2405 owns only obsolete graph wrapper mock/setup
seams in this file, explicitly excluding Surface expectation changes; preserve
those seams. Old root-Surface proposal #2326 is CLOSED, unmerged. #2298's shared
conversation mocks and #1188/#3824's Plan work remain excluded.

Critique: supplying only catalog/layout/state would leave the aggregate contract
incomplete. Supply events/jobs/plan_view too, using the existing synthetic
fixtures, and prove the actual aggregate function is called before Inspector
opens. Preserve explicit empty Inspector text and absence of Edit.

Validate the affected module, exact-source hosted/build/validator, full discovered
diagnostic and unchanged failure identities outside this case. Obtain independent
exact-head cumulative review before merge. Current full baseline is 8125 pass,
110 fail, 2 pending; full qualification stays red until actual proof.
