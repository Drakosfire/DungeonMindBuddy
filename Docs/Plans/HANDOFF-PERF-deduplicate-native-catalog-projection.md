# PERF: deduplicate native catalog assertion projection

ACTIVE serial slice on af6e07872. Predecessor #4158 is merged and deployed.
Authorized under the hosted Send-to-Jev goal. Owns native_graph_reads.py,
test_native_plan_assertions.py, and this handoff. No unmerged dependency.
The warm 6.25-second Graph query included 2.89 seconds of match catalog work.
This patch converts each immutable assertion ID to the wire contract once
per catalog and preserves all witnessing entities, scoped labels, digests,
discovery hops, and order. No query or source-policy changes. Verify the exact
existing catalog contracts and measure hosted impact before claiming speedup.
