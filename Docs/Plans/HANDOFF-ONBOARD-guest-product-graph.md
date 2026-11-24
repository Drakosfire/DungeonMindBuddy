# ONBOARD: Sizzek in Buddy's Graph workspace

Status: MERGED on main via PR #4579 (`42a524ade2e48c8a1a8c354b0b56d86f48b99a72`); serving adoption is tracked in `HANDOFF-ONBOARD-guest-product-graph-serving.md`. The owner corrected the onboarding direction: the signed-out
demo must lead visitors through Buddy's actual surfaces, not a separate landing
experience. This first serial slice opens the published Sizzek copy in the real
Graph workspace at `/graph`. Base is the fetched `origin/main` and branch is
`codex/onboard-guest-product-graph`. No database, provider, live runtime or
release-copy write is leased. Open guest/media implementation PR inventory was
checked; the active DOGFOOD lane owns separate Plan/authoring work.

Reuse `NativeGraphDemo` and `WorldGraphCanvas` with an explicit guest mode and
an adapter over only the anonymous immutable release response. Never call the
private managed-World API or the server-backed playground. Display released
connections and their source excerpts, evidence roles and qualifications using
release-local IDs; do not present them as admitted private native records.
Guest layout is memory-only and the read-only product graph does not claim it is
saved. Preserve the existing guest home, temporary graph additions, saved answer
and scene while the next serial slice adds temporary create/connect/reset to the
real Graph. Subsequent serial slices bring the same guest session into actual
Build, Plan and Play surfaces; this slice is not completion of that objective.

Write lease: this handoff; `App.tsx` and its owning guest composition tests;
`guestRelease/GuestReleasePage.tsx` and tests for the Graph entry; a focused
guest Graph adapter/page and tests; `nativeGraphDemo/NativeGraphDemo.tsx`,
`nativeGraphDemoApi.ts`, and owning tests solely for honest guest rendering and
memory-only layout. AppChrome and auth/API/schema policy are outside the lease.

Verify actual signed-out App composition, release changes and unavailable
copies, released node/edge/source closure, evidence qualifications, no private
or playground network requests, no guest layout persistence, keyboard/mobile
interaction and signed-in non-regression. Run exact-SHA hosted and discovered
frontend verification, retain inherited failures and obtain independent Bugbot
review. Serving adoption is serial from the actual deployed image after
re-anchoring the active runtime lanes.
