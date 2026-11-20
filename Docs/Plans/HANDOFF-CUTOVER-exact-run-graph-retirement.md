# Retire exact-run legacy recap graph visualization

Active serial slice. MIND owns delivery on c8286fe3 (merged #4246).
The user authorized implementation, review and merge.

Return typed 410 from the exact-run recap projection GET after existing
query and hosted authorization gates. Preserve saved source and candidate
APIs, receipt recovery and run identity. Ingestion and Graph Review must
stop dispatching legacy graph projection. Restored admitted URLs should
show retirement without substituting another graph or enabling promotion.

Hubble owns graph_preview.py, test_graph_preview_routes.py and
test_hosted_native_graph_access.py, only the retirement handler and its
witnesses. MIND owns IngestionModule.tsx, GraphReviewWorkbenchModule.tsx,
their existing owning tests, and the two cutover handoffs. Open overlaps
3824, 3808, 2405, 2090, 2087, 2082, 2081 and 1235 stay separate. This slice
owns the retirement regions on current main.

Verify mounted query and auth precedence, typed 410 and zero projection
or source IO. Verify saved source, candidate selection, no publication
fallback, and restored-URL behavior. Run owning/auth and frontend checks
and compare the full UI suite with the exact base. Review before merge.

The next Core export audit must still examine retained readers and
internal callers. Elderwyld deployment, rehearsed rollback and serving
acceptance remain open.
