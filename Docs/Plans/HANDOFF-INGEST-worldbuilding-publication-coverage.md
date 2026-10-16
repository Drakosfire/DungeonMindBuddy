# Exact-run historical Worldbuilding publication coverage

ACTIVE. PRIME solo implementation; ARCHITECTURE independent review/advice.
Buddy base `2efb6ea184870df0f266ff98fe2eb9938c5d0366`, branch
`codex/worldbuilding-publication-coverage`, non-serving checkout
`/tmp/prime-recap-mention-boundaries`. Topology: cross-repository stacked consumer
of Core #128 reviewed head `5430d5ddca52f2aab0ae71f62556adbb41b44313`.
Core merged as `dd20b9734eeba5e17704c6e091bc0e61411e7964` after renewed
independent exact-head PASS and CI success; consumer pin uses that accepted merge.

## Outcome

An authenticated GM can reopen an exact Worldbuilding ExtractionRun and read
historical successful publication receipts and candidate/facet coverage without
the original prepared plan or replaying prepare/confirm. Resolve sealed run/source,
managed World and current native pin server-side. Read Core's complete verified
ancestry discovery, prove exact source ownership and candidate assertion mapping,
and recheck managed/source binding before returning. No caller-selected native
World, actor, source path, publication schema or mutable extraction-status write.

Match mapper-generated product assertion hypotheses to verified native assertions
by exact preserved ID AND normalized semantic/qualifier/source/evidence content.
Derive unique candidate→subject bindings from proven native facts; edges require
both endpoints. Reuse pure candidate/support mappers and native normalization at
the exact historical parent. Never reconstruct a whole plan or use today's alias
or identity ledger to invent historical decisions. Count only proven alias facts.
Ambiguous/unmapped published facts remain visible and prevent full-coverage claims.

Report existence, description, alias, source observation and relationship facets
separately. A bound description is not a newly published node. Native rejected
assertions can prove only their exact rejection; absence means not yet proven
published, never implicit rejection/deferral. Aggregate multiple immutable receipts.
Historical success survives later withdrawal; do not claim current active status.
Complete empty discovery is not_published; unavailable/corrupt/binding changes are
unknown/error, not zero coverage. Pending/failed attempt history remains a separate
contract; do not fabricate it from terminal success records.

## Exclusive write set

- This handoff
- `apps/live_control_server/ports/world_graph_authority.py`
- `apps/live_control_server/integrations/dungeonmind/world_graph_authority_adapter.py`
- `apps/live_control_server/integrations/dungeonmind/worldbuilding_publication_discovery.py` (new)
- `apps/live_control_server/models/worldbuilding_publication_coverage.py` (new)
- `apps/live_control_server/services/worldbuilding_publication_coverage.py` (new)
- `apps/live_control_server/routes/extract_promote.py`
- `tests/test_worldbuilding_publication_coverage.py` (new)
- `tests/test_worldbuilding_publication_discovery.py` (new)
- `pyproject.toml`
- `uv.lock`

No overlap with active #1235 UI observation review/confirmation, #1251 candidate
readiness or #1256 Ingest navigation leases (current PR file lists inspected).
DOGFOOD owns UI adoption and rendered/operator acceptance; send the reviewed API
contract after implementation. No serving ports, retained publication, source edits,
provider calls or migrations in this slice. Tests use synthetic memory/disposable
PostgreSQL and read-only retained acceptance only after independent review.

## Evidence and settlement

Prove fresh-service reopen without original plan, selective facets/multiple receipts,
source/World/run and auth isolation, unsupported/unmapped facts, exact evidence and
qualifiers, malformed/corrupt records and authority down, no writes/replay/first-admit,
and managed binding changes during read. Exercise real native publication through
the existing owning fixture and authenticated mounted route. Review the cumulative
diff, pin accepted Core merge, commit/push/open one PR, send exact head promptly to
ARCHITECTURE. Preserve beginning/end refs and results for future local-model gold.

Predecessor settlement: Core #128 added verified complete pinned-ancestry discovery;
its initial author82/independent46 tests pass. CI repair restores typed selection
construction without changing serialized semantics. Retained read-only Mirathorn
witness found one publication/11 assertions across13 revisions in1.083 seconds.
Core merge is verified; Buddy consumer acceptance remains pending. Twenty focused
tests pass including six real native publication/reopen cases in disposable Core
and APP databases, current 1.13 source observations and governs normalization,
selective second-publication aggregation, changed candidate/source, zero result,
and mounted route authentication/binding/unknown behavior. Initial test failures
exposed an invalid v0.1 fixture under profile1.13 and an accepted-edge hypothesis
outcome/rekey mismatch; fixed through the real producer's pure mapping contracts.
One earlier redundant sandboxed ASGI pytest process stalled; stopped its exact
PID after the same mounted tests passed in the isolated runner. No provider,
retained publication, corpus edit, migration or serving runtime change occurred.
