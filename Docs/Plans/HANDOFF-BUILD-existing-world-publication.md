# BUILD: review worldbuilding into an existing World

Status: ACTIVE — PRIME owns this UI-only serial slice under the operator's
request to ingest authored Edge material into an enriched, traversable graph.
Base: origin/main@cbd3a901c62199c56c66c66e7f1a5a540bdbdfb6.
Branch: codex/build-existing-world-publication. Reuse buddy-context-loop checkout
and shared dependencies. ARCHITECTURE independently reviews; PRIME merges and
adopts on 5202. No new checkout or environment.

## Contract

Expose the existing server-owned worldbuilding capabilities, prepare and confirm
contracts in exact-run Graph Review. Do not modify backend authority, schema,
source data, extraction or the graph during implementation/verification.
Existing-world readiness is independent of generic recap promotable and
first-world eligibility. Resolve the verified managed World through its existing
native projection; capability configuration alone does not establish readiness.
A missing binding permits the existing first-world UI only when the exact
review also explicitly reports an uninitialized eligible World. Other read
failures never bootstrap or fall back to another World.

Every assertion starts deferred. The GM explicitly creates/binds/omits nodes and
accepts/omits relationships, retaining visible source and draft qualifiers.
Binding selects a real native identity from the resolved projection. Preparation
is an explicit action: it admits exact source provenance and seals identity,
but publishes no graph facts. Display the exact returned plan and its proposed
effect; a separate Confirm posts that unchanged plan. Validate returned run,
source, World/binding and expected-head identities. Stale source/head, errors,
unknown confirm results, selection changes and unmounts never auto-reprepare,
auto-confirm, substitute current source or retry a publication.

## Exclusive write set

- This handoff
- apps/live-control-ui/src/api/worldbuildingPublicationApi.ts and its tests
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorldbuildingPublication.tsx and its tests
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx

The existing backend contracts are consumed unchanged. No registry, APP-STATE,
provider, profile, source-correction, telemetry or runtime source changes.
Any new durable contract or missing authority requirement is a stop/rebrief.
DOGFOOD's semantic source-snapshot successor remains separate and BLOCKED.

## Verification and delivery

Test mounted existing/first-World separation, all-deferred initial decisions,
bind-existing identity and omitted edges, explicit one prepare/one confirm,
exact plan round-trip, stale head and unknown result, malformed identity,
selection/unmount races and zero writes on inspection. Reuse existing frontend
tools; typecheck/build and inspect the cumulative diff. Commit/push/open one PR,
obtain exact-head independent review, then PRIME merge and UI-only adoption with
old assets retained and original user draft untouched. Verify exact Edge review
renders the new choices without pressing Prepare or Confirm. Actual semantic
approval and graph publication remain distinct from UI delivery.

## Implementation evidence before independent review

Authenticated client and mounted publication component consume the existing
contracts without reconstructing the sealed plan. Exact source/World/binding,
head, decision snapshot and receipt identity are checked. Every initial choice
is deferred. First-world UI is reached only after explicit missing native
binding plus the exact review's uninitialized/eligible state. Other errors fail
without bootstrap. Unknown confirm outcomes disable another POST.

64 focused client/mounted/Workbench integration/first-world tests pass; UI
typecheck and production build pass (existing large-bundle warning). Broader
Workbench module suite has 17 failures: exact base and current have the same
17 full test names, with no new failures. Baseline was exercised by temporarily
restoring only the module from the pinned base, then restoring implementation
bytes in a finally block. Private logs remain in existing .pytest_cache under
worldbuilding-ui-*. No provider, preparation, publication or retained-data
mutation was used for verification. Independent review and delivery are pending.
