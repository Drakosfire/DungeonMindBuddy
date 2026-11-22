# ONBOARD: guest review on the current 0192 serving release

Status: ACTIVE. The owner authorized review, merge and deployment through the
onboarding goal. Serial replacement for the now-stale #4471 serving integration.
Base: current live `a5c7599c3c32731785de4562ced073cadf392e07`, remote parent
`codex/build-plan-semantic-hosted-0192`; branch
`codex/onboard-guest-review-serving-0192`. The parent is already deployed and
schema 0192 is active. Carry only merged #4467's guest build configuration and
this handoff, preserving every live runtime and schema change. The creature
label fix #4475 is a separate successor, not included here.

Expected write set: this handoff and the six files changed by #4467. No live
World, database, service, port or public content is leased for implementation.
Verify exact cumulative diff, helper tests, guest-release owning boundary and
exact-head frontend hosted/discovered evidence, compare failures with the
serving parent, and obtain independent Bugbot review. Build and stage an
owner-review-only image with guest page delivery off. Before any activation,
recheck live image, schema, configuration, signing key, runtime collisions and
applicable guest-release gates; preserve the exact deployed lineage. This
integration does not publish a World or authorize exposing private data.
