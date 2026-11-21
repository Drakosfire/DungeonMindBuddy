# World Plan presentation Save and load over HTTP

Status: ACTIVE for implementation and disposable verification on
`codex/plan-presentation-http` in the existing isolated Plan lane. Serial base:
`c68d9a2417b7cae8798f80da17c747c6dfe3e6c7` (#4344).

The current prepare/commit endpoint accepts presentation for authored Pages
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

#4343 reserves application reader-fence predecessor 0173. Implementation and
disposable testing can proceed now. Allocate this slice's single forward-only
reader fence only after #4343 lands, against the actual then-current migration
head. A final fenced exact-head verification and independent review precede
merge. Production migrations, runtime deployment and serving selection are
separately governed.

Expected write set:

- `apps/live_control_server/services/tiptap_markdown_write.py`
- `apps/live_control_server/services/workspace_document_registry.py`
- `tests/application_state/test_authored_pages_postgres.py` for the existing
  shared Content contract and actual HTTP lifecycle checks
- The single successor migration after its predecessor gate
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
