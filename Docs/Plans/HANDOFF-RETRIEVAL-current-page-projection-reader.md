# RETRIEVAL: read the exact current-page projection

Status: ACTIVE under the user's over-retrieval objective. Serial reader bridge
between deployed #4892 (`9a21c8684e44a601ea76943d887884d2a59a2a32`) and the
direct-page producer. Branch `codex/current-page-projection-reader`, checkout
`retrieval-source-window`. The user owns this lane. The producer's in-progress
patch is preserved at `/tmp/buddy-current-page-direct-producer-wip.patch` and
its pinned brief is on `codex/current-page-direct-producer`; neither is active
while this bridge is delivered. #4884's current diff was checked for overlap.

The future current-page-only scope must project a one-page source offer without
implying a World-wide catalog. Add deterministic host and writer descriptions
for that already recognized future scope; preserve all existing scope bytes.
This reader must not emit the future scope or acquire a page. Existing fail-closed
recovery guards remain in place. Future completed-record reconstruction and
actual direct acquisition remain producer qualification gates.

Write lease: this handoff,
`src/application_state/agent_conversation/build_pending_app_coverage.py`,
`native_build_work_view.py`, and new focused test file
`tests/test_build_current_page_projection_reader.py`. Verify historical scope
projection, exact current-only scope and writer description, absence limitations,
wrong/multiple page rejection where the reader can establish it, and unchanged
producer decision emission. Review the exact cumulative diff, require independent
exact-head approval and Actions release, then re-anchor before the producer.
