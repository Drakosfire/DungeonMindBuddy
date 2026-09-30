# DEMO — exact World Plan work-object identity

**Status:** MERGED — Buddy #801, reviewed head `550aa4c0251ffa08477bda2293829725f2d6a8d8`, merge `442ee470a33ce4dfa0ba3239c9022ab69220cde9`

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Authority:** [STEWARDS-HANDOFF-demo.md](STEWARDS-HANDOFF-demo.md), operator-approved second serial slice

**Pinned predecessor/base:** Buddy #800 merged as `393ec5664916ee4eeabe0d0801bc6c8de9820c79`; fetched `origin/main` at that exact ref

**Proposed branch:** `codex/demo-world-plan-identity` in `/home/drakosfire/.codex/worktrees/8b2b/DungeonMindBuddy`

**Topology:** serial. The Plan document-switch safety predecessor is merged. The EditHost controls successor remains blocked until this identity slice lands. Closed #793 is reference-only.

## One capability and owning invariant

Publish exactly one current World Plan canvas work object through the existing
AgentInteraction/Surface publication seam. A saved Plan uses its server-issued
document ID; an unsaved blank Plan uses a unique browser-local draft token
scoped to its World. The World Plan context contribution and canvas publication
must carry the same exact surface identity, so later EditHost commands can
target the work object without guessing from a title, revision or editor
generation. Shared publisher, lease and host contracts remain unchanged.

The browser-local `dmb_plan_promotion_recovery_v2` record currently has no
`local_draft_id`; its read and write helpers whitelist fields. Merely creating a
token during render would lose it on reload or the next draft write. Migrate a
legacy blank local record once, preserve its title/body/revision, pending write
and uncertain-create recovery, and persist the token. Keep that token through
edits/reload; deliberately rotate it on New blank. Keep server document ID,
local token, revision and TipTap editor generation distinct. Existing saved
records continue to use their exact server ID. A successful create promotion
changes the active work object to the returned server ID without assuming an
uncertain create succeeded.

While a different saved Plan snapshot is unresolved, retire the outgoing
active canvas publication. Publish the incoming identity only after its
World/scope validation succeeds. On World replacement or unmount, release the
old publication. A failed load must not claim the incoming document identity.
The page continues to use its existing local recovery and save/conflict paths.

## Proposed exclusive expected write lease

- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- `apps/live-control-ui/src/planSurface/components/PlanSurfaceContext.tsx`
- `apps/live-control-ui/src/planSurface/components/PlanSurfaceContext.test.tsx`
- `apps/live-control-ui/src/planSurface/worldPlanIdentity.ts` — only if a small shared World Plan identity helper is needed to prevent context/canvas drift
- `Docs/Plans/HANDOFF-DEMO-world-plan-identity.md`
- `Docs/Plans/HANDOFF-DEMO-plan-document-switch-safety.md` — only the backward-looking #800 result/status settlement
- `Docs/Roadmaps/ROADMAP-demo.md` — backward-looking #800 settlement and this slice's execution evidence

No AppChrome/EditHost controls, shared Surface publisher/host changes,
styles, package dependencies, lockfiles or other repository paths are leased.
Current open Buddy PRs #798, #781, #763–765 and #760–761 were checked after
#800; none owns these proposed paths. Any newly required path returns to the
steward/PRIME before editing.

## Runtime and verification contract

No service, port, database, schema, corpus or external state is leased. Use
mocked APIs and mounted World Plan/AppChrome boundary tests. Prove migration of
legacy blank recovery without field loss; stable identity across edit/reload;
distinct identity after New blank; exact World and saved-document replacement;
local-to-server promotion; retirement during pending/failed selection and
unmount; and matching context/canvas identity. Verify the cumulative base-to-head
diff, focused tests and UI typecheck, stating inherited failures. This is an
identity publication slice, not universal Agent turn wiring or EditHost command
placement. No full connected DEMO acceptance is claimed by these tests.

**Settlement:** PRIME reviewed the cumulative eight-path diff and independently
reran 18/18 focused Plan page/context tests at the accepted head. The existing
`ThreatPublicationPanel.tsx:553` JSX namespace typecheck error remained outside
the diff. No runtime, database, corpus or provider was used. The exact World
Plan identity lease was released by merge; EditHost placement and the connected
DEMO journey remain open.
