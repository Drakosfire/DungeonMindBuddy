# ONBOARD: combine Sizzek and conversation serving lineages

Status: ACTIVE for source integration under the owner's Sizzek goal and explicit
review/merge/deploy authority. Base is the merged conversation-serving branch
`4acc97af48d7986b00b7eb46ae2278564cc21c1c` (merged #4509), branch
`codex/onboard-combined-serving-0197` in this checkout. The Sizzek source is
merged serving branch `3cc09cbc383a9bbf1542af4684abf181c5b85e90`; both descend
from previously observed image revision `5647a799e3996d38a7ace6ad79b706ad15cb6092`.
No production service, database, port, World or external state is leased here.

Outcome: prepare a candidate that preserves both merged lineages rather than
letting a Sizzek activation remove conversation work or vice versa. Carry only
#4497's exact Core pin, #4498's independently selected guest context excerpts,
#4505's graph/review layout and their tests/handoffs. The base already carries
#4502/#4504/#4509 conversation work and APP reader fences through 0198. Preserve all
of that source and the existing guest build configuration. Do not incorporate
or rewrite the separately owned portrait 0193 migration; if live schema is on
the 0193 branch, a reviewed migration-branch reconciliation is required before
this candidate can run. Runtime activation is expressly outside this lease.

Write lease: this handoff; `pyproject.toml`, `uv.lock` solely for exact #4497
Core pin; `Docs/Plans/HANDOFF-ONBOARD-guest-independent-excerpts.md` and
`HANDOFF-ONBOARD-guest-review-layout.md`; `BuddyApp.tsx`, guest release drawer,
review CSS and tests; owner guest-selection service/routes/tests and the exact
owner route registration in `apps/live_control_server/main.py`; CI test
classification only as in #4505. No conversation implementation, migration,
public flag, provider or model changes. Source integration is serial after both
merged source lineages; it does not replace their independent reviews. Re-anchor
parent heads and other active leases before final review. The two source branches
share the service; any cutover must be serialized with its owner and follow a
fresh actual live image/schema/config/backup check. SSH access has been restored; the separate DOGFOOD lane owns the first 0198 cutover. Parallel-independent navigation PR #4510 touches a disjoint UI write set; preserve and integrate it separately after its review.

Review both the narrow parent-to-head change and the complete last-observed
serving-to-head release map. Verify carried files match reviewed source, exact
Core pin and migration topology, run exact-head hosted and full discovered
frontend diagnostics with exact parent comparison and affected guest/conversation
backend contracts in locked disposable environments. Independently review with
Bugbot. A source integration PR is not permission to cut over an unqualified
schema lineage; require the conversation lane's retained exact-source recovery,
source, provider and cutover evidence, fresh backup/restore and compatible
forward recovery before any deployment. Preserve baseline failures honestly.
Private owner candidate preparation, digest approval and guest isolation remain
separate gates. No incomplete Sizzek experience is represented as shipped.
