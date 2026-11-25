# BUILD — Reopen an unchanged page’s pending placement proposal

ACTIVE. The placement release goal assigns this slice to this chat’s clarification app lane.
One serial PR from main at `94961697e1880eb77c14eb498513b2e697a90eab`, on
`codex/build-proposal-cold-restore`. The serving predecessor is #4676 at
`4000e9da04dea6d514ffbf899e64921dc8783426`. The release follows review of
the restore slice on main and verification on the serving base.

The write scope covers the existing authenticated Build proposal review read and
open responses, their proposal lookup, the Build editor restore path, focused
authorization and placement regressions, and the action catalog. Use the existing
isolated clarification app database for the HTTP checks. Review the unchanged
plain page with temporary editor IDs missing after cold reload, the exact
paragraph boundary, changed content, and denied access. Preserve the existing
apply and save receipts and require the author to accept before mutation.

Preserve guest Graph and guest Build during release and keep #4559 separate.
Run one deployed smoke that verifies the saved question, answer, proposal, and
unchanged page through reload. Leave that proposal unaccepted.

## Serving port

Main merged #4680 at `015e3f1339dddfd6c5661d67fa2b639c825da86d`.
The serial serving port uses `codex/build-proposal-cold-restore-serving`, based
on #4679 at `928cfbc75cba30bdee2a4a0666cbcc8151ac0f8c`. Confirm that exact parent
is live before merging the port so the publisher can still select the deployed
predecessor. Preserve every enabled guest option on that parent.
