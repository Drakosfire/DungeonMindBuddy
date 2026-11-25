# ONBOARD: edit a guest Play session copy

Status: ACTIVE under the owner's one-shot delivery, review, merge and deployment authority. Serial slice based on serving 31690f7dce1038d001db2cbee3a1abc940b3a7f9; branch codex/sizzek-guest-play-edit. Owns guest admission and transport for Play content history/commands, the guest transaction guard and its bounded edition storage, the Play edition commit callback, focused tests, and this handoff. Open guest/Play PRs were checked and cover separate work. No production database or runtime lease.

Outcome: signed-out guests can save and reopen edits to their own existing session copy through normal Play controls. Keep the saved Plan and other guests unchanged; bind each write to the live guest session and reset lock before Run locks, retain exact-command replay, enforce edition count/byte limits, and reject cross-World or invalid requests. Signed-in paths remain unchanged. Guest session review, proposals and full signed-out acceptance remain required successors.

Verify mounted HTTP save/reopen, stale conflict, exact replay at quota, CSRF, two-guest denial, reset-vs-commit serialization and source preservation; verify transport scoping and existing authenticated content behavior. Obtain independent review, recheck the live serving parent, merge, publish and deploy via Actions; smoke actual guest editing on production.
