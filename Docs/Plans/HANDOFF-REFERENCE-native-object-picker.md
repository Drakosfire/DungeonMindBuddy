# Native object reference picker

Status: ACTIVE. Owner: PRIME. Topology: serial. Base: origin/main
04d9d6793e197f50069b5b77ea89b3db3d26c9af. Authority: operator's active reference goal;
proposed design at 0f7c696ecbf2cb8d9cfe92a6927b5eada14e5f41.

## Outcome and expected write lease
Discover the same admitted objects as the native Graph browser, including Fellinor;
select exact native identity, binding and selection revision. Selection remains unread.
Exclusive writes: this handoff and these apps/live-control-ui/src files:
- surface/SurfaceGraphReferenceInput.tsx, its .test.tsx and .css
- graphLens/NativeGraphInspection.tsx and its .test.tsx

Adopt the existing native catalogue and inspector with optional explicit selection.
Remove the picker's projection hooks, classic adapter and classic inspector dispatch.
GraphReferenceSearch and its adapter retain other live callers; do not delete them.
No endpoint, authority, provider call, dependency, durable schema or database mutation.
ADVERSARY PR2079's ingestion runtime write set is disjoint.

## Failure cases and validation
Distinguish unavailable from empty, permit refresh, reject foreign scope/World and
inconsistent catalogue pins, discard late responses and reset on World change.
Keep duplicate labels distinct, name variants searchable, partial coverage visible
and every returned entity reachable without the old hidden 40-result ceiling.
Inspection does not select; selection does not read source bodies. Historical mode
requests no catalogue. Preserve chips on errors and disable new selection when busy.
Run owning UI tests, typecheck/build and existing native authored acquisition checks.
Require independent exact cumulative Bugbot review followed by author diff inspection.

## Dependencies and delivery
Reuse checkout, UI node_modules and .venv. This grants no runtime lease. After merge,
re-anchor and lease actual UI/API delivery with retained-data/draft conservation and
served-release verification. Three-surface dogfood and operator acceptance remain
open. Recaps, passages, restrictions and wider Plan/Play integration are later slices.
