# PERF · Attribute the first Build sending transaction

Active under the hosted Build Send-to-Jev goal. Serial successor to #4174.
Base b69e7d712b50251f0a07d1ecf6aa827451df5cba. This isolated lane owns the
Build runtime service, conversation service, their SDK boundary test and this brief.

The hosted acknowledgement took 1.82 seconds while retained codec replay
took 127 ms median. Add non-overlapping timestamps at the existing schema,
transaction open, locked read, claim clock, prospective validation, update
and readback, and commit/close boundaries. Locked read includes SQL, row
transfer, decoding and any PostgreSQL row contention. A measured locked read
is not, by itself, proof of a database lock wait.

Use the existing trace and unchanged durable owner. Verify that every
successful timing stage closes before exact SDK transport enters, and run
the local conversation contract and independent review. No primary or schema
edits. Measure on hosted ready-state Build before choosing a transaction fix.
