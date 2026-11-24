# ONBOARD: temporary edits in the guest Graph

Status: ACTIVE. The owner authorized the Sizzek signed-out demo and corrected its
scope to guide visitors through Buddy's real surfaces. This serial successor to
main PR #4579 and serving PR #4582 enables a visitor to create a temporary point,
connect it, and reset the real Graph to the released snapshot. Branch
`codex/onboard-guest-graph-edit` starts from fetched `origin/main`. No database,
provider, live World, release publication or shared benchmark resource is leased.

Use the existing Graph interaction and a release-scoped, memory-only guest API.
Never write to the managed World, public release, server playground, browser
storage or another guest's session. Clearly label additions as temporary and
separate them from cited released evidence; reset must remove all temporary
nodes, edges, pending operations and selection/layout state without altering the
immutable copy. Leaving/remounting the Graph discards edits. Handle stale
confirmations and duplicate operations without resurrecting data after reset.
Keep authenticated Graph behavior unchanged. Guest Build, Plan and Play remain
separate serial successors; retain the existing saved examples during transition.

Exclusive write lease: this handoff, `guestRelease/GuestProductGraph.tsx`,
`guestRelease/guestGraphModel.ts`, `guestRelease/GuestReleasePage.test.tsx` and
associated guest styles, and `nativeGraphDemo/NativeGraphDemo.tsx` with its
owning tests only for guest interaction, reset and truthful messaging. Existing
active DOGFOOD PR #4573 uses separate Plan/authoring files. The checkout owns no
shared ports, services, databases or output directories.

Verify the actual signed-out App/Graph composition can add, connect and reset;
released sources remain accurate, temporary nodes are labeled and uncited,
repeated/stale operations cannot escape reset, remount/session isolation and
no private network or browser storage writes, mobile and signed-in regression.
Run the exact-SHA hosted and discovered frontend checks, compare retained baseline
failures, obtain independent Bugbot review, then serially adopt and deploy onto
the current serving lineage with guarded runtime verification.
