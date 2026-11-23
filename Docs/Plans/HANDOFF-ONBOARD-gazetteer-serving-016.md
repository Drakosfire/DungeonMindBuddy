# ONBOARD: carry Gazetteer review onto serving

Status: ACTIVE under the owner's Sizzek goal and authorized review, merge and
deploy. Serial integration after merged #4556 (`2ee69a04bdf83d79a68f60de698b39e4641a05ec`),
based on the exact running `01632e3a48f52a6e070f042be85e77560f8a4cfc` via
`origin/codex/onboard-worldbuilding-serving-2d`. The sole behavior change is
showing invalid Gazetteer evidence review without calling unsupported correction;
invalid evidence still cannot be published.

Write lease: this handoff and the files in #4556. Preserve the serving guest
settings and schema 0204. Verify the cumulative base-to-head diff, focused and
exact-SHA hosted frontend checks, full-discovery diagnostic against the serving
baseline, and independent Bugbot review. Production activation is a subsequent
step under the owner's release authority, with the shared deployment lock,
current-image recheck, immutable candidate and same-schema rollback. No live
runtime or data is leased during implementation and testing.
