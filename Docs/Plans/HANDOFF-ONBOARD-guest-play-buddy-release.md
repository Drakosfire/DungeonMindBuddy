# ONBOARD: guest Play Buddy release wiring

Status: ACTIVE under the owner's Sizzek delivery authority, serial successor to merged Play discussion #4691 and Buddy release controls #4690. Branch `codex/onboard-play-buddy-release` starts at main `b2d3dee88735026dfbfa0a0efa023782314f25a9`. Earlier serving releases must be activated in order before this capability can be deployed.

Outcome: explicitly bind Play Buddy frontend and backend switches to a distinct candidate image identity, staged record and candidate-only runtime overlay. Existing Buddy and other release modes stay compatible; a prior Buddy-labelled image must never be mistaken for one containing Play Buddy. Preserve guest World, source, image, rollback and session protections.

Write lease: Dockerfile.production, publisher workflow, production Compose/stage/activation helpers and their focused tests, guest image verifier/config tests, cutover runbook and this handoff. No live service, database, provider or production state is leased. A serving integration carrying product code remains a separate successor after the exact serving parent is live.

Verify focused image configuration, staging and activation harnesses including prior-mode compatibility, mismatched image identity, missing runtime switch and rollback isolation. Obtain Bugbot review at the exact head. This slice does not establish live provider quality or signed-out production acceptance.

Working-tree evidence: 25 image configuration tests pass; staging and activation harnesses pass with Docker/Compose stubs, including old Buddy image rejection, missing Play Buddy runtime switch and rollback isolation. Preliminary Bugbot static review found no actionable defect; exact-head review remains. These checks do not constitute real Docker or production acceptance.
