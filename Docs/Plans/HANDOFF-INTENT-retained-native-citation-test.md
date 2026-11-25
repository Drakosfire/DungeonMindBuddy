# Intent: verify retained native citation reopening

Status: ACTIVE. User authorized intent-first verification and focused review/merge. Serial test-only slice based on `codex/sizzek-play-edit-base` at `65f8b33b06e4aaf559cdaff090b42bfb87a038aa`; branch `codex/intent-retained-citation-test`. No runtime, provider, database or production changes.

Extend the existing pending native citation owner fixture to re-admit an actual prior source read into a synthetic later pending turn with no new source settlement. Verify exact reopening and current binding denial. The later turn is a synthetic model copy with a stubbed inspect service and retains the prior completion; it has no newly authorized writer or completion binding. This exercises only retained source resolution, exact bytes and changed-binding denial. It does not prove a valid stored follow-up, producing-citation binding, revoked source admission, or prior-reference recursion.

Write set: this handoff and `tests/test_build_source_free_protocol.py`. Verify the changed case, adjacent direct citation and route authorization. Obtain independent exact-head review.
