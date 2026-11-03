# GRAPH: retire the orphan Union recap renderer

Status: ACTIVE under the operator's cleanup and demolition goal.
Owner: PRIME. Base: origin/main@ba208e8002413f3aec228d3ac7ec7fe715fe40dc.
Branch: codex/retire-union-recap-renderer.
Checkout: /home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy.
Topology: parallel-independent of PR2049@9e0dddde80af9143409543c3554b6771e346f23e.
No unmerged behavioral dependency or shared write path: that PR owns backend
execution evidence; its entire UI subtree is byte-identical to this base. Reuse
this checkout serially between frozen branches. No new checkout, environment,
dependency, provider, database, running service or Graph/Gold effect lease.

## One reviewable outcome

Delete the unused 116-line UnionSupergraphRecapProjection component, its 359-line
exclusive test and its eight-line exclusive source-mode type/comment. Current
source references to the component are confined to its definition and test; no
application import, catalog entry or wildcard loader exists. The source-mode
export is imported only by that component. Do not mistake RecapProjectionSource
for the active RecapProjectionSourceSpan contract.

The audit union-preview-retirement-caller-audit-v1.json pins source hashes and
caller limits. ADVERSARY separately scanned 561 current/planned private drivers
with no exact legacy API/symbol matches; its durable consumer audit is scoped
independent evidence, not a blanket unused-code or Gold-deletion certificate.

## Exclusive expected write set

- Delete apps/live-control-ui/src/planSurface/graphPreview/UnionSupergraphRecapProjection.tsx.
- Delete its exclusive UnionSupergraphRecapProjection.test.tsx.
- apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx: remove
  only the exclusive RecapProjectionSource type and its inaccurate legacy comment.
  Keep the actual native recap component and every behavior unchanged.
- This handoff. Do not edit PR2049's handoff or implementation lease.

## Critique, preservation and validation

The orphan renders GraphProjectionReader and shared node/evidence presentation,
but those units have current exercised native callers. Preserve their bytes,
shared Graph/Gold types, fixture bytes and current transport/publication. In
particular, unionSupergraphFixture still supports current object-card and recap
node-presentation tests. Retain shared CSS and actual World Graph projection.
Do not add a replacement, alias, fallback or compatibility entry.

The adjacent unused Union client is woven into current review tests through
obsolete mocks/spies. Its transport/test retirement is a separate bounded slice.
Directory-discovery developer/Gold routes require their own caller and authority
audit; this handoff does not delete them, Gold fixtures or independent assessment.
The full cleanup goal remains open after this small slice.

Before deletion, UI type checking passes. Four shared/native presentation test
files produce 27 passes and seven failures at both this exact base and PR2049's
identical UI subtree. Six expect an obsolete Published recap label; one uses an
ambiguous heading query after additional object-card headings. Original logs
and union-preview-shared-presentation-baseline-comparison.json are retained.
Compare after deletion without relaxing assertions or absorbing fixture debt.

Verify import closure, full UI type checking and the same shared/native cohort.
Review the cumulative four-path diff, commit/push/open one small PR, obtain
independent Bugbot review and applicable CI, then merge and settle under standing
PRIME authority. Any delivery gets a separately re-anchored lease; these source
changes never authorize provider calls or primary/Graph/Gold writes. Tests and
code deletion do not establish ordinary dogfood or operator acceptance.

## Author verification

After deletion, a fresh full TypeScript build check passes. Neither retired
symbol remains in UI source/tests. The same four shared/native test files still
produce 27 passes and the same seven failed tests/messages as exact base; no
assertion was relaxed or unrelated fixture repaired. Comparison and original
logs: union-recap-renderer-author-verification.json. The cumulative runtime diff
is the two deletions plus the exclusive source-mode type removal. Shared Graph
reader, presentation, contracts and fixtures remain byte-identical. Independent
review, CI and merge/delivery settlement remain required.
