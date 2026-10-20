# Current Plan/Play Cards only

Status: ACTIVE — Play successor. Operator authorizes removing remaining legacy
card paths with no backwards compatibility. PRIME/Buddy UI owns this serial slice.
Base cd98b4708a5cd5eb7ebd0ff1ad39c123e291d7f9; branch codex/retire-play-v1-cards;
reused buddy-context-loop checkout. Open PRs inspected; no overlapping active UI lane.
Architecture supplied the prior scope critique and reviews the cumulative successor.

## Settled predecessor
Plan PR1479 merged cd98b4708a5cd5eb7ebd0ff1ad39c123e291d7f9 after independent
Architecture cycle1 approval of d8f8467b3bbdbe14fc272fc8bc98092dac4f4e94. All117
tests passed independently, including all20 Plan integration cases without skips.
Production build passed. UI adopted on5202; desktop and narrow current-v2 Plan cards
rendered, unsupported-v1 Cards failed closed with working Document access. All14
protected JSON responses unchanged after browser checks, including the v1 source.
No conversion, API restart or provider call. Plan write lease released. Mock Agent
saveInFlight proves owner fencing, not downstream service enforcement; World identity
test remounts rather than same-mounted World switching. Known act warnings retained.

## Active exclusive Play write lease
- This handoff
- apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx
- apps/live-control-ui/src/playSurface/PlaySurfacePage.test.tsx
- apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx
- apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.test.tsx
- apps/live-control-ui/src/playSurface/runbook/index.ts
- apps/live-control-ui/src/playSurface/currentMoment/playRunMutation.ts
- apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
- apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.test.tsx
- apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.stories.tsx
- apps/live-control-ui/src/shared/SceneCard.adapters.test.tsx

## Contract and gates
Reject Playable grammar v1 at surface admission before ready/publication/active-pointer
or progress writes. Remove v1Deck/RunbookTableDeck renderer and its supported-v1 tests.
Move neutral mutation status to the currentMoment owner. API schema v1 names are not
Playable grammar compatibility. Lower parsers, source APIs, persisted Runs and migrations
are outside this slice. Do not convert, delete or silently repin stored data.
Migrate current successful Play surface fixtures to v2; retain chooser/load/rebase,
notes/CAS/session-copy/Agent fences. Add explicit unsupported-v1 no-write/publication
evidence. Full PlaySurfacePage and current cockpit suites plus Plan20/model/adapters,
production build, independent exact cumulative review, merge, guarded5202 UI adoption,
current-v2 and unsupported-v1 rendered checks, retained-state comparison, settlement.
Established5202 artifact directory only; no API restart or provider calls required.

Author verification:153 tests passed across8 full files (Play owner36, cockpit68,
Plan integration20, model14, adapters5, Contents7, layout1, deck2); no skipped cases.
Production build passed. Old renderer's18 tests are retired with that owner; current
cockpit68 covers notes/CAS/recovery/identity boundaries. Successful Play fixtures now
use v2 Beat/Scene structure, durable current Beat/Scene and exact pinned content hashes.
Contents selection uses current accessible buttons; progress re-admission uses current
note-save interaction. The v1 manifest rejection covers marked and unmarked source and
asserts no content/active/progress/rebase/World conversation publication. Current failed
admission cannot offer rebase. Lower source parser/API coverage remains unchanged.
