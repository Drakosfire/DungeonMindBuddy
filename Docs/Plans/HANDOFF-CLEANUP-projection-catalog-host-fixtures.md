# CLEANUP: mount current presentation in catalog integration fixtures

Status: ACTIVE under the user-authorized cleanup goal, including review and merge.
Base: a5060c55611e30bdd950f3be44d3afed7ee67f0b.
Branch: codex/projection-catalog-host-fixtures in the existing cleanup checkout.
Topology: serial after merged #4082; no unmerged behavioral dependency.
Owner: cleanup steward, independent Bugbot review before merge. Follow-up #4074.

Outcome: repair three catalog integration cases whose projection-only fixture
omits the singular production ToolHost. Mount the real ToolHost and Peek region
provider/slot, then select the intended tool from the visible drawer. Reset each
Ingest case to /ingest so a preceding tool URL cannot pre-open its projection. Preserve
all exact renderer inventories, sibling exclusion, registration uniqueness,
missing-binding and ready-payload assertions. Do not replace catalog/host runtime
with mocks or bypass the user interaction. No runtime product changes.

Write lease: apps/live-control-ui/src/planSurface/projection/projectionCatalogRegistrations.test.tsx,
this handoff, and HANDOFF-CLEANUP-chrome-band-owner-fixtures.md for truthful
predecessor settlement. All 61 open PR file lists checked at activation; no overlap
on the existing leased files. Shared test hosts, runtime owners and active branches
are read-only; this fixture helper stays local to its test module.

Verification: focused before/after diagnostic first. Exact-head hosted verifier,
production build and validator, then full discovered diagnostic under the global
frontend lock with verified Projects external scratch. Compare complete inventory,
all failure IDs and leading messages with retained byte-identical parent frontend.
Require all original module cases to pass and exactly three inherited failures
to resolve without new failures or omissions. Preserve unrelated red results,
conditional inventory extras and unresolved quote-correction observation. Obtain
independent cumulative exact-head source and raw-evidence review before merge.

No application servers, providers, operator databases or remote host writes.
Original cleanup owner/release gates remain outstanding.
