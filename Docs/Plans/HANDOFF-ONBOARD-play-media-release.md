# ONBOARD: Release guest Play and inline media

Status: ACTIVE under the owner's Sizzek delivery, review, merge and deployment authority. Serial release-control slice on `codex/onboard-play-media-release`, based on `4f9119048372436419672525b10fecacb560d2ff`. Merged guest Play #4682 and guest inline media #4684 precede this slice. The currently serving Plan/documents release is `928cfbc75cba30bdee2a4a0666cbcc8151ac0f8c`; a serving integration based on the actual production parent follows this control slice. This implementation leases no production runtime, provider or database.

Outcome: publish and stage a release that enables existing guest Play and inline media alongside Graph, Build, Plan and source documents. Image identity, serving parent and staged settings must bind all flags; defaults remain off and older modes remain compatible. Play requires Plan; media requires Build. This is not full ingestion or guest Buddy.

Write lease: this handoff, `.github/workflows/publish-buddy-image.yml`, `scripts/verify_guest_graph_release.sh`, `deploy/production/stage-buddy-release`, `deploy/production/activate-buddy-release`, their focused shell tests and `tests/test_guest_release_image_config.py`. Open PRs were inspected; older serving integration PRs are separate lanes. Recheck before merge.

Verify focused publisher configuration and shell staging/activation cases, including wrong image configuration, invalid dependencies, persisted flags, rollback and retention parsing. Inspect the cumulative diff and request Bugbot review. After merge, integrate against the actual serving parent, publish and deploy the exact reviewed candidate, then verify actual guest Play and media with the production provider. Preserve the recorded rollback limitation.
