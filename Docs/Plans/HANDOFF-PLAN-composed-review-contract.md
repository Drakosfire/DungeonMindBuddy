# Native review and Save for an insertion inside a Plan slot

Status: MERGED in PR #4347 at `a459c18238c76e55f21b77e6708828401353e66e`.
Independently reviewed head `9a836c81c95922340ae2e14610745a723f117c13`
passed 62 focused owner tests and the local hosted-contract frontend build
and suite. The named local backend suites retained seven Build failures
matching the exact base's test IDs and error messages. The independent
disposable 0175 witness passed 18 checks, including real older-reader
refusal, preservation of an existing sidecar and a typed pending review
through a refused downgrade, and cleanup. Witness SHA256
`0271b8769cddd0708532442a3fe3d98b07743da9a956f0a5498cc841ed18b42a`.
The next serial slice is the
[composed Plan location decision](HANDOFF-PLAN-composed-native-targeting.md).

Completed assignment:
Serial branch `codex/plan-composed-review-contract` at exact base
`a210cdf11442464ca37984375978add72f27681f`, the manual Plan composition merge
#4346. Use the existing isolated contextual verification checkout and uniquely
owned disposable application-state clones. The ordinary Send producer is a
serial successor after this contract merges.

## Outcome and boundary

Bind insertion before or after a paragraph within an existing composed row
slot. Keep a distinct slot boundary capture so the existing root-boundary
meaning stays precise. The exact editor and draft Markdown, checked draft
presentation, saved presentation fingerprint, World, document, committed
revision and conversation binding must agree. Stable row, slot and block IDs
and their indices are host data. Model input in the successor may provide
prose, meaningful headings and row/slot descriptions, permitted relations and
local aliases.
The slot address is the sole insertion locator. The existing range fields
retain the captured selection witness, and the successor will resolve the
slot address against its actual editor instead of storing a second target
position. The first receiver admits only page content whose editor and source
can be compared exactly: paragraphs, headings and horizontal rules. Other
block formats require a separately proven projection before agent insertion.

Native Review Prepare accepts one checked resulting sidecar when the captured
target is slot-local. The sealed application and committed revision retain it.
Confirm uses the existing atomic Content CAS and checks that the same owner,
revision and before-layout remain current. Require only new reviewed prose at
the chosen slot boundary, unchanged IDs and structure elsewhere, and correct
new Markdown byte ranges and source digests. Old review commands and receipts
retain byte-compatible validation/serialization. Reject stale, foreign,
malformed, omitted and unrelated layout changes before mutation. Retain the
per-attempt state across lost acknowledgements, replay and explicit recovery
without treating matching Markdown as matching layout.

This assignment owns the slot capture and review persistence contract and
focused tests. It has no ordinary Send/model activation, writer guidance,
retrieval order, proposal UI, Build, image movement, Graph creation,
deployment or serving-pin changes.

## Ownership and proof

Write set is the host-native Plan authoring capture, the Plan action target
kind and its existing selection constraints, a narrow composed layout
validation module if needed, the existing application-state Plan Review
contract and its tests, a versioned slot catalog validator where needed to
verify the host geometry, at most one application-schema reader fence and
its compatibility checks, this handoff and the merged manual predecessor.
Content's `commit_plan_in_connection` also needs the existing presentation
argument threaded through to its shared Content CAS. This changes only that
adapter in `src/application_state/content/service.py`; its default retains
the existing old-writer refusal.
Read current contracts and exact related open diffs. #3307
(`8cb62d310bba188ed328459def044dca7792b520`) and #2225
(`f720e5f55f5b357dba09977663306482d5188a65`) touch native execution/
retrieval. #3290 owns writer compaction. The held #2104 reference retirement
has a separate scope. This receiver slice leaves those runtime files alone.

The fetched chain ends in 0174. Recheck open migration allocations before
using 0175 for the new durable capture/application forms, then demonstrate an
older reader refuses the upgraded disposable database. Preserve old records,
explicit rollback behavior and clean teardown. Verify the narrow React/
browser workflow in the succeeding producer assignment, after this native
receiver is merged.

Use owning PostgreSQL and actual HTTP/Review tests for an exact before/after
inside-slot insertion, immutable neighboring slots and geometry, duplicate and
foreign ownership controls, stale layout with identical Markdown, command
retry and same-transaction rollback. Run the owning local locked backend
contract and require independent exact-head review before merge. Keep known
baseline failures visible.
