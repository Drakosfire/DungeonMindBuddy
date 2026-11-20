# DOGFOOD: explore the evidence behind an answer

Status: ACTIVE under the user's direct design instruction on 2026-10-13: apply the loaded graph explorer's readable, navigable presentation to the evidence returned for a question.
Base: current remote `main` at `ec1da1b7872fe6d4f9fee0b501510a5137677eea`.
Topology: serial, one Plan-answer evidence presentation slice. Open PRs were checked; none owns this UI surface. The loaded graph inspector (#1078) and conversation/evidence improvements (#1113) are merged predecessors.
Write lease:
- `Docs/Plans/HANDOFF-DOGFOOD-queried-evidence-presentation.md`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.css`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx`

## Capability

Present evidence attached to a saved Plan answer as a compact, collapsed-by-default evidence trail. Expand it to inspect the answer's graph claims, distinguish cited Graph references from readable source passages and related recap passages, and open the exact server-pinned passage in a readable paper-style card. Group sources under the exact claim they support. Keep opaque IDs and revisions in the existing turn details rather than the primary reading path.

## Invariants and failure cases

- Render only claims, citation mappings, source-open targets and status rows present in that saved turn. Never infer a source-to-claim relationship or use the shared loaded projection as if it were the question's evidence.
- Preserve the current exact-World, graph-revision, artifact, and anchor checks in the existing source reader. Opening evidence reads a pinned source only; it never reposts the Ask.
- Keep graph citations, readable Graph evidence, and related recap context as distinct counts and labels. A citation reference is not a readable passage.
- Make absent, partial, overflowed, or unavailable source context understandable without exposing opaque metadata. Do not claim exhaustive retrieval or quote a source that was not opened.
- Keep source prose collapsed until the user chooses a passage. Preserve keyboard access and fit compact widths.

## Runtime and verification boundary

UI-only. No API, schema, Graph, provider, database, port, or running 5202 changes are leased. Verify the mounted conversation at its owning component boundary with focused tests, typecheck, and cumulative diff review. Live runtime dogfood remains a separate deployment/acceptance step.

## Verification evidence

- `WorldPlanAgentConversation.worldHistory.test.tsx`: 197 tests passed, including collapsed-by-default behavior, exact pinned source reads, recap continuation, partial/missing-source states, and the no-repost guard.
- `npm run typecheck -- --pretty false` in `apps/live-control-ui`: passed using a temporary validation copy because this checkout has no installed dependencies and the shared dependency directory is outside its writable boundary.
- `git diff --check`: passed.
- No browser/runtime visual acceptance was performed; 5202 was left running and untouched.
