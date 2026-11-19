# CLEANUP: isolate historical Graph transport

Status: ACTIVE bounded assignment under the user's cleanup goal. This write
lease ends when the assigned PR merges or closes; it grants no successor work.
Base: `26132b18652ef80b0c311cdfc08a8f6b118ad5b3`. Serial, one PR, no unmerged parent.

Outcome: move the isolated launcher/HTTP transport into the lab tree, retain its
exact dependency and ownership guards, and stop shipping the unused HTTP server.
Current product Graph service/storage, UI and routes remain outside this lease.

Writes: move `scripts/native_graph_demo.py` and
`apps/live_control_server/native_graph_demo/server.py` to `evals/native_graph_demo/`;
adjust their repository-root/import bindings and `tests/test_native_graph_demo_http.py`;
add the lab README, link it from `evals/README.md`, and clarify historical status
in `HANDOFF-SURFACE-native-graph-demo.md`; this brief.

Prerequisites checked: no live exact launcher process; independent audit found
no overlapping launcher/test/handoff files in 99 open PRs. Existing hosted
authorization, Plan and Local World leases remain untouched.

Verify exact-source HTTP/launcher guards and retained production Graph imports,
fresh production copy/image exclusion and size difference, local documentation
links, repository hosted frontend verifier, and independent cumulative review.
No historical native launch, production deployment, provider call or dependency
upgrade is part of this relocation. #4014 retains that separate owner decision.
