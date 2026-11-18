# AGENT — Record retrieval decisions for replay

Status: ACTIVE under the user's unified reply Details goal. Serial successor
to merged Buddy #3764 (`cbe8ae70d`), which is running on 5202 and passed the
one-trace-read browser check. This slice consumes merged Core #210
(`89fdd9f6163effba353fe232ede31f5124ce01a8`).

Branch `codex/buddy-replay-retrieval-decisions` uses the existing
`graph-timeline-layouts/DungeonMindBuddy` checkout. Its write scope is the Core
dependency pin, immediate retrieval adapter, validated operation and selection
metadata, trace projection, and owning regression tests. Replay visual changes
follow serially. Tests use disposable resources and no operator data.

Keep directed hops and bounded object-cap omissions tied to the exact saved
operation. Keep explicit controller exclusions tied to the validated typed
decision and exact attempt. Historical fields remain optional. Metadata does
not enter the model retrieval payload and grants no evidence or access.

Verify the locked backend and affected query-and-answer contracts, inspect the
exact cumulative change independently, then merge. The consuming replay slice
must prove a fresh Elderwyld hop and pruning decision plus legacy behavior,
evidence and responsiveness on 5202.
