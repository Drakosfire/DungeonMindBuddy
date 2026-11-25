# ONBOARD: guest Play session review

Status: ACTIVE under the owner's delivery, review, merge and deployment authorization. Serial slice based on serving 65f8b33b06e4aaf559cdaff090b42bfb87a038aa; branch codex/sizzek-review-latest-head; carried unchanged from merged #4772 after another production release. Owns guest review route admission and transport, the review transaction guard and bounded storage, focused tests, and this handoff. Open Play/guest PRs were checked and own separate work. No production database or runtime lease.

Outcome: guests can end, read, save and reopen their own Play session review using existing controls. Guest writes lock the active session before the Run, serialize with reset, bound the full retained review payload, and preserve exact-command replay. Foreign Worlds, missing CSRF and disabled features remain denied; signed-in paths stay unchanged. Guest Play proposals and final acceptance remain required successors.

Verify mounted guest end/replay/quota/reopen, cross-guest denial and reset race with an observed lock waiter; check narrow route/transport scope and authenticated review regression. Obtain independent review, recheck the serving parent, merge and deploy via Actions; verify the actual signed-out review control on production.
