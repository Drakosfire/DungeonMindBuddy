# ONBOARD: guest Build proposal release wiring

Status: ACTIVE under the owner's signed-out Sizzek delivery and merge/deployment authority. Branch `codex/onboard-guest-build-proposal-release` starts from Buddy main `3b4cacedb11f75fc728f4bc3def7f38fe6124a43`, after merged source PR #4694. This release-control slice is parallel-independent of serving integration #4693 and the serving PRs #4686/#4687; the actual release must follow their deployed serving-parent order.

Outcome: bind the already merged default-off guest Build proposal frontend and backend switches to a distinct image identity, staged record and candidate-only runtime configuration. Preserve existing modes and rollback behavior. The normal Build editor remains the surface; no new workflow or page.

Write lease: Dockerfile.production, publisher workflow, production Compose/staging/activation helpers and their focused shell tests, guest image verifier/config tests, cutover runbook and this handoff. No production service, provider or database is used in implementation. Verify focused image identity/dependency checks and staging/activation with candidate-only and rollback tests; inspect cumulative diff and obtain exact-head Bugbot review. Live integration and deployed acceptance remain separate.

Predecessor settlement: #4694 merged at `3b4cacedb11f75fc728f4bc3def7f38fe6124a43`. Its HTTP synthetic-provider and mounted mocked-transport evidence is separate, so the merged source does not establish joined browser/server or real-provider production behavior.

Working-tree checkpoint: Docker build argument, Compose default, publisher input/dependency, distinct image tag/label, and source verifier are wired. The source verifier accepts all prerequisites and rejects proposal activation without Play Buddy. Stage and activation record/overlay support and their failure/rollback tests are not yet implemented; do not publish or deploy this partial change.

Working-tree focused checks: 26 image configuration tests pass. The staging and activation shell harnesses pass with Docker/Compose stubs, including distinct identity rejection, enabled candidate, missing runtime switch and rollback. The source verifier rejects proposals without Play Buddy. These do not prove production activation or a joined guest workflow.
