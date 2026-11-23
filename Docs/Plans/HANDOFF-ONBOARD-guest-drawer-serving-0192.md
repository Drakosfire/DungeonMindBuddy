# ONBOARD: keep the serving Graph usable during release review

Status: ACTIVE for source integration, explicitly authorized by the Sizzek
onboarding goal. Base `2fb4e5594196bf419965d5098b38cd46fbf13503` is the merged
#4503 serving lineage; branch `codex/onboard-guest-drawer-serving-0192`, this
checkout. No live service, database, port, flags or World is leased.

Carry merged main #4505 unchanged onto #4503, preserving its exact Core pin,
Graph support and excerpt-selection behavior. Exclusive write lease: this
handoff; `Docs/Plans/HANDOFF-ONBOARD-guest-review-layout.md`; `BuddyApp.tsx`,
`guestRelease/GuestReleaseDrawer.tsx` and its test, guest review CSS, and the
single test classification. Compare carried files with merged main. No schema,
backend, public release or feature-switch change is in scope.

Source topology is parallel-independent of open #4502 as checked at head
`692fcf579af7882e3ad5298eaceebf2a8d0b1e0f`; it touches none of these paths.
Both integrations share the production service: cutovers are serial and require
fresh live revision, schema, rollback and lane reconciliation. SSH signing for
the live host was last observed unavailable. This brief does not activate or
lease the runtime.

Run the exact-head hosted frontend verifier, full discovered diagnostic and
exact-parent comparison, inspect cumulative serving-base diff, and obtain
independent Bugbot review. Preserve known red tests and report their identities;
matching IDs do not establish identical causes. Browser evidence from #4505 is
synthetic; deployed owner acceptance, exact guest snapshot review and the rest
of onboarding remain outstanding.
