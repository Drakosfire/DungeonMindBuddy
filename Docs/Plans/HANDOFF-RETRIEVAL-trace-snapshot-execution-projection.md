# Skip execution reads for reference-free trace snapshots

ACTIVE. Serial Buddy latency slice on merged #4428, 57777c1aaece74fd97841ecf2b206f54a2486254.
Use the existing isolated checkout and disposable PostgreSQL fixtures. Write set
is the context trace store, its existing PostgreSQL tests, and this handoff.
There are no schema or Core dependencies beyond the merged base.

A typed context snapshot with no historical source references needs no
execution projection. Keep the ordinary claim fence, snapshot model/trace
validation and persistence, and all execution reads for other validators
and historical references. The stored observations and provider behavior
must match exactly apart from elapsed times and generated identities.

Verify independent review and owner tests. Use the retained D02/WF01 wires
first, then the frozen 31-case cohort from b.d2UJuG if the pair passes.
Require at least 100 ms median paired trace savings on both stress cases,
no paired writer-ready regression, exact writer and Jev packets, and all
required citations reopening. Keep primary data and working conversation
untouched. Preserve the experiment evidence even if rejected.
