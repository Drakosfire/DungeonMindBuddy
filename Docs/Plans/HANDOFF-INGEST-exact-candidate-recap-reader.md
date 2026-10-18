# INGEST: read the exact unpublished candidate in recap prose

Status: SETTLED — merged as PR #1401 at239011a4ebe4aa478d38b23da8760366bc88f972
after ARCHITECTURE Cycle2 PASS on9717a5232e06eaffe1bb8f285ce3c38053d20df7.
Scoped API/UI delivery is verified; this original write lease is closed.
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
narrativeMarkdown, projectedMarkdown, coordinate segments into narrativeMarkdown before navigation-link insertion, typed candidate nodes/edges/evidence,
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

## Exclusive implementation write set (14 paths)

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
- apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.tsx
- apps/live-control-ui/src/planSurface/graphProjectionReader/GraphProjectionReader.test.tsx

Existing registry/source/basis/APP-STATE/mention engine/models-types remain
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

## Activation and exact verification commands

Steward design pinned first at a88b5a128a507d9e074da10b35f1533493063b23.
Final critique permits source_only ONLY as prominent read metadata; malformed
or conflicting frozen context cannot downgrade to it. No correction/disposition/
publication control may consume that status. Use existing source/artifact/run
SELECT + exact captured component reads; instrument transitive mutations in tests.
The public GET/schema above is explicitly approved for this slice and no other
new public or durable contract is authorized. All domain behavior stays read-only.

Shared fixture dungeonbuddy-review-fixture-pg is running at127.0.0.1:54329,
owned by PRIME. ROOT and DOGFOOD use unique disposable databases through owning
fixtures. Retained54330/54331 are forbidden; no cleanup while either consumer is
active. Runtime outputs are this checkout's .pytest_cache/candidate-reader*.
No serving action until exact-head independent review and PRIME merge.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. TMPDIR="$PWD/.pytest_cache" /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/runtime/bin/python -m pytest -o addopts='' --basetemp=.pytest_cache/candidate-reader tests/test_exact_run_candidate_projection.py -q --tb=short
cd apps/live-control-ui
./node_modules/.bin/vitest run src/api/exactRunCandidateProjectionApi.test.ts src/planSurface/graphReviewWorkbench/GraphReviewCandidateRecapProjection.test.tsx src/modules/IngestionModule.test.tsx
./node_modules/.bin/tsc -b
./node_modules/.bin/vite build
```

Before delivery, inspect exact cumulative diff, commit/push/open the one assigned
PR and obtain independent ARCHITECTURE review. First runtime adoption overlays
only reviewed paths into the existing API/UI leases and preserves original user
tabs, source/candidates, graph head, media and ingestion state. Candidate rendered
acceptance may use exact retained S29 read only; no Process/provider/correction/
semantic decision/prepare/confirm or source write. No predecessor sync remains;
#1400's settlement is already in this base.

## Implementation review checkpoint

ROOT implementation is ready for independent exact-head review. Thirty backend
checks pass against synthetic production-produced runs in unique disposable
PostgreSQL databases, including authenticated bearer/session HTTP, no-store reads,
non-GM/remote rejection, no-write canonical-source trap, digest/scope/identity drift,
local IDs, duplicate/overlapping names, CommonMark and Unicode/CRLF coordinates.
The three UI suites pass 101 tests, including mounted Process→candidate, exact
source/World/session fencing, local inspectors, explicit admitted-memory switching,
real qualified-threat hover with zero native hydration, and unknown graph links.
Typecheck, production build, scoped Python lint and diff checks pass. Existing
React act/Pydantic schema-shadow warnings and Vite chunk-size warning remain.
No paid generation, real correction, semantic decision, admission or publication
was performed. Runtime adoption remains gated on independent review and merge;
retained S29 GET/render acceptance is still pending.


## Cycle1 review correction — PRIME rebrief

ARCHITECTURE held a83d5922f because the final shared reader unconditionally
strips leading YAML, including unknown source text deliberately preserved by the
server. PRIME authorizes the two shared reader paths above for this same read
capability: optional explicit frontmatter preservation, selected only by the
exact-candidate consumer; existing callers keep their default preprocessing.
This is an internal presentation option, not a new durable/API contract.
No overlap with DOGFOOD #1403's source-binding paths or settled Play #1402.
Re-anchored against main6743466d5f167f26d49c14d87b6353a35843f39e.

Prove the final mounted real renderer preserves unknown/malformed headers and
changed flattened prefixes/suffixes, while recognized envelopes already removed
by the server stay absent. Preserve candidate chips, evidence and raw source.
Test the default shared-reader behavior and switching the policy on rerender.
Do not disguise source using invented prefix prose or alter captured bytes.


Mounted verification also exposed a chip timing seam: source-span attachment ran
before React node-view labels existed, so full-paragraph matching missed evidence.
The leased reader now observes child-content arrival, reapplies the existing
source-span matcher, disconnects on cleanup and scrolls at most once per effect.
The mounted regression retains unknown header text, candidate inspection, exact
raw source and evidence attachment together. Existing shared-reader diagnostic
assertions are updated to the already-current saved-image/safe-URL messages;
no corresponding Markdown admission behavior is changed.


## Delivery settlement

API PID682397 and UI index5d90f904 deliver this reviewed capability. Ten retained
API records and captured Ingestion artifact hashes remain unchanged; older UI
assets are retained. Actual saved Session29 candidate opens66nodes/65edges and
Brin's local inspector/relationships/pinned evidence. No provider, correction or
publication occurred. Raw3component hashes are unchanged; the isolated read was
36.54ms (one sample, not a benchmark).66mentions are not66distinct nodes:
47nodes still have no literal linked mention.

Live rendering exposed two four-space-indented source blocks containing generated
navigation markup. CommonMark treats these as code; they must remain source text.
That remaining issue is separately bounded by HANDOFF-INGEST-indented-candidate-code.md.
This delivery does not establish full recall or semantic acceptance of Session29.
