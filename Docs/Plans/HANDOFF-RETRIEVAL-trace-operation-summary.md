# RETRIEVAL · Count calls in the benchmark waterfall

Status ACTIVE. Serial report-only slice after #4271, main e95529af1.
Branch codex/benchmark-trace-operation-summary in the isolated trace checkout.
Write set is the report renderer, its existing workflow test, lab guide and
this handoff. No capture, runtime or provider changes.

Report observed operation counts, inclusive duration and single-operation
exclusive wall time. Retain shared overlaps in the waterfall. Run the local
workflow tests and verify that retained Q01 has identical total attribution
and timeline accounting. Receive independent review before merging.
