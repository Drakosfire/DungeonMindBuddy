# World Plan presentation Save and load over HTTP

Status: MERGED in PR #4345 as `2e9f2bb7cd069f40ed7334b20a2fd21f113b4f56`.
Reviewed head `00fe2f84a8eac3d8170e938aef5503113a740ca6` passed seventy focused
HTTP/review checks and the disposable 0173/0174 old-reader and forward-recovery
witness. The named suite had 476 passes, two skips and the matching inherited
Build Image HTTP failure. The next serial slice is
[manual Plan composition](HANDOFF-PLAN-manual-composition.md).

The predecessor prepare/commit endpoint accepts presentation for authored Pages
and refuses it for Plans. The Content prerequisite owns atomic revision
storage and old-writer refusal. This slice carries that same checked
`PagePresentationV1` through existing authorized World Plan prepare, commit
and cold load. The interactive composer and nested ordinary agent requests
follow in separately reviewed serial slices.

## Current ownership and sequencing

Routine implementation, disposable verification and review are covered by the
user's lane authority. Open integration draft #3824 at
`76c31187f3e9badecbc403f2d9c943994c5f5f9c` overlaps the existing Save service.
Its active fixture lease is separate. Preserve every actual World authorization
and principal check when reconciling the two source diffs. The editor and its
welcome/rollout overlaps remain outside this slice.
The held #2104 route proposal remains separate. This slice owns only the
presentation commit callback at the existing Markdown route, so that a
hosted Plan without artwork still verifies the principal at the Content lock.

#4343 merged as `ce85237d83500b6dd0735b3404c08618a0cd7b1c` with application
revision 0173 and is integrated into this branch. After rechecking that
0174 was unreserved, this slice adds one forward-only reader fence after 0173.
Final fenced exact-head verification and independent review precede merge.
Production migrations, runtime deployment and serving selection are separately
governed.

Expected write set:

- `apps/live_control_server/services/tiptap_markdown_write.py`
- `apps/live_control_server/routes/live.py` for the locked presentation commit
  World callback only
- `apps/live_control_server/services/workspace_document_registry.py`
- `tests/application_state/test_authored_pages_postgres.py` for the existing
  shared Content contract and actual HTTP lifecycle checks
- `src/application_state/migrations/versions/20261121_0174_world_plan_presentation_reader_fence.py`
- This handoff and the merged Content predecessor handoff

## Invariant and verification

Scope an explicit presentation to the selected World, document and registry
revision. Prepare is read-only for presentation Save and binds the candidate
fingerprint to the exact Markdown, title, authorization scope and revision.
Commit performs the same check under the owning Content CAS and returns the
durable layout fingerprint. A lost-ack retry must reproduce the same receipt
identity. Old omission/null, a foreign owner, a changed layout, and a stale
token must leave content and stable identities intact. Cold GET returns
presentation paired with its exact committed Markdown.

Use the existing owned disposable PostgreSQL cluster and locked Python runtime.
Verify the real HTTP endpoints for local operator and hosted World principal
scopes, including layout-only revision, prose Save, rejection, exact retry and
cold read. Keep existing Plan, Runbook and authored Page paths compatible.
Retain before/after schema-fence and rollback evidence, final exact local
contract verification, and independent review. This PR supplies the durable
API prerequisite for the next editor/browser witness.
