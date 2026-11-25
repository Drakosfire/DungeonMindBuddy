# ONBOARD: guest Play proposal history

Status: ACTIVE under the owner's one-shot delivery, review, merge and deployment authorization. Serial slice based on serving 675495998fbcd888525c7e66eaaf574646c21e73, branch codex/sizzek-guest-play-proposals. Owns read-only guest proposal admission/transport and focused tests. Open guest/proposal PRs were checked; they own other paths. No production database or runtime lease.

Outcome: the normal guest Play UI can list and read proposals belonging to its own Run without a 401. Admit GET only, behind existing Play and Buddy flags, with canonical selectors, same-origin session admission and World checks. Do not enable proposal generation in this slice: its model input can contain host-owned identifiers in scene markers and media references and requires a separate prompt-boundary correction, as well as bounded generation and reset-safe writes. The full one-shot objective remains active.

Verify feature-off and method denial, guest/foreign World isolation, malformed selectors, reset and guest transport. Independently review the cumulative diff, recheck serving parent, merge and deploy through Actions; verify a fresh guest Play session no longer receives a history 401. The guest proposal writer and final end-to-end acceptance remain required successors.
