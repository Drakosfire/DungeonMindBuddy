# RETRIEVAL · Attribute the writer admission append

Active under the Q01 latency goal. Serial successor to merged #4247
(`fa8593e2843153bcc988bc137c8d4f1c5aef44bc`).
Own the claim fence's writer-append timing and the ordinary Plan contract
assertion. Keep the comparison study running on its separate pinned checkout.

The Q01 pilot placed 2.20 s in execution appends, including one 834 ms
invocation near writer-ready. Split the existing writer append into Plan
session finish and writer admission persistence when detailed tracing is
selected. Preserve APP ownership, locks, storage semantics and request bytes.
Verify both markers in ordinary Plan, nesting under execution append, and
the existing writer receipt and no-network contract. Further database
decomposition and any removal of duplicated work depend on those findings.
