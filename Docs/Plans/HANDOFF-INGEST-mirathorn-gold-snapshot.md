# INGEST: Preserve the historical Mirathorn Gold test contract

SETTLED. PR #2400 merged at
`0d3c5b41373c50181408622b8cd180f12d5b430d`. The fixture write lease is released.

The serial test slice started at base
`59e7621de4cb26784d843ab57f4f091ec5beed43`, branch
`codex/mirathorn-historical-gold-fixture` in the recorded-names-control checkout.
PR #2399 merged and released its fixture lease.

The former write lease covered this handoff, its predecessor
`HANDOFF-INGEST-worldbuilding-publication-fixtures.md`,
`tests/test_mirathorn_worldbuilding_query_gold_v1.py`, and the inert fixture
`tests/fixtures/mirathorn_gold_source_snapshot.json`.

The original Gold pins profile and contract bytes from commit
`236c7a75be3ea5b7a74be338b44e7957400aa267`. Freeze those twelve files as
hash-verified text data so tests exercise that historical contract in shallow
checkouts. The validator reads the text as fixture input. Preserve Gold bytes
and source quotations. Verify the full existing Gold suite and independently
compare the fixture to the pinned Git objects before delivery.
