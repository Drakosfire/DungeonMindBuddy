# SURFACE: reusable local World graph canvas primitives

**Status:** ACTIVE — authorized bounded component/adapter implementation.
Created: 2026-11-08
Conversation/workstream: Alan's blank Surface → local World → World Graph Canvas plan.
Flow / owner: SURFACE / DungeonMindBuddy.
Direction: DESIGN → CODE → REVIEW.
**Design authority base:** `7de8666c8d5ed6c2ca8e40c0c708e9c68c16bdc2`
Design inputs: `Docs/Design/DESIGN-blank-surface-to-world-graph-canvas.md` and existing local World repository contract `apps/live-control-ui/src/localWorld/localWorldRepository.ts`. Re-anchor: a successful fetch verified `origin/main@7de8666c8d5ed6c2ca8e40c0c708e9c68c16bdc2` (merges #2209 and #2266 after initial allocation); neither the graph path nor `localWorldRepository.ts` changed in those commits. The component lane was rebased to this current base before code changes were staged.
Activation authority: Alan explicitly assigned this bounded stewardship and implementation lane through the coordinating dot; the dot explicitly authorized resolving and activating the component/adapter/test handoff. No approval is attributed to PRIME or another unavailable person. The route/foundation lane remains separately owned.
Activation gate: none — the exact local repository contract is present on the pinned base and the lane is explicitly authorized. This does not activate route wiring or integration.
**Implementation base:** `7de8666c8d5ed6c2ca8e40c0c708e9c68c16bdc2` (`origin/main`, fetched again after the shared ref advanced).
| Branch / isolated checkout | `codex/world-graph-canvas-20261108` / `/home/drakosfire/Projects/.codex/world-graph-canvas-20261108/worktrees/DungeonMindBuddy` |
| Runtime/state ownership | Pure in-memory React/SVG rendering and isolated Vitest DOM only. No dev server, shared database, generated output, browser profile, provider, hosted graph or external service is used. |
PR topology: parallel-independent relative to the concurrent foundation integration lane. This lane consumes only the existing local World repository contract and does not depend on the other lane's unmerged route composition. Exact graph paths below do not overlap its `App.tsx` or `LocalWorldSurface.tsx` ownership. Recheck PR/worktree leases before publication; if an unmerged dependency is discovered, stop and return for topology change. The local write-lease preflight reported zero overlapping paths. A fetch during this lane confirmed the re-anchored base at `7de8666c8d5ed6c2ca8e40c0c708e9c68c16bdc2` (after #2209 and #2266 merges); the GitHub open-PR query was unavailable because `api.github.com` could not be reached, so hosted lane coverage must be retried before publication.
PR authorization: open/update this one implementation PR only after its exact-head review; no successor, foundation integration, merge, or deployment is authorized.
PR title: `SURFACE: add reusable local World graph canvas primitives`.

## §1 Mission and merge-ready invariant

**Mission:** A future local World Surface can render and directly edit the same local World through reusable, bounded graph primitives without treating layout as semantic data.

**Invariant:** Each rendered node and assertion retains its existing local identity; semantic edits go through `LocalWorldRepository.commitSemanticEdit` with expected local revision, while pointer/layout changes go through `writeLayout` with expected layout revision. Renderer state is controlled and never becomes a second graph store. Relationship identity is its local relationship ID, so parallel assertions are not deduplicated by endpoint pair. Failed, stale, interrupted and missing-endpoint paths do not silently discard or invent semantic facts.

## §2 Critique and failure cases

- The repository may return a semantic conflict, missing World, or operational error. The adapter must return that outcome intact to its caller; it must not optimistically replace the committed graph or clear a losing candidate.
- A layout conflict/error is independent of semantic state. A failed layout write cannot advance semantic revision or alter assertions.
- Repeated/interrupted edit completions can arrive out of order. Adapter requests capture IDs, snapshot, expected revision and edit description before awaiting; a completion for an older request cannot overwrite newer controlled input.
- Two relationships can share endpoints and kind while having distinct identities. Render and key both by relationship ID; never use endpoint-based deduplication.
- Cycles are valid. No synthetic World/root node or tree assumption is permitted.
- A missing relationship endpoint is a projection-integrity issue. Omit that edge and expose a deterministic diagnostic; do not create a fake node. Never silently claim the malformed source was repaired.
- Rendering cost must be bounded by explicit visible item limits; no perpetual force simulation or network/retrieval calls.

## §3 Outcome boundary

This slice supplies reusable controlled rendering, projection, and local-repository command adapters. It does not wire a route, title chrome, Save menu, guest/auth boundary, seed graph, or autosave lifecycle. It introduces no storage, ID allocator, semantic ledger, or dependency. Local object/relationship IDs and repository revisions remain authoritative. A later surface integration calls these primitives and chooses/creates the initial two-People/Location/Event content using repository commands. After a `committed` or `written` callback result, the consuming Surface must replace its controlled `record` with the returned record; on conflict it keeps the committed record and the returned candidate, and never retries/merges silently.

## §4 Exclusive expected write paths

| Path | Purpose |
| --- | --- |
| `Docs/Plans/HANDOFF-SURFACE-phase3-world-graph-canvas-primitives.md` | This bounded execution authority and evidence record. |
| `apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.ts` | Deterministic bounded graph projection preserving local identities and parallel edges. |
| `apps/live-control-ui/src/localWorld/worldGraphCanvas/localWorldGraphAdapter.ts` | CAS-backed semantic/layout intents over the existing repository contract. |
| `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.tsx` | Controlled accessible SVG canvas, selection and direct edit affordances. |
| `apps/live-control-ui/src/localWorld/worldGraphCanvas/worldGraphCanvas.css` | Quiet parchment/gold/dark contrast styling, reduced-motion and focus states. |
| `apps/live-control-ui/src/localWorld/worldGraphCanvas/graphProjection.test.ts` | Projection identity, cycles, limits and missing-endpoint evidence. |
| `apps/live-control-ui/src/localWorld/worldGraphCanvas/localWorldGraphAdapter.test.ts` | Semantic/layout CAS, interrupted edits, conflicts and identity evidence. |
| `apps/live-control-ui/src/localWorld/worldGraphCanvas/WorldGraphCanvas.test.tsx` | Keyboard/pointer/accessibility, controlled repeat edits and parallel-edge rendering. |

No wildcards. Any required path outside this list is a stop-and-return-for-amendment signal.

## §5 Exclusions and collision boundaries

| Path | Reason |
| --- | --- |
| `apps/live-control-ui/src/App.tsx` | Owned by the concurrent guest-entry/foundation integration lane. |
| `apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.tsx` | Owned by the concurrent foundation integration lane. |
| `apps/live-control-ui/src/localWorld/localWorldRepository.ts` and all existing localWorld files | Consume the existing contract; no edits to shared persistence/semantic authority. |
| `apps/live-control-ui/package.json`, `package-lock.json`, root config, server/API/auth files | No new dependency, routing, hosted graph access or infrastructure contract. |
| all other paths | Out of scope. |

Runtime/state: pure in-memory React/SVG rendering and isolated Vitest DOM only. No dev server, shared database, generated output, browser profile, provider, hosted graph or external service is used by this lane.

## §6 PR topology and ownership

`parallel-independent` from the pinned main base. The component lane does not import the concurrent unmerged route/surface files and does not need their behavior to prove its contract. Concurrent path ownership checked from the supplied active-lane assignment and local worktrees: the integration lane owns `App.tsx` and `LocalWorldSurface.tsx`; neither is in §4. Existing local World repository contract is read-only. If live GitHub/PR reconciliation is unavailable or reveals a changed parent/dependency, report that limit and stop publication pending a new topology decision. No merge/deployment authority.

## §7 Verification commands

```bash
cd apps/live-control-ui
npm test -- --run src/localWorld/worldGraphCanvas
npm run typecheck
npm run build
cd ../..
git diff --check 3b181c34b2ae064ec5d3910155ce572e74a363b4
```

Also review the exact cumulative diff and run the relevant repository contract tests if adapter coverage exposes a boundary regression. Do not run broad tests unless required by a touched contract. Record each command result and known build warnings.

### Implementation evidence (2026-11-09)

- `npm test -- --run src/localWorld/worldGraphCanvas --reporter=dot`: 17/17 pass.
- `npm test -- --run src/localWorld --reporter=dot`: 50/50 pass on the re-anchored 7de8666c tree.
- `npm run typecheck`: pass.
- `npm run build`: pass. Existing warnings remain for the `connectedPageApi.ts` dynamic/static import and the >500 kB initial bundle.
- `git diff --cached --check 7de8666c8d5ed6c2ca8e40c0c708e9c68c16bdc2`: pass.
- Independent read-only review found and corrected three P2 findings (expanded-canvas pointer scaling, parallel-edge label collision, and edge accessible names using internal IDs). Re-review closed those findings, then identified an unbounded invalid-edge diagnostic scan; the scan is now capped and a 1,000-invalid-record test passes. The reviewer confirmed no further material findings and did not rerun the test/build commands.
- Verification used the existing installed package trees through an ignored task-local node_modules overlay; `package.json` and the lockfile are unchanged. No route/browser dogfood was run because route wiring is owned by the separate integration lane. Required manual/component sequences: repeated edits; interruption/out-of-order completion; two same-endpoint parallel relationships; cycles; missing endpoint diagnostics; semantic conflict retaining candidate; layout conflict changing no semantic revision; keyboard selection/edit; reduced motion; configured projection caps.

## §8 State-authority sync set

No completion or future merge state is to be pre-recorded. After merge, the next dependent surface integration handoff should record the exact merged graph primitives and consume them; no stable architecture/design document changes unless this implementation falsifies a claim.

## §9 Acceptance and stop conditions

- Projection uses object IDs and relationship IDs unchanged, supports cycles and parallel assertions, enforces finite node/edge caps and examines at most `maxEdges + 12` relationship records; it lists at most 12 invalid-endpoint diagnostics, reports suppressed/unexamined counts, and never synthesizes endpoint entities.
- Controlled canvas has fixed deterministic initial positions when no saved layout exists, supports selection and layout drag without force simulation, and exposes keyboard operation, accessible node/edge labels, focus visibility and reduced-motion behavior.
- Semantic editor actions call only repository semantic CAS; layout actions call only layout CAS. Repeated submissions and stale completions cannot erase newer drafts. Conflicts/errors/missing records remain visible and preserve repository-returned state.
- Tests include two People, one Location, one Event, a Person-to-Person assertion and all three connected to the Event; this fixture is test-only and uses distinct local IDs. No synthetic root entity is added.
- Tests prove object/relationship identity preservation, parallel edges and labels, cycle/self-loop support, finite projection caps including 1,000 malformed relationships, missing endpoints, expanded-canvas pointer drag, semantic vs layout revision separation, conflict preservation, failed/interrupted/repeated edits, and accessible keyboard interaction.
- Stop if implementation requires route/chrome wiring, package/lockfile/dependency mutation, repository schema or persistence changes, a new semantic allocator/history, hosted graph/network calls, or edits outside §4. Return the exact needed path/owner and proposed seam.
