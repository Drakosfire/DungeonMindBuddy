# PERF: reuse admission transaction connections for schema checks

ACTIVE serial slice on 2afb8ff5b. Predecessor #4161 is merged and deployed.
Authorized in the hosted Send-to-Jev lane. Owns agent_conversation/service.py,
its existing claim fence test, and this handoff. No unmerged dependency.
Scope is accept_turn and claim_turn only. Verify the live migration head on
the connection used by each transaction, as existing content and catalog
owners do. Preserve transaction separation, locks, mutation order, commit
semantics, idempotency and expiration rules. No migration or primary writes.
Use local isolated claim/retry and ordinary Build contracts, independent review,
and matched hosted timings. The earlier 11.75 ms median connection probe implies
a modest expected saving. The rest of the measured 1.84 s remains open.
