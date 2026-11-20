# Public legacy projection retirement

Status: ACTIVE. MIND owns this serial slice on Buddy main
9cddc3c38d7016f6cda093889a07566d54e45b5f after PR #4242.
The operator has authorized implementation, review and merge.

Retire both raw projection POSTs with typed 410 after current GM, model and
query checks. Keep managed native projection and published native Recap.
Retire the classic branches of Graph Lens and Recap and clear stale display.
Campaign statblock creation loses automatic classic head lookup. Preserve
explicit pins, opt-in standalone creation, existing V1 mechanics and native
V2 creation. Keep historical review receipt, recovery and exact revision
identity. Display legacy graph visualization as unavailable. Remove retry
controls for retired graph reads. The separate historical exact-run preview
and shared service implementation remain available for their owning callers.

## Write scope

Hubble owns only apps/live_control_server/routes/world_graph_projection.py
and tests/test_agent_graph_auth.py. MIND owns the four production callers
(useWorldGraphLensProjection.ts, RecapGraphModule.tsx,
StatblockWorkbenchModule.tsx and graphReviewLiveReviewState.ts), the committed
projection panel, owning tests and the two handoffs. Rebrief before touching
additional paths. Open PR #3824 touches the route, auth test and Recap module.
MIND allocates only retirement regions on current main. Keep that proposal intact.

Verify mounted 401/403/422/410 with no legacy projection work for either
endpoint. Verify managed native success, stale response rejection, preserved
statblock creation and mechanics, historical receipt recovery and zero old
requests from all four UI callers. Review the cumulative diff, run backend
owning and authorization checks and the frontend verifier on the final source.
Compare full UI failures against the current base. Preserve existing failed
evidence and obtain independent review before merge.

The full cutover still requires deployment, rollback rehearsal and serving
acceptance. The frozen retrieval baseline is retained.
