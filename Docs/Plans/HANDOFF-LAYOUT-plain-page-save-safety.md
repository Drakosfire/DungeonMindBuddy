# Plain-page identity Save safety

Status: MERGED. PR #4243 merged as
`08d23da86a079121b7b31812e93db1857df17864` after independent source review cycle 1
PASS at `6da4b530aa2fdefc41ca281b4a3fb6e05d827eeb`. This implementation lease
has ended. The active contextual-layout goal authorized the serial Save-safety
slice from `/home/drakosfire/Downloads/Buddy-Contextual-Layout-Handoff.md`.
On November 20, 2026 Alan also explicitly authorized the bounded Save-forwarding
split in BuildSurfaceShell.tsx, preserving #3824's hosted-authorization work.
That frontend split is reserved for the successor; this PR does not edit it.

## Slice and ownership

Outcome: an ordinary old writer cannot silently erase an identity-only Page
presentation by sending null. Preserve existing explicit visual unwrap behavior
and sidecar-free Save behavior. Identity-aware writers retain the existing v1
all-block bindings; unsupported writers refuse before mutation.

Serial first slice, based on origin/main
`4715f169d28f2fc6cade2f883fba4730b67445e8`, branch
`codex/contextual-layout-save-safety`, checkout
`/home/drakosfire/Projects/.codex/bf5b/DungeonMindBuddy`.
No unmerged implementation dependency. Draft #3867 remains the preserved
contextual-placement benchmark, not evidence of ordinary routing acceptance.
The original assignment withheld merge and deployment authority. Alan's updated
goal subsequently granted merge authority; deployment remains unauthorized.

Exclusive expected write set: this handoff,
`src/application_state/content/page_presentation.py`, and
`tests/test_authored_page_database_cutover.py`. Current open-PR filename audit
checked 59 returned open PRs and found no overlap on the two implementation paths.
No changes to #3824-owned transport, frontend forwarding, schemas, lockfiles,
providers, runtime pins or real Worlds. Return for a split before expanding.

## Failure critique and proof

Before this implementation, omission refused an existing sidecar, but explicit null stripped it.
The wrapper-free frontend projection emits null, so v1 read compatibility does
not prove writer compatibility. Refusal must apply at both prepare and actual
commit, including a direct database-owner call; stale tokens cannot bypass it.
Do not normalize Markdown, invent visual rows, or allocate a migration.

Characterize sidecar-free omission/null and two identical identity-only fixtures
through actual authoring Save with fresh database connections. Verify Markdown,
block identities, presentation fingerprint and revision. Cover preserving Save,
lost acknowledgment/retry, stale snapshots, transaction rollback, explicit visual
unwrap, and the existing forward-only old-reader fence. A lower-layer candidate
check is diagnostic only, not persistence evidence.

Disposable PostgreSQL: task-owned container `buddy-layout-save-a0jv7t`, loopback
33111, synthetic fixture role, session template and per-test clones. No other
container, verifier, service, database or serving build is owned by this lane.
Evidence/scratch root: `/home/drakosfire/Projects/.codex/buddy-check.A0jV7T` on
Projects UUID `48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8`.

Validation: focused persistence tests, then exact-SHA saved-page-readers contract
in an isolated checkout with the locked owning Python environment; required
exact-SHA hosted frontend verifier and retained validation result. Inspect the
cumulative base-to-head diff before commit/push/PR. Independent exact-head review
and merge authority remain separate. Success here does not enable contextual
chat, enroll real pages, establish model quality or qualify a release.

## Remaining serial work

After storage safety: identity-retaining frontend Save and ordinary Plan chat,
then composed Plan and Build qualification; existing typed Graph references;
independent statblock creation proof; bounded adjacent-slot image move after its
owner gates. Keep real-model nomination separate from scripted apply/persistence
evidence, preserve frozen held-out cases, and retain the full active goal.

## Implementation checkpoint

The shared backend candidate guard now rejects explicit null only when the
current presentation consists entirely of ordinary block bindings. Existing
visual unwrap and unenrolled plain Save remain supported. Both prepare and
commit, including the direct transactional owner, consume this guard.

Before the fix, the five-case focused database diagnostic had four passes and
one failure: the identity-only explicit-null prepare did not refuse. After the
fix, all 54 owning Page Save tests passed in the freshly installed locked Python
3.13.12 environment. This includes six new cases covering sidecar-free writer
forms, enrolled writer refusals, identity-aware Save/retry/stale/rollback and the
existing old-reader schema fence. Ruff and diff whitespace checks pass.
These are working-tree diagnostics; exact-commit contract/verifier results must
be inspected separately before review. No frontend activation or real enrollment.
