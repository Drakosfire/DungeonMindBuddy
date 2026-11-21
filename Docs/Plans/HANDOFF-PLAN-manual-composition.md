# Manual composition in the World Plan editor

Status: MERGED in PR #4346 at `a210cdf11442464ca37984375978add72f27681f`.
Independently reviewed head `7241b88b725768c61f372e073f2f23edaa0ad716`
passed 1,465 selected frontend checks and the production build. Full discovery
had 8,450 passes, 102 matching inherited failures and two skips, with all five
new tests passing and no missing cases. The exact main baseline had 8,444
passes, 103 failures and the same skips. Full discovery remains red.

Chromium, real Plan Save routes and disposable PostgreSQL verified unchanged
Markdown on layout-only Save, row dimensions, Undo/Redo, a 390px cold reopen,
prose Save, retained identities after a committed-but-unacknowledged Save and
newer Undo, and refusal of a stale revision without mutation. The exact
browser packet is `manual-plan-7241-dpk8_xw1/witness-summary.json` under the
task evidence root, SHA256
`96eecc123742fe066ed0ff126dbdb5e8f9a25af7d4f817d77b71ca3b783c4799`.
The next serial slice is the
[native composed Plan review contract](HANDOFF-PLAN-composed-review-contract.md).

Use the existing Page composer controls and checked PagePresentationV1
projection in the saved, World-owned Plan's Document view. An author can
compose existing supported prose into a row, edit slots and save layout-only
or prose changes through the existing Plan owner. Layout joins the exact
Markdown and World/document/revision basis throughout local recovery, Prepare,
Commit and cold reopen. Preserve stable identities and Undo/Redo.

Normal plain Plan, blank-plan welcome, Cards and hosted authorization retain
their current behavior. The legacy Plan proposal path cannot apply composed
layout; manual composition and conversation are distinct from the later
ordinary inside-slot agent assignment. No new migration is needed for this
producer because the exact HTTP receiver and reader fence are merged.

## Ownership and verification

Current open #3824 is the hosted integration draft with a separate active
fixture lease. #1188 at `3d6733a5e34026a52306f155917adf9c29dddf47` has the
historical Plan lease superseded by completed #1416. #1014 is inactive rollout
preparation. The held #2104 and remaining API-type draft overlaps stay in their
separate scopes. Reconcile the actual diffs and preserve live authorization.

Expected writes are `PlanSurfacePage.tsx` and its existing tests,
`api/types.ts` for the four presentation fields/consumers, a Plan-specific
presentation projection or recovery helper if needed, this handoff and the
merged HTTP predecessor handoff. Existing Page and Build composer owners,
API routes, protected agent codecs and the database schema remain outside
the assignment.

Use the locked local frontend verifier and fresh disposable application
state. Prove actual mounted Plan layout-only and prose Save, old or altered
receipt refusal, recovery of an exact lost acknowledgement with newer local
edits preserved, stale CAS refusal, Undo/Redo and cold reopen with empty
browser storage. Verify an ordinary plain Plan and Card path as regressions.
Retain local suite baselines and independent exact-head review before merge.
