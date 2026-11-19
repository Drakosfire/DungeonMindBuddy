# BUILD: Page composer persistence prerequisite

Status: ACTIVE for investigation and bounded implementation after the mapping proof below.

Alan authorized “Build it” on 2026-11-15 after the proposal at
`56507b4cc47241be61a1d27fbd53a87e5d3a7421:Docs/Backlog/DESIGN-build-page-composer.md`.
Parent assigned the first mixed-content row or its smallest necessary persistence
prerequisite. This lane does not implement the later text layer or print slice.

Base: `e1163038c83651a1b4351800f9ce7ad4f3f15bcb` fetched current main. Branch:
`codex/build-composer-persistence-20261115`. Isolated Projects checkout:
`/home/drakosfire/Projects/.codex/build-composer.7jGA6u/source`.
Topology: serial implementation; #3683 is separate unmerged design, not code dependency.
Open PR path scan found no overlap in Page persistence; #2298 touches historical
frontend API tests only. No frontend API test or root policy edits in this lane.
No allocated server port, live database, provider call, or World mutation.

## Invariant and representation decision

The current Page write path commits Markdown only. Same-content commits and
immediate retries use the semantic content digest. Never change that digest's meaning.
Use typed Page-only presentation metadata bound atomically to an immutable Page
WorkRevision. Content stays in Markdown once. Bind layout blocks to exact UTF-8
spans within that revision, not to guessed stable offsets across revisions.
The only start prerequisite for persistence code is a proved mapping of the
first-slice supported prose/image/table/callout blocks through the existing editor
parser and saved Markdown. If that fails, stop with concrete read-only findings.

## Expected bounded write set

- This handoff.
- `src/application_state/content/page_presentation.py` (typed validated presentation).
- `src/application_state/content/pages.py`, `service.py` (Page atomic owner/no-op).
- `src/application_state/migrations/versions/20261115_0158_page_presentation.py`.
- `src/application_state/content/markdown_source_blocks.py` and
  `src/application_state/agent_conversation/authored_excerpt_blocks.py`: parent-approved
  pure parser extraction, preserving existing evidence handles and bytes.
- `apps/live_control_server/services/tiptap_markdown_write.py`,
  `workspace_document_registry.py` (prepare/commit/snapshot transport).
- Owning Page tests in `tests/test_authored_page_database_cutover.py`.

Any extra shared parser extraction or client/UI work requires scope amendment.

## Verification

Exact repeated commit is idempotent; unchanged Markdown with changed layout creates
one revision; stale basis or omitted layout on a composed page fails without loss.
Snapshot cold read returns exact presentation. Same semantic hash and historical
source/citation text remain unchanged. Test full rollback, wrong World ownership,
invalid/duplicate/spoofed spans, UTF-8, leading YAML, tables, and callouts. Use only
disposable database fixtures and the repo-owned saved-page contract. Report missing
coverage and never call backend persistence a completed composer UI. Open draft PR;
no merge or deployment authority.

## Mapping checkpoint

Independent read-only proof at the base parsed Unicode prose, standalone media image,
flat table and canonical callout with and without leading YAML. Per-whole-span
reconstruction equaled the full editor JSON, with no import diagnostics. The prefix
is excluded by UTF-8 length, not JavaScript character count. Other source constructs
are not claimed by that proof. New typed schema refuses raw HTML/code blocks and
arbitrary attributes. No UI is included in this prerequisite.

Disposable database: own `buddy-composer-7jga6u-pg` PostgreSQL 16 container,
127.0.0.1:32775, tmpfs database storage. Test fixtures own template and cloned DBs.
No changes to any existing container or database.
