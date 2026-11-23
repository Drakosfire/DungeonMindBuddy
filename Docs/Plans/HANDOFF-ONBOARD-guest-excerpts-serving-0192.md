# ONBOARD: serve independently selected guest excerpts

Status: ACTIVE for source integration only, authorized by the owner's onboarding
goal including Bugbot review, merge and deployment. Base is the last observed
serving lineage `ebd7c0148aa60ae10b007a614896667761b0dfe6` (same tree as live
image revision `5647a799e3996d38a7ace6ad79b706ad15cb6092` at last successful
observation); branch `codex/onboard-guest-excerpts-serving-0192` in this checkout.
It does not lease the live service, production databases, flags, or ports.

Carry the reviewed Core pin `0a6cf9a9acb6ee5e47ee0bf5db06bd091afebb9f` from
main's #4497 and the merged independently selected guest source functionality
#4498, with their tests and handoff. Preserve the serving Graph fix, owner-review
build configuration, and existing behavior. Exact expected write lease: this
handoff; `pyproject.toml`, `uv.lock` solely for the exact reviewed Core pin;
`Docs/Plans/HANDOFF-ONBOARD-guest-independent-excerpts.md`; guest release
selection UI, test, route, service and integration/route tests; the exact hosted
route registration in `apps/live_control_server/main.py`. No migration or
feature activation is included.

Topology is parallel-independent source integration relative to open #4502 head
`692fcf579af7882e3ad5298eaceebf2a8d0b1e0f`: its diff was checked against the
serving revision and does not touch these code paths or the Core pin files.
Both target the same runtime, so deployment is serial and this brief does not
authorize a concurrent cutover. Re-anchor the actual live revision and #4502's
head, schema and ownership before any serving activation; if it changes,
reconcile source lineage and test again. SSH currently cannot sign for `alan`.

Verify the cumulative serving-base diff and exact carried-file parity; run
exact-head hosted frontend and guest-release contracts with locked Python and
the pinned Core, and the full discovered frontend diagnostic with exact-parent
comparison if failures differ or baseline is unproven. Obtain independent Bugbot
review. Preserve inherited red failures and evidence limitations. Merge this
integration only after applicable exact-source checks and review. A separate
qualified operational step, owner-reviewed candidate, digest-bound approval,
public isolation and other onboarding successors remain necessary; do not
activate flags or imply an anonymous demo exists.
