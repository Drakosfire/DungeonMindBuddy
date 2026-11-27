# RETRIEVAL: carry Build discussion quality to serving

Status: ACTIVE. The user authorized reviewed merges and production deployment.
Serial successor to merged main PR #4941, merge
`80cf2da25118d06a554cc8202fe99c35066ce465`. Base the serving port on the healthy
production revision `9ec881f7e3bc091a2ea9d2a4815ab0b71fd6718d`, image
`sha256:987cee9a9ddca070726499f65e80c9a5c5eada1a6aa72fd516e6caac921c38a1`;
branch `codex/build-discussion-effort-serving`, base branch
`codex/coverage-capability-serving-base`. Recheck production and base before
publication and cutover. If either moves, rebase and requalify the port.

Outcome and lease: port the exact main selector into
`apps/live_control_server/services/plan_jev_writer.py`, preserving this serving
lineage's existing none/low/medium defaults, plus its focused tests in
`tests/test_plan_jev_response_assembly.py` and this handoff. Do not carry unrelated
main-line changes, change product prompts, retrieval, citations, schemas or data.
The old #3290 draft touches unrelated Plan compaction within the writer file and
is not an active pinned lease or behavioral dependency.

Evidence inherited from #4941 is recorded in its handoff and local synthetic
workstream cases 382–397: a promoted creative regression failed on low effort and
passed the temporary medium candidate; a source-required actual turn passed with
matching citation; two generic prompt-only variants failed. In one matched local
pair, low/medium request cycles were 3.65/4.10 s. These are small samples, not a
production latency guarantee or full acquisition qualification. The two unrelated
main-base assembly failures remain documented in #4941 and were not fixed here.

Validate exact selector parity to merged main, actual serving writer-to-TextRequest
selection and exclusions using focused tests, independent cumulative review, and
required short checks. Then publish through GitHub Actions using the current
serving parent/rollback pins and established release mode/document digest, deploy
through Actions under standing user approval, verify staged/live pins and public
checks, and run a signed-in synthetic creative smoke plus a source-required
control. Preserve the user's current workspace. The remaining H5 context and
related controls are not consumed by this port; overall goal completion remains
separate from this release.

Working-tree diagnostics: 14 focused serving writer-to-TextRequest and exclusion
cases passed. The selector and both test-function ASTs match merged main. An
actual pending-Build port check and exact-head review remain outstanding.
