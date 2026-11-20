# Local Threat hydration through native authority

Active serial slice on Buddy main 8b556a3fe3950d89f6291d8db7a87e7d27bbd464.
The operator authorized implementation, review and merge. MIND owns delivery.
PR #4249 is the merged predecessor.

Move mounted local Threat hydration to the authorized managed World and
exact native revision path. Preserve campaign scope through the existing
native context campaign selector and verify response correspondence. An
unbound World or unavailable revision fails closed. Preserve direct saved V1
mechanics reads and existing hosted ownership checks. Do not infer historical
APP associations from a graph revision. Hermes invocation authority is a
separate serial slice.

Hubble owns internal scoped projection support in
managed_world_graph_projection.py and its existing owning test file.
MIND owns the Threat hydration route and service, their existing owning
tests, and the two handoffs. Rebrief if inspection establishes that a
client scope producer also needs to change. Draft #3824 overlaps the route
and service. Allocate only the local-native dispatch and its tests on main.

Verify separate managed/native IDs, original pinned revision after head
advance, campaign scope, admission before I/O and binding recheck after
hydration. Prove there is no mounted fallback to classic projection and
saved V1 mechanics still read from the exact saved revision. Run focused
backend and app authorization checks, plus affected UI tests if client
changes are required. Independently review the final source before merge.

## UI scope after caller audit

Graph reference scopes contain native World IDs. Threat hover and sheet
requests need the managed ID from a verified matching projection binding.
The response remains keyed to the requested managed ID. Keep native ID,
campaign, revision and binding generation in UI cache and in-flight
identity. A missing or mismatched binding fails closed.

MIND owns the two Threat mechanics hooks, threatSheetViewModel.ts and
their existing tests for this adaptation. Inspect alternate scope
producers before editing them. The change ships with the route switch
because the old UI request cannot reliably address a managed World.

Review found that a rebind before dispatch could succeed under the new
binding while the UI cached under the old binding. MIND also owns the
Threat request model and matching TypeScript API type. Add a paired
expected native World and binding version as correspondence conditions.
Existing callers without captured binding can omit both. The UI sends both.
The server derives authority from its registry and checks the expected
binding before reading Core, then preserves the existing final recheck.

## Delivered

PR #4251 merged at 4e22cd3f9487b84f449d84e673cc8fb257fedb3c after review
5996296631 and three successful GitHub checks. Source 861c3a11 passed
60 owning and 335 authorization tests. Hosted UI passed 1,421 and built.
Full UI reproduced the base's 103 failures and two pending cases, with
one added test and no removals. Full release qualification remains open.
