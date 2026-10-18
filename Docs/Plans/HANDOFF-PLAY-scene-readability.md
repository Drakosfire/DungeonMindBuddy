# PLAY: readable authored Scene headings and tables

Status: SETTLED — implementation merged as PR #1402 at
6743466d5f167f26d49c14d87b6353a35843f39e after ARCHITECTURE exact-head
Cycle 2 PASS on c80064f160df4f2ee4364d67b1451582eff3583a. The exclusive
write lease is closed. UI-only delivery on5202 is verified;5268 is stopped.
Base: origin/main@15aa918eb91071b469ea7f733cce6d2c6a3262e6.
Branch: codex/play-scene-readability; reuse buddy-context-loop checkout/dependencies.
Topology: parallel-independent of held INGEST candidate-reader #1401 and DOGFOOD's
source-snapshot correction lane; no overlapping expected paths or dependency.
The existing serial checkout is reused; no new worktree or environment.

## Observed invariant and critique before activation

Actual saved Edge prep in Play renders body h4 headings rgb(241,245,251) over
parchment, and ability cells with1px padding/no border. The statblock's header
and values visually run together. Source/Plan/Run pin bytes are correct; this is
a rendered CSS failure, not extraction or persistence.

Authored Scene headings must inherit the paper ink while shell headings retain
shell colors. Tables must have clear cell separation and responsive natural
column sizing; long cells must wrap without page overflow at narrow widths.
Preserve original content, all headings/cells, Scene actions/inspection/Run cursor,
notes and pin identities. Do not hide text or modify semantic content to work
around styling. Failure cases: broad shell-color override, missing h5/h6 styling,
fixed/equal widths, narrow overflow, stylesheet-order regression and unreadable
choice/source context. No new runtime/public/data contract.

## Exclusive expected write paths

1. Docs/Plans/HANDOFF-PLAY-scene-readability.md
2. apps/live-control-ui/src/playSurface/playSurface.css
3. apps/live-control-ui/src/shared/SceneCard.stories.tsx

Only existing Play cockpit authored-body selectors and an isolated synthetic
Scene story are changed. No shared renderer, app state, provider, API, dependency,
Graph or live document mutations. No code from held #1401 is adopted.

## Verification and delivery

Use the real shared Scene renderer under the actual Play cockpit CSS, synthetic
headings h2–h6 and ability/long-text tables, at desktop and narrow widths. Prove
heading ink, cell padding/borders, preserved content and no document overflow.
Inspect screenshots. Focused existing shared-adapter and Play cockpit suites,
typecheck/build, cumulative base→head diff; commit/push/open this one PR.

A single temporary Ladle preview on127.0.0.1:5268 is permitted only for this visual
check. PRIME owns start/stop, first verifies the port is free, and stops it after
review. Reuse established dependencies and checkout-local .pytest_cache outputs;
no source export, new environment or /tmp task directory. Never change5202 until
independent exact-head PASS and guarded merge.

UI-only adoption on the existing5202 unit preserves API8000, older hashed assets,
all source/Plan/Run pin hashes, notes and original user tabs. Recheck the actual
Edge walkthrough read-only after delivery; no new Run, source, provider or Graph
write is required. Mutable completion authority is this handoff only.


## Delivered evidence and limits

Independent actual-browser checks at measured1280px and390px preserve all18
fixture cells and body text, paper heading ink, shell colors, complete short
headers/numerals/modifier tokens, natural column sizing and no page overflow.
80 focused tests and typecheck pass independently; production build passes.
Cycle1 exposed short-token splitting, corrected before Cycle2 PASS.

PRIME reproduced the prior serving index byte-for-byte before delivery and
atomically adopted only the reviewed CSS change. Runtime JavaScript bytes are
unchanged, previous hashed assets remain available, UI PID17085 is unchanged,
and API8000 was not restarted. Four retained Edge source/Plan/reference/Run
records hash identically before/after. Actual retained Edge Play headings and
ability cells verify the correction. No source, Plan, Run, note, provider or
Graph write occurred. This is presentation delivery, not acceptance of the
unplaytested encounter or completion of the broader session workflow.

Private build/rollout/preservation receipts: established experiment directory
jev-evidence-loop-20261016, play-readability-* evidence. The temporary5268
preview was stopped after both reviewers finished and its port verified free.
Held candidate-reader #1401 remains unadopted.
