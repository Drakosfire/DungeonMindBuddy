# HANDOFF — OPT01 resident verified world revision runtime

Branch: `opt/opt01-resident-verified-world-revision`

## Mission

Implement process-local verified resident revision loading, coalescing, lifecycle,
scrub, clear, and request-scoped I/O counters in
`src/graph_memory/kernel/world_read_runtime.py`, with lifecycle tests in
`tests/test_graph_kernel_world_read_runtime.py`.

Full contract: see parent agent briefing / commit plan for OPT01. Parent may
paste the complete handoff body here.

## Status

- `world_read_runtime.py` — implemented
- `test_graph_kernel_world_read_runtime.py` — E2/E3/E5/E6 lifecycle proofs
- Service wiring (`world_projection.py`, projection cache) — **out of scope** for this handoff
