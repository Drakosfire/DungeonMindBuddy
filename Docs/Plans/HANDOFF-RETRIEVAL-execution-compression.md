# RETRIEVAL: compress new execution records with LZ4

ACTIVE under the Buddy Send-to-writer latency goal. Root owns this serial
slice from `774aa06344eb0a9411855eccdc7e33e7fead89c4`, branch
`codex/plan-execution-lz4`, isolated Projects checkout
`buddy-binary-plan-ack`. No unmerged behavioral dependency. Expected writes
are this handoff and the new application-state compression migration.

PostgreSQL already compresses wide execution JSONB. Select LZ4 for this
column only. Existing tuples keep their stored compression. Upgrade and
downgrade change the codec for future writes, without a historical rewrite.
The supported server binary must continue to read both codecs. The pinned
PostgreSQL 16 and CI PostgreSQL 16 Alpine images have LZ4 enabled. Runtime
SQL, exact byte checks, checkpoint transactions and recovery stay with
their existing owners.

Two disposable provider-free D02 trials using the same Jev tape met the
screening threshold of ten percent at write/ACK and half a second at
writer-ready. Qualify fresh migration and populated upgrade/downgrade,
prove both codecs reopen byte-identically, exercise storage integrity
tests, and run the frozen 31-case cohort with exact writer/citation parity.
Use the existing Projects evidence in `core-scope-pilot.Ikt8NV`.
Independent exact-head review and local verification precede merge.
No primary migration or deployment is authorized by this handoff.

PR #4264 moved main and landed the preceding migration. This slice is
now revision `20261121_0173`. Requalify the integrated migration and
check retained Jev wire pins before reusing route timing or parity.
