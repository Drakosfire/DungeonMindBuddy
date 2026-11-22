# ONBOARD: configurable guest release image

Status: ACTIVE. The owner's onboarding goal explicitly authorizes implementation,
Bugbot review, merge and deployment. Serial slice based on `c95e7d80a06151620ba1795850dbe4aa7c5c6843` in branch `codex/onboard-guest-build-config`; no live runtime, database, port or public release is leased by this implementation.

Outcome: production image builds can explicitly compile the existing owner review,
guest page and guest Home public-ID settings, while default builds remain off.
A release image built for one configuration must not be silently reused for a
different one. These settings are public build inputs, not credentials; they do
not enable backend APIs or approve/publish a World. Public release and private
preparation remain gated by the existing guest release contract and owner review.

Write set: `Dockerfile.production`, `scripts/prepare_buddy_release_image.sh`,
focused release-image helper tests and this handoff. Verify validated inputs,
default compatibility, configured tag and label identity, image reuse/mismatch,
and a real isolated UI build where available. Run repository exact-SHA hosted
frontend verification and an independent Bugbot review before merge. Backend
and deployment are unchanged by this slice. No other implementation lane was
assigned in this workstream; open PR search found no Dockerfile.production match.
