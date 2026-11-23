# ONBOARD: admit exact table hard breaks in Build captures

Status: ACTIVE. The Sizzek onboarding goal authorizes implementation, Bugbot
review, merge and deployment. This serial implementation slice uses branch
`codex/onboard-table-hardbreak`, based on `origin/main@f438e9c21`, in the
build-status-baseline checkout. Production serving integration #4557 owns its
separate deployment; this slice must follow its settled serving head.

Winter Wonderland's Build capture uses `<br>` for editor hard breaks in table
cells. The server rejects this exact capture, and the hosted resolver masks the
validation error as a 403. The fix recognizes only that exact encoding inside
protected tables and retains exact text, marks, geometry and other HTML denial.
Write lease: this handoff, `protected_boundary_blocks.py`, and its focused
`test_build_prose_catalog.py` tests. No private source, guest content, schema,
authorization or runtime configuration changes. Verify valid capture and
altered-content/HTML rejection at the server boundary, review the cumulative
diff and obtain independent Bugbot review. Release adoption follows the active
serving work and its checks; inherited failures remain explicitly documented.
