# RETRIEVAL: observe the actual Core connection

Status: ACTIVE. This serial evaluator slice starts from main
`91a9c81dbf648fdb928196a9f3b1ee9709a31ce1` on
`codex/negative-environment-review`. The explicit goal requires preserving
necessary source reads and qualifying capture environments. Existing open
retrieval and benchmark PRs were checked; none owns this evaluator boundary.

The write set is this brief, a focused negative-retrieval Core connection
observer, its capture, SQL-window and report integration, focused tests and the
evaluator README. The
observer must check the connection actually delivered by the known Core
PostgreSQL owner against the frozen local Core identity and a separately checked
non-writing login, including transaction read-only status. Record only
content-free counters and provenance; never retain credentials or place host
metadata in model input. Hooks must be removed even on failure. Unobserved
drivers, pre-existing aliases, pools, other processes, and late work stay
unknown; this slice cannot certify a complete journal or environment.

Exercise matching and incorrect identities, read-write transactions, owner
failure and hook cleanup at the connection boundary, then run a provider-free
check against the existing read-only shared Core with the single already-owned
App clone. No clone, production state, model call, schema change or full
database scan belongs to this slice. Review the exact cumulative diff and have
an independent exact-head review before merge. A successor can use the witness
to build stronger per-run environment evidence after this slice merges; its
scope and source parent must be re-anchored then.

Provider-free initial owner check on the existing clone reached the real
read-only Core transaction; case 413 failed because the check script expected
a tuple from the Core owner's dictionary row factory. Case 414 corrected that
assertion and observed one connection and one verified transaction using only
`SELECT 1`. Both workers closed. These checks used the earlier witness head;
the lifecycle fixes require a fresh exact-head check and review.
