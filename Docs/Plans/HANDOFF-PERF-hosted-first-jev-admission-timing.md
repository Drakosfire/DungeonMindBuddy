# PERF: attribute first Jev admission work

ACTIVE serial follow-up to merged and deployed #4148. Base 73f2efd3c.
Authorized under the hosted Send-to-Jev performance goal. Owns the Build
harness, context trace collector and execution service timing call sites.
No unmerged dependency. The native extension and publication lanes retain
their own files. Keep the current hosted configuration and primary data intact.

On the 8.30-second continued sample, the runtime-admission and authorization
intervals cover 5.33 seconds after removing overlap. On a second continued
sample they cover 6.46 seconds. The existing endpoint scopes are preserved.
Use bounded fixed names and the existing first-transport marker to split
driver creation, trace start and append, prompt evidence storage, and the
durable authorize or sending append. No prompt fields, transactions, ordering,
or authorization decisions change. Execution append and trace append cumulative
spans stay available. Do not add nested durations when reporting elapsed time.

Verify locally with the ordinary Build and context trace tests and the owning
query-and-answer contract in disposable state. Independently review and ship
the exact qualified delta. Compare hosted span unions on the same saved page.
Database connection, locks, SQL and commit still need attribution if the
durable operations dominate these new spans.
