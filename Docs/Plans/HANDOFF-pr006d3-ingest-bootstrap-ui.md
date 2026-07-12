# HANDOFF — PR006D3 — `/ingest` review and activation UI

**Blocked on:** PR006D2

## Mission

A GM can see exactly what campaign memory will be created and explicitly publish
it from `/ingest`.

## Scope (allowlist)

- Consume the exact PR006D2 API contract (shared/generated fixture — no hand mocks)
- Render review projection: hubs, party/PCs, session events, relationships,
  Tripod attributes, source classification, trust boundaries / non-claims
- Confirmation UX enabled only after review surface is shown
- Active / advanced / blocked / invalid_bundle health display
- Vitest coverage against contract fixture; dogfood on `/ingest`

## Explicitly out of scope

- Kernel initialization (PR006D1)
- Backend acceptance policy / prepare-confirm service (PR006D2)
- Projection Engine / Plan migration

## Blocking findings from #336 to absorb

1. UI must not invent response shapes
2. Confirmation must review real memory, not only digest + totals

## Verification

- Vitest panel tests using committed contract fixture
- Manual dogfood: prepare → review → confirm on a disposable world root
