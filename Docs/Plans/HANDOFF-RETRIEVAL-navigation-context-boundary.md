# RETRIEVAL: source-navigation prompt boundary

Status: ACTIVE under the user's over-retrieval goal. Root owns this serial
prerequisite to draft #4973; serving base
`2c42e181fac064454f2b998e2e2ef771a781d125`, branch
`codex/retrieval-navigation-context-boundary`. The producer must not resume its
model replay until this fix is reviewed and deployed.

Development replay case 562 was stopped before its fifth provider request. An
independent exact-wire audit found host acquisition counts embedded in an
examined-source description. That request was not sent. Earlier four audited
requests were sent; the same owned clone and partial evidence remain. This is
an existing shared source-navigation projection, not a reason to weaken the
model prompt boundary.

Produce a semantic search-attempt outcome without counts or host identity in
model-visible context. Preserve useful task context, the distinction between a
completed and unresolved search, and an indication when some sources were
unavailable. Keep all actual counts, source records, access fences, and
completeness checks with their existing host owners. Historical captured
requests must remain readable; no regex scrubbing or hidden prompt channel.

Write lease: `apps/live_control_server/services/corpus_source_navigation.py`,
focused existing source-navigation tests and this handoff. Validate at the
actual serialized decision boundary: complete, partially unavailable and
unresolved search cases; no count/IDs in final wire; no altered acquisition
record or unsafe claim of completeness; historical proof reconstruction;
principal and one-shot safeguards where applicable. Use mock providers for
focused checks, then independent exact-head review. Merge/deploy through
Actions only with current serving and rollback pins, and smoke the signed-in
app. Rebase and requalify #4973 on the deployed fix; its live benchmark remains
separate and may resume only with a fresh prompt audit. One owned App clone,
serial workers and shared read-only Core remain in force.
