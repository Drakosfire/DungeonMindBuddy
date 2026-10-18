# BUILD: review worldbuilding into an existing World

Status: DELIVERED — PR #1400 merged as 5ebb1794fa2e78359c07db9e09cbb8f3d66434d3 after ARCHITECTURE Cycle 2 PASS on f2ef3e1f6c673bf5be185f8acec0c73e122faffe. The implementation lease is closed. Historical scope: PRIME owned this UI-only serial slice under the operator's
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

- apps/live-control-ui/src/api/liveApi.ts (only exact existing-world publication authorization classification)
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

## Review Cycle 1 and bounded lease extension

ARCHITECTURE held exact b834e26c875221152a4ad7ff2632d6e64635ec60: real
transport authorization classification omitted these paths, and nested prepared
source digest could contradict the reviewed sha256 source revision. PRIME
explicitly extends this slice to liveApi.ts solely for the exact three existing
worldbuilding endpoints. Real-helper tests belong in the already leased client
test file; no backend/auth-policy weakening or new automatic mutation retry.
Check nested source digest correspondence and document binding shape before
showing Confirm. Re-review the complete revised head after both corrections.

### Review corrections verified before Cycle 2

The exact capabilities/prepare/confirm paths now enter the real local GM
authorization classifier. Real-helper tests mock only fetch: configured bearer,
session restoration and CSRF, nonloopback rejection, invalid bearer and trusted
CSRF rejection. The existing helper may refresh the local session after an
auth rejection; prepare/confirm remain excluded from its mutation retry list
and each publication endpoint is sent only once. No backend guard changed.

Prepared publication sourceSha256 must equal the reviewed sha256 revision, and
document ID/revision shape is validated. Contradictory/malformed nested digests
are rejected before Confirm. 77 focused tests, typecheck and production build
pass. Existing broad baseline failures remain as recorded. Independent Cycle 2
and deployment are pending.

## Delivered acceptance and remaining work

ARCHITECTURE independently passed 77 focused tests and typecheck, plus four
additional mounted binding/unmount checks. Review Cycle 1 HOLD and Cycle 2 PASS
are retained as history; no CI statuses or workflow runs existed at merge.
PRIME verified the exact cumulative eight-path diff and guarded the merge by
the reviewed head.

A pinned baseline build exactly matched serving index
43b1234f36dffbea1816cb4aac88ae1d89ce09049f0dcb9f2b10646f333c4d27. Only four
reviewed production files changed in the candidate build. UI-only adoption on
5202 installed index fa24cd18cee70e305b3074376a73c140dba4f1af610a612b245ccd98507c624d,
retaining old browser assets and UI PID 17085; no API restart, original operator
tab reload, provider call or database write. Private rollout authority/build/
receipt evidence is under the established jev-evidence-loop-20261016 state.

In a fresh verification tab, the exact saved Edge run loaded existing-World
review with 81 enabled assertion selectors, all initially deferred, Prepare
disabled, no Confirm and no alerts. A local-only choice successfully selected
existing Edge identity loc_3; Prepare then enabled and Confirm remained absent.
Neither action button was pressed. The original Build draft and the user's
Session29 tab were left untouched. DOM checks prove the controls; the hidden-tab
screenshot was blank and is not visual-layout acceptance.

This delivers the publication review UI, not semantic approval or publication
of Edge. Unsupported Velvet Reed identification, synthetic group representation,
missing civilian/location links, media graph bindings and concrete named refugee
records remain separate acceptance work. No Session26–29 correction or
publication is established by this delivery.
