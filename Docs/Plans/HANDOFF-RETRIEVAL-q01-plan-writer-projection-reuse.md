# RETRIEVAL · Reuse the Plan prose evidence projection

Active under the Q01 latency goal. Serial after #4250, merged as
`574afc331b1076aaacbaa83d9d525ac2f078cc86`. Branch
`codex/q01-plan-writer-projection-reuse`. Scope covers the writer verifier
and this brief.

The Plan prose verifier already builds the exact admitted host evidence to
compare the rendered user message. Reuse that same local projection for
the later output and selector checks. Keep prospective binding validation,
the strict wire comparison, ambiguous-carrier rejection, and the other
writer routes intact.

Verify locally through the owning ordinary Plan and writer contracts.
Compare ordinary Q01 replays with tracing off and identical Jev request,
writer bytes, evidence frame, citations and Core data. Keep the offline
20-pair projection result distinct from ordinary request timing.
