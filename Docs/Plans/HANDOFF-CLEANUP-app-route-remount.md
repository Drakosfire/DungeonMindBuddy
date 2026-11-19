# CLEANUP: App route remount ownership

Status: ACTIVE under the standing cleanup goal's implementation, independent
review and merge authority. Serial successor to merged #4145. Base
`ca239ca90e42281f0a85ef10a5c62d0945ffaf92`; branch
`codex/app-route-remount`, reused isolated checkout. No runtime resources.

## Lease and contract

Only the E7 route-remount case in `apps/live-control-ui/src/App.test.tsx`, this
handoff, and removal of completed `HANDOFF-CLEANUP-world-run-query-history.md`.
Open PR path inventory checked: #2405 owns obsolete shared wrapper setup, untouched.
Complete cached #3824 paths exclude App.test.tsx. No shared mock, runtime,
classification, Plan implementation or Agent implementation writes.

Current E7 never mounts its saved Build page: its snapshot fixture targets an old
API, while the controller uses committed page reads. Bare Plan now chooses a World
instead of opening C2. Agent chrome requires a real Ask plugin (merged #701);
do not manufacture registration or preserve obsolete unconditional presence.

Exercise actual App/SelectedWorldProvider and saved Build → selected World Plan
→ saved Build remounts. Supply case-local typed admission and committed-page
responses at current owning APIs. Require ready editor/page identity, singular
ToolHost/EditHost where owned, and real plugin-driven Agent ownership. Establish
the selected Plan's real plugin before asserting presence. Check outgoing hosts
are removed after unmount, rather than accepting duplicate remnants. Preserve
all other case bytes and the E7 ID. No provider/Chat/model calls or saves.

If current selected-World Plan cannot be exercised within this fixture boundary,
stop and revise scope before substituting an entry-only page or fake plugin.

## Verification and predecessor settlement

#4145 reviewed head59d1d0df9d44fcd0b3f05cffd707e7bef5dcd139 merged at base.
Full8147pass103fail2pending,8252reported/8250inventory; exactly query-history
fail→pass, three bare-Run owner controls green. Hosted1406/build/validator0.
Merge adds backend/docs only; frontend verification inputs unchanged. Its cold
one-worker Plan-loading observation remains unresolved, despite integrated pass.
Original247 dispositions remain229bounded+18residual. Git preserves predecessor.

First use isolated exact-source focused diagnostics under the frontend lock and
verified Projects storage. Preserve failures; clean owned scratch. Then exact-head
hosted/build/validator and full discovered identity/status comparison, independent
cumulative review, docs check. Full qualification remains red. No arbitrary
timeout/preload, test deletion, fabricated ownership or weakened runtime guards.

## Diagnostic contract correction

Initiala7b6d63 focused cold Build import timed out; complete module reached Build
but exposed missing editor snapshot (controller committed-read and canvas authoring
read are distinct). ee93174 supplies both and restores prior mock implementations;
its module reached Plan but old Agent chrome selector was absent. Current owner
`daa92ae2e` introduces PlanConversationDockAdapter; current adapter owns the shared
ConversationDock and redirects Agent chrome to a launcher. Assert one actual dock
and real WorldPlanAgentConversation composer, zero obsolete chrome, and outgoing
dock removal. This preserves Agent/remount coverage under current presentation,
not a chooser-only substitution or fabricated plugin. Retain both failed attempts.
