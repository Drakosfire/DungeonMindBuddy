# PERF · Claim and capture a fresh Build draft atomically

Active under the hosted Build Send-to-Jev goal. Serial successor to #4170.
Base 609205a4e6b0baf6ff6db558cfd86a4f051000ca, branch codex/jev-build-claim-capture.
This lane owns agent_turn_service.py, agent_context_trace_collector.py, the
application-state conversation service and context-trace store, their owning
tests and this handoff. All verification uses disposable local databases.

The warm continued reference measured 446 ms claiming, 110 ms starting
the trace and 795 ms capturing the working draft. The candidate shares the
claim transaction with the trace and existing typed draft append for fresh
ordinary Build requests without an authored reference capture. Preserve the
trace origin sequence and the exact same record order, saved basis, admission
proof and attempt fence. Reviewed actions and previously captured requests
retain their established sequence. Authorization and sending still require
their own acknowledged commits, so a provider failure cannot undo capture.

Verify ordinary route event order and exact wire, rollback of claim and trace
when capture fails, concurrency and retry fences, retained draft reopening,
unchanged primary and source state, independent exact-head review, and
hosted Send-to-Jev timing. Do not activate an unqualified candidate.
