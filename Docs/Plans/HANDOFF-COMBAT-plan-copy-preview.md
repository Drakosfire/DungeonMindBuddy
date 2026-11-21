# COMBAT — preview and confirm a saved encounter in Plan

ACTIVE under the Old Bath House end-to-end goal in chat
01a1ef4e-ff74-7d11-bd9a-2a499da090ff. Serial successor to merged #4316.
Root owns the Plan Combat projection UI. Base
`0559b54fa7095eb10cf7e917d386ce1613d077fd`, branch
`codex/combat-plan-copy-preview`, existing fc67 checkout. No hosted or
shared runtime write lease. The open PR file census reported no overlaps
in PlanSceneEncounter or sceneTemplatesApi. Portrait #3808 and the Build
AW10 #4312 agent lane remain independent.

The existing Plan scene drawer will list committed World encounter sources
on demand, preview exact source revision and roster, then attach a copy
only after confirmation against the exact clean saved target Plan. A
stale preview requires review and a new intent. Retain existing creation,
retry, cancel, readback, and occupied-scene behavior. Use the existing
Combat list and preparation transaction. Keep the copy intent recoverable
after reload and distinguish its digest from legacy empty/custom intent.

Expected writes: this brief, predecessor status, PlanSceneEncounter,
sceneTemplatesApi, and their owning tests. Verify visibility, no write
before confirmation, revision and target binding, exactly-once retries,
and no mutation for dirty or occupied targets. Use exact-head hosted
verification plus discovered diagnostics and independent review. Agent
conversation proposal integration and end-to-end art/Play continuity
follow in their owning slices; this preview is the reusable user-facing
confirmation path.
