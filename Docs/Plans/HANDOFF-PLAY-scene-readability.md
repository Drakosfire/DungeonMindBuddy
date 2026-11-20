# PLAY: readable authored Scene headings and tables

Status: ACTIVE — PRIME designs and authorizes this bounded correction under the
operator's live Build→Plan→Play dogfood objective. Independent ARCHITECTURE review
is required before PRIME merges and adopts on5202.
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
