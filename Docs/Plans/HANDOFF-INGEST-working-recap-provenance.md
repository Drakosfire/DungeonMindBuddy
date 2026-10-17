# INGEST: clarify working recap provenance

**Status:** ACTIVE — PRIME authorized this bounded UX slice on 2026-10-17.
**Base:** Current Buddy main `f35a152f4fc11b2f108b00c84313f5b275e5b130` has been merged into this feature branch. The cumulative main-to-head diff remains limited to this handoff and the two leased UI files.
**Branch:** `codex/ingest-working-recap-provenance`.
**Checkout:** Reuse the assigned `996b` workspace for focused verification only. Its existing branch is 36 commits behind current main and has unrelated dirty/untracked Ingest work; do not switch branches, reset, stash, or edit any path outside this lease. The two leased source/test files match current main byte-for-byte at the pinned base. Publish the reviewed cumulative change on this named branch.
**Topology:** Serial; one small Ingest UI PR. PRIME retains review and merge authority. No new worktree, environment, server, provider call, corpus or database write.

## Mission

The Session 10 Ingest reader currently presents a notice saying “Working projection — Local and uncommitted. Canonical recap and World memory are unchanged.” while the projection reader itself is labeled “Published recap.” Preserve the source’s published provenance while making the visible document label describe the local working projection being shown.

The user’s normal view remains the enriched, node-bearing recap. Do not expose raw Markdown, change extraction, create a second projection, change the canonical recap, or alter how authoring proposals are staged.

## Evidence

- Rendered on 5202 at `/ingest?world=elderwyld&campaign=longmont-c2&session=session-10&view=recap`: the same surface visibly contains the Working projection notice and a Published recap reader.
- Current `main@23066e13e847c74dcefdbb80b24d548b883b31c5` mounts `PublishedRecapLocalAuthoring` from `WorldGraphRecapProjection`; the reader’s `documentLabel` is “Published recap.”
- Current screen is read-only evidence. Do not click authoring, stage/commit proposals, process a recap, reload the user’s tab, or change 5202 state.

## Exact write lease

- `Docs/Plans/HANDOFF-INGEST-working-recap-provenance.md` — this bounded contract and truthful implementation/verification evidence.
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.tsx` — change the reader label to describe its working projection and explicitly identify the published recap as its source. Preserve source identity/provenance and the existing “local and uncommitted; canonical recap and World memory unchanged” notice.
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.test.tsx` — regress both labels, their source/working relationship, and unchanged authoring behavior.

No other source, tests, CSS, routes, API, server, schemas, extraction prompt/profile, candidate, corpus, source artifact, World Graph, database, build output served on 5202, or runtime file is leased. Stop if implementation requires any other path or exposes an ownership collision.

## Acceptance and verification

- The working document is named “Working recap” (or an equally explicit label chosen in implementation); the source is identified as the published recap.
- The unchanged notice continues to communicate that the current projection is local and uncommitted and that the canonical recap and World memory are unchanged.
- Existing node pills, selected source identity, draft staging, and author-node interactions remain unchanged.
- Focused `PublishedRecapLocalAuthoring.test.tsx`: 12/12 passed; UI `npm run typecheck`: passed; production build: passed with the existing large-chunk warning; `git diff --check`: passed. The build was initially emitted to `/tmp/dmb-ingest-working-recap-build` before the cache-location restriction was communicated. All nine generated files were moved into `.pytest_cache/dmb-ingest-working-recap-build`; relative-path SHA-256 manifests match exactly and the original `/tmp` directory is gone. This records the original build location truthfully and does not imply it was built in the cache.
- Perform read-only rendered checks at desktop and narrow widths through an existing surface. Do not use the user’s 5202 tab for interactions or writes; do not change its served assets. If the current environment cannot provide both rendered widths safely, report the missing evidence rather than claiming acceptance.
- Review the exact cumulative base-to-head diff and present one PR to PRIME. Do not merge it.

## Implementation evidence

- The reader now says “Working recap”; the adjacent notice explicitly says “Source: Published recap.” The local/uncommitted and canonical-state disclaimer remains intact.
- Added a regression assertion for the working label, source label, and unchanged notice. Focused suite passes 12/12 tests (including the prior 11); `npm run typecheck` passes; `npm run build -- --outDir /tmp/dmb-ingest-working-recap-build` passes with the existing large-chunk warning; `git diff --check` passes.
- The exact cumulative diff against the newly fetched `main@f35a152f4fc11b2f108b00c84313f5b275e5b130` contains only this handoff and the two leased UI files; main has three additional commits since the pinned starting base and no changed paths in this effective diff.
- Current-head rendered desktop and narrow checks are **not verified** and are deferred to the next already-authorized main UI rollout on 5202. DOGFOOD owns that check: verify the “Working recap” label and “Source: Published recap” at desktop and narrow widths, with the node-bearing source projection still visible. Do not mark visual acceptance passed until those states are actually observed. No server change or preview is authorized solely for a screenshot.

## Settlement

PRIME accepts independent code review and owning tests before render. PRIME will inspect the exact PR head and run the owning test file before merge. Rendered desktop/narrow acceptance remains an explicit DOGFOOD gate at the next already-authorized main UI rollout; no visual PASS is claimed here. Keep this handoff ACTIVE until the review/merge and later rollout check are recorded.
