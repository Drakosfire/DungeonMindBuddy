# INGEST: read the exact unpublished candidate in recap prose

Status: BLOCKED — steward design; no implementation lease until the final
source-only read scope critique is resolved. ROOT owns design and implementation.
Base: origin/main@15aa918eb91071b469ea7f733cce6d2c6a3262e6.
Branch: codex/ingest-exact-candidate-reader. Reuse buddy-context-loop checkout
and established dependencies. Topology: parallel-independent of DOGFOOD's
source-snapshot correction lane: disjoint paths, no unmerged behavioral dependency.
ARCHITECTURE independently critiques/reviews; PRIME merges and adopts on5202.
No new worktree, environment, source export or task directory under /tmp.

## Bounded read contract

Add authenticated GET /api/live/graph-preview/extraction-runs/{run_id}/candidate-projection
with one required managed_world_id query selector, rejecting unknown/duplicate
selectors. Response schema dmb_exact_run_candidate_projection_v1 is a bounded
read presentation contract: exact run revision/status/profile, source artifact/
revision/raw SHA, candidate/span SHA, registered managed/native source binding,
explicit trustBoundary=unpublished_candidate, raw sourceMarkdown, ephemeral
projectedMarkdown, coordinate segments, typed candidate nodes/edges/evidence,
local reader node views/spans, diagnostics and honest coverage. It is NOT a
WorldGraphProjection and carries no fabricated admitted snapshot/head/authority.

Initial scope is recap_category_v1@1.0, candidate preview v0.1, sealed REVIEWABLE
or PROMOTED runs only. A promoted candidate is still its frozen extraction view;
admitted-current World browsing remains separately labeled. DRAFT/failed/partial,
unsupported profile/preview and missing/malformed/changed evidence fail explicitly,
never fall back to session latest, gold, native memory or another source.

Use direct get_extraction_run and assert_run_reviewable_evidence plus confined,
non-symlink captured component reads, exact raw-byte hashes and pure typed preview/
source-span validation. Hash the bytes actually parsed. Recheck run and registered
binding identity after capture. PROHIBIT resolve_promotable_ingest_run and any
transitive promotion/read convenience wrapper: they can write source seals.
No source admission, registry mutation, preview materialization/cache, source
repair, native graph/object query, provider or persistence in this GET.

Registered SourceArtifact native World must match the verified existing managed
binding; campaign/session and any present frozen context must agree. A legacy
run with absent frozen World context may be read ONLY with explicit source-only
binding status if canonical source World is verified; never fabricate or persist
frozen run scope. Contradictory/missing canonical World blocks. This grants no
correction/publication authority or historical backfill.

## Prose, coordinates and local identity

Namespace every view key by run/candidate digest/raw candidate ID, preserving raw
ID separately. Even raw loc_3 is candidate-local; no native lookup/delegation.
Use exact case-sensitive labels only inside each node's verified evidence spans,
then existing LocatedMentionBinding/CommonMark protection. No fuzzy aliases,
prefixes, pronouns or global label substitution. Ambiguous/overlapping owners
remain plain with diagnostics. All unmatched nodes remain inspectable in a local
list. Local edges can navigate only the returned map; missing endpoints are
explicit unresolved references. Existing/forged dmb-node links outside that map
must cause zero native requests or authoring actions.

Raw source/digests stay unchanged in Advanced. Display removes only a recognized
leading dmb_recap_normalized_v1 envelope; supported duplicated flattened envelope
is hidden ONLY when it exactly equals whitespace-flattened verified outer header
plus matching heading. Return source-to-display coordinate segments. Unknown or
changed prefixes/suffixes remain visible/labeled; no story-text regex deletion.
Mentions/highlights must map from original source coordinates correctly after
cuts, including Unicode/CRLF. Existing code/link/image protection stays intact;
source formatting limits are diagnostics, not invented links. Inspector labels
Extracted description, preserves full multiline text behind expansion and never
summarizes or claims canonical biography/semantic approval.

GraphProjectionReader is read-only with a LOCAL inspector callback, guarded map
lookup and authoring disabled. Never use useCompleteWorldObject/native popovers
for these candidates. Preserve input, Process failures/source conflict behavior,
exact route restoration, historical memory access and selection/unmount fencing.

## Exact proposed write set (12 paths; not active yet)

- This handoff
- apps/live_control_server/models/exact_run_candidate_projection.py
- apps/live_control_server/services/exact_run_candidate_projection.py
- apps/live_control_server/routes/graph_preview.py (narrow authenticated GET only)
- tests/test_exact_run_candidate_projection.py
- apps/live-control-ui/src/api/exactRunCandidateProjectionApi.ts
- apps/live-control-ui/src/api/exactRunCandidateProjectionApi.test.ts
- apps/live-control-ui/src/api/liveApi.ts (exact read auth classifier only)
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewCandidateRecapProjection.tsx
- apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewCandidateRecapProjection.test.tsx
- apps/live-control-ui/src/modules/IngestionModule.tsx
- apps/live-control-ui/src/modules/IngestionModule.test.tsx

Existing registry/source/basis/APP-STATE/mention engine/reader/models-types remain
read-only. DOGFOOD's13paths retain their exclusive lease. Any missing owning seam,
new public contract or path requires steward split/rebrief before edits.

## Required proof and delivery

Actual registered synthetic production run in disposable PostgreSQL54329 with
candidate != admitted graph: held/new candidates render and inspect locally.
All source/candidate/span tamper/World/campaign/session mismatches block; native
ID collision, Lysandro/Lysandra/duplicate labels, Markdown/code/link/image/Unicode
and coordinate tests prove no guessed links. Canonical source URI OUTSIDE ingest
roots is a write trap: instrument filesystem mkdir/write/replace and DB mutation
methods, prove zero domain mutation/native/provider calls and no promote_seals.
Real bearer/session/CSRF/loopback auth; existing local-session bootstrap POST is
auth, not domain mutation. Mounted Process success→candidate reader, source switch/
unmount/late result, exact raw Advanced content and separate historical view.

PRIME owns shared fixture container lifecycle; DOGFOOD and ROOT use independent
unique test databases and distinct .pytest_cache outputs. Do not remove fixture
until every consumer completes. Never retained54330/54331 or real data mutation.
Owning pytest/frontend suites, typecheck/build and cumulative diff inspection;
commit/push/open one PR, independent exact-head review, then guarded PRIME merge
and scoped5202/API delivery preserving drafts/source/graph. No paid experiment
or publication is required. This read model does not establish full recall,
semantic acceptance, NPC continuity or media enrichment.
