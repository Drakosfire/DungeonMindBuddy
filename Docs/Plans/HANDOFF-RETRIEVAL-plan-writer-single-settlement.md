# Settle the Plan execution at writer authorization

ACTIVE. Authorized by the Buddy latency goal. Serial on merged #4426,
f1a912f88325104131a728ae401e64d966cf1f34. Reuse the settled isolated
checkout on codex/plan-writer-single-settlement. No Core or schema change.
Use retained provider wires and disposable PostgreSQL clones on 32768.

Write set covers the Plan session storage owner, the writer dispatch boundary,
the existing SQL repository and the affected Plan and Rules owner tests.
Authorize only the active read-only Plan writer via existing admission.
Commit the Rules binding, final writer event, and retirement of its ordered
checkpoint in one transaction. Preserve every preceding read checkpoint.
Before acknowledgement, verify exact SQL bytes and locked root/provenance/
Rules state. The standalone non-dispatch session finish still settles history.

Pinned control is the merged #4426 tree with the 31-case replay at b.91qYrj.
The detailed two-case control is b.kMQeIm. Verify stale/expired refusal,
rollback, independent cold read, and no duplicate dispatch after commit
acknowledgement failure. Compare D02 and WF01 on frozen transport and require
exact writer bytes, identical Jev requests and event order, exact citation
reopening, and at least 200 ms median reduction of the combined frontier
spans on each case. If adoption passes, verify all 31 and obtain independent
exact-head review. Leave primary data and the working conversation untouched.
