# ONBOARD: guest review on the serving release

Status: ACTIVE. The owner's onboarding goal explicitly authorizes review, merge,
and deployment. This is a serial release-integration slice based on the live
revision `590e45a2bd7a92e90e80aa6d053353e4cfebdc19`, remote parent
`codex/dogfood-authored-context-0189`; the parent is an already deployed release
line, not an unmerged behavioral dependency to be deployed later. Branch
`codex/onboard-guest-review-serving` carries only merged PR #4467's build-setting
change and this handoff on top of that parent. No schema or product behavior is
changed by this integration.

Exclusive write set: this handoff and the six paths changed in #4467, including
CI contract/inventory entries. No private World data belongs in this PR. Verify
that all pre-existing serving files are retained, review the exact cumulative
base-to-head diff, run the affected helper tests and exact-source hosted frontend
verifier, compare any discovered frontend failures with this exact parent, and
obtain independent Bugbot review. Preserve schema 0189 and the serving source's
runtime, auth, World, signing key, and other configuration during any later
activation. Production image, service, database, and public routes are not
leased by this implementation; obtain a collision-free cutover window and verify
its exact current state before activation.

The goal is a reviewed image capable of enabling authenticated owner-only review
and private candidate preparation. The existing guest-release contract governs
all backend flags, real-source validation and owner approval. This integration
does not publish or expose private content and does not authorize guest access
without the separately required checks and owner selection.
