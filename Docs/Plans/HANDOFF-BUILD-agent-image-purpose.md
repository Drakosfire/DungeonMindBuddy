# Agent image purpose into Image Studio

Status: CLOSED implementation lease; merged #1405 at897cf77f58baf3351f8ae969c798b7489e8e4d46,
reviewed aa9a2d9c9173cc54dd0f7634f1f85207e1cb3077. API/UI adopted with preserved
retained state. Live acceptance exposed a separate serving IPC producer still
omitting purpose; follow-up contract HANDOFF-BUILD-agent-image-purpose-ipc.md owns
that producer. The successor merged1406 at308accba and ordinary Agent→prepared action→wizard
Map acceptance passed; see successor settlement. Historical base
b73b3f6225aaed4954a86a54005c6837eeaa49e9. One bounded capability, one PR.

Observed current5202 turn0d79e139-5d06-487d-bbab-a50c650bce19 prepared and opened
a map prompt but Image Studio selected Illustration. No image was generated and
Edge was not saved. Fix explicit purpose propagation, not prompt keyword inference.

Contract: new strict writer direction includes required purpose map|illustration.
Keep parsing old prompt/alt-only writer proof. Stored v2 preparation gains optional
purpose, absent means legacy unspecified; preserve existing result digests exactly
when absent. Present purpose is proof-bound, idempotency-bound and included in
result digest. UI initializes purpose explicitly and validates fresh purpose on
reopen; legacy unspecified stays Illustration. Manual purpose changes remain.
No generation, placement, save, public media or user-source behavior expansion.

Rebrief: owning tests exposed the closed durable writer-policy literal; add only
src/application_state/agent_conversation/types.py to accept the new explicit policy
alongside the unchanged old policy. No schema migration or other scope expansion.

Exact paths: this handoff; src/application_state/agent_conversation/types.py; src/application_state/build_proposal/types.py;
src/application_state/build_proposal/images.py;
src/application_state/agent_conversation/build_authoring.py;
apps/live_control_server/services/build_image_writer.py;
apps/live_control_server/services/build_jev_harness.py;
apps/live-control-ui/src/media/PreparedBuildImage.tsx;
apps/live-control-ui/src/media/MediaImageWizard.tsx;
tests/test_build_jev_image.py;
tests/test_build_image_tool.py;
apps/live-control-ui/src/media/PreparedBuildImage.test.tsx;
apps/live-control-ui/src/media/MediaImageWizard.test.tsx.

Owning proof: actual mocked Harness writer→DB preparation→completion/reopen for
both purposes; purpose tampering/idempotency conflicts reject; old proof/digest
reopen unchanged. Mounted prepared host passes explicit purpose, wizard generation
request carries it and manual selection remains possible. No real image generation.
Use shared dependencies and only unique disposable54329 test DBs, never retained
54330/54331. DOGFOOD's actor paths are disjoint; shared fixture uses unique test DBs.
No new worktree/environment/preview or /tmp task directory. Tests, cumulative diff,
commit/push/PR, ARCHITECTURE exact-head independent review, PRIME guarded delivery.
Preserve all active drafts/media/Run pins; live acceptance only through a separate
tab and deliberate prepared-wizard request, no user page Save/reload.

Pre-review proof: 22 owning Harness/tool tests pass against unique54329 fixture
DBs, including map/illustration, missing/invalid purpose, forged persisted purpose,
legacy schema/proof/digest reopen and idempotency conflict. Seventeen mounted
prepared-host/wizard tests, UI typecheck, production build, scoped Ruff F and
cumulative diff checks pass. Build retains the existing chunk-size warning.
Initial tests exposed the closed policy literal, now fixed within the rebrief.
No runtime delivery, image generation or Edge source save is claimed yet.
