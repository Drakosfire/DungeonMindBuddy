# DEMO-J3 PLAY-2 — persistent vNext PostgreSQL composition evidence

**Disposition:** IMPLEMENTED / REVIEW CYCLE 1 HOLD REPAIRED
**Buddy base:** `58c650e80eee0825c4d713999fcbbd3789856c33`
**DungeonMind runtime and migration pin:** `0f709d76fdc53bac9c9258d1751463ae2c76ca71`
**WorldKeeper runtime pin:** `49a8620f066ce7ef8972a699020c012f50af9158`

## Proven boundary

The accepted Buddy consumer composes with WorldKeeper and DungeonMind's native
PostgreSQL repository over a freshly migrated disposable database. The canonical
Pippa `works_at` brewery proposal prepares read-only, confirms one exact child,
persists matching head/event/receipt/result authority, survives service and
process reconstruction, and replays without another child. Competing parent CAS,
concurrent duplicate confirmation, missing evidence, V2 profile, changed claimed
meaning, stale preparation, and unsafe DSN behavior are covered at this boundary.
Prepared identity, producer meaning, and publication time tampering are rejected
by WorldKeeper's sealed-plan integrity guard before any authority mutation.
PostgreSQL URL query/fragment routing overrides are rejected before connection or
migration so the generated database path cannot be superseded by `dbname`.

## Exact evidence

The required positive run uses a clean detached DungeonMind migration checkout
at the exact runtime pin and the local development admin authority on port 54329.
It creates only `dmb_play2_test_<random>` and drops that exact database in
`finally`; credentials are not reported.

```text
prepare                  revisions/events/receipts/results = 1/1/0/0
confirm                  revisions/events/receipts/results = 2/2/1/1
fresh-process read-back  same child and graph-payload digest
replay                   revisions/events/receipts/results = 2/2/1/1
competing CAS            revisions/events/receipts/results = 2/2/1/1
duplicate confirmation   revisions/events/receipts/results = 2/2/1/1
```

```text
PLAY-2 PostgreSQL witness: 4 passed in 5.48s, 0 skipped
PLAY-1 + V6.2 regressions: 54 passed in 1.71s
scoped Ruff: pass
git diff --check: pass
full default suite: eight inherited collection errors, matching activation evidence
disposable database residue: none
```

PRIME Review Cycle 1 reviewed `b3eab88b27acc547e76998c7960cd9c06ad31e62`
and posted HOLD as review `5331382343`. This head repairs both findings: effective
DSN routing overrides now fail before I/O, and pre-commit prepared-value identity,
meaning, and publication metadata tampering fails closed with zero mutation.

## Explicitly unproved

This is not a production route, browser journey, source-ingestion witness,
bridge migration, V2→V3 transition, live Eldyrwild publication, or cutover.
The fixture evidence reference does not prove source-content persistence.
DEMO-J3 next-turn retrieval and human acceptance remain open. The token
`CON_READY_PLAY_2_PERSISTENT_VNEXT_POSTGRES_ACCEPTED` remains unauthorized
until independent exact-head review and merge.
