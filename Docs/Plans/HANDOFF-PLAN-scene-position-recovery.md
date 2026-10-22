# PLAN — scene position through navigation and reload

SETTLED. #1585 merged9d3ce62ae6969b514043f134c32c2a2f287e0497 and is running
on UI5202. Bugbot independently approvedf9447a9a (15 focused tests); typecheck
and production build passed. Actual second-card selection survived full reload,
Plan→Play→Plan navigation and Document reload, then Cards. Scene note,18 protected
host tables/687 rows, Combat revision3, independent actor state and exact
mechanics/World association stayed unchanged. UI-only rollout retained1494 APP
rows with API unchanged. This is session-local view memory, not cross-device
position sync or full adventure acceptance. The implementation lease is released.

PRIME owned this serial dependent slice from origin/main
110f7e9ae2d546ce254c02078d125ff8e33eebf7 in buddy-context-loop,
branch codex/plan-scene-position-recovery. Current open PRs have no overlapping
active implementation lease. No new service, database, provider or Graph writes.

One capability: retain an explicitly selected Plan scene when the host unmounts
or the page reloads, including a round trip through Play/Combat. Session-local
browser view state is advisory, keyed by exact World and saved Plan IDs. It
contains only the scene ID. The current draft projection must contain that scene
before it can become the focused card or document scroll destination. No cursor
may switch World/document, mutate content, or manufacture an Agent edit lease.
Missing, stale, malformed or unavailable storage falls back to ordinary scene
navigation without blocking editing or changing the writer. Other tabs retain
their independent session cursor. New blank Plans do not borrow saved positions.

Failure cases: async initial load must not overwrite the stored selection with
the first scene; outgoing callbacks cannot write a different scope; removed scene
IDs cannot become editing targets; returning to a Plan restores Document/Cards
position without touching committed content, drafts, notes or Play progress.
This is view state, not an APP/Graph authority or a new recovery copy of content.

Exclusive write lease: this handoff; predecessor
HANDOFF-COMBAT-shared-surface-continuity.md and ROADMAP-demo.md settlement;
apps/live-control-ui/src/planSurface/planScenePosition.ts and its tests;
PlanSurfacePage.tsx and its owning integration tests. No API/schema/dependencies.

Verify mounted Plan selection→unmount→remount in Cards and Document, scope
partitioning, removed/malformed cursor, storage denial, unchanged writer calls,
existing card edits/ABA and same editor continuity. Bugbot exact cumulative review
then PRIME merge and guarded UI-only5202 delivery. Ordinary Plan→Play→Plan and
reload must retain the scene; saved Combat actor state and notes stay unchanged.

Predecessor #1584 merged110f7e9ae and delivered on5202 after Bugbot approved
1fb02706. Ordinary synthetic Plan Combat unsaved note→close→explicit recovery→
Play explicit recovery→Save revision3→Plan reopen succeeded. Same API restart
preserved1494 APP rows/59 product files;18 protected host tables/687 rows stayed
identical. Exact mechanics/association/Graph head remained unchanged. Full page
navigation reset Plan's scene to the first card, motivating this slice. This
witness does not award full adventure/J1–J6 acceptance.
