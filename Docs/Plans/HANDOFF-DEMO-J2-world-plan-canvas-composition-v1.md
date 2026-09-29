---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J2 — World-owned Plan canvas composition
  - Direction: STEWARD → CODE → PRIME
  - Handoff: `Docs/Plans/HANDOFF-DEMO-J2-world-plan-canvas-composition-v1.md`
  - Topology: serial; one assigned implementation PR, no merge by DEMO

  ## Verification pointer
  - Exact dispatch base: `eac67508ea34115b102c7c4af8a55e17843a16d9`
  - Review contract: active handoff, cumulative diff, §7 owning-boundary evidence
---

# HANDOFF — restore the World-owned Plan canvas and editing chrome

**Created:** 2026-09-29
**Status:** COMPLETE / HISTORICAL — Buddy #789 merged at `ed1bf1ba0531bf9018f2397863825fa20c781bfe` from reviewed code head `7e4fb73d5a553b58bd1350c9c0ded653ef97b2e0`; one distinct review-head cycle. Composition implementation is complete; the operator explicitly rejected its visual quality, so Plan presentation and J2 remain unaccepted.
**Workstream / owner:** LOCAL DEMO ACCEPTED / DEMO J2; Buddy Plan composition
**Direction:** STEWARD → CODE → PRIME
**Activation base:** Buddy `main@eac67508ea34115b102c7c4af8a55e17843a16d9` (PR #788 merge)
**PR topology:** serial — this is the one assigned implementation PR; no stacked successor
**PR title:** `DEMO: restore the World Plan canvas and editing chrome`
**PR authorization:** after PRIME accepts this handoff's boundary, open/update the assigned implementation PR without another operator prompt; do not merge. PRIME owns ecosystem merge coordination.
**Implementation branch:** `codex/demo-world-plan-composition-impl`
**Activation record:** PRIME reviewed and accepted the exact path lease plus World-owned Plan / Agent identity boundary before production implementation began. This authorizes only the existing composition PR, not Agent/API work.

This handoff is on a clean, isolated branch based on the verified current remote
`main` SHA above. It does not edit the detached user checkout or the existing
PR #788 merge history.

## §1 Mission and merge-ready invariant

Integrate the World-owned Plan document into Buddy's established Plan canvas and
editor-tool composition while preserving the exact World/document ownership,
save, reload, and uncertain-recovery behavior delivered by #788.

**Merge-ready invariant:** a World-owned Plan is not a raw contenteditable
rectangle with a handful of unrelated form controls. It uses the established
Buddy Plan canvas presentation and the existing editing/tool affordances, while
document navigation and Save remain bound to the exact World-owned Plan.
Changing Worlds/documents cannot transfer editor state or actions across
identities. This is a composition slice, not proof that the DEMO J2 Agent
acceptance has passed.

The experience must retain these exact identities:

```text
World-owned Plan:
  world_id = selected managed World UUID
  campaign_id = null
  target_session = null
  document_id = exact selected/saved Plan UUID, or no document while blank
```

Do not invent a campaign ID, session number, graph head, or Plan document to
make a campaign-oriented component mount.

## §2 Current evidence and architecture boundary

Re-anchored facts:

- PR #788 merged to `main` at `eac67508ea34115b102c7c4af8a55e17843a16d9`;
  exact reviewed code head `27bb1a76a113ef85f54c6ac09bbd4d18aa121b41`;
  five distinct reviewed heads through the final accepted head. It proves
  World-owned Plan create/save/reload/recovery and the exact World/null-campaign
  Content shape. It does not prove full Plan-shell composition or J2.
- The live blank World B witness is
  `http://127.0.0.1:5201/plan?world=pr788-exact-head-witness-b-2026-09-28`.
  Operator feedback: the Plan surface looks awful, has no perceptible canvas
  boundary, and falls back to generic/default editor styling. Inspection shows
  the World branch in `PlanSurfacePage.tsx` directly renders `EditorContent`
  inside `.world-owned-plan__editor`. The established campaign Plan canvas
  instead composes `PlanSurfaceCanvas`, `plan-surface-canvas`, and the
  `tiptap-spike-editor md-content md-theme-*` presentation. A thin CSS border is
  not a sufficient product boundary: the World route is also missing the
  established toolbar and Plan context/action composition. The required repair
  is to compose the actual shared canvas and its owning surface controls, not
  patch the raw editor with another decorative border.
- World-owned Plan already has its own Saved Plans selector, local draft journal,
  uncertain-create recovery, and scope-specific APIs. Keep these as authority;
  do not replace them with campaign/session Plan descriptors.
- The global route navigation already remains mounted. The missing established
  Plan composition includes the editor toolbar and Plan-owned context/actions;
  verify the real canvas boundary and styling in-browser rather than inferring
  success from a CSS declaration or component mount.
- Open PR #781 (`INTERACTION MAP: prove shared Build projection action`) leases
  Agent semantic-action projection paths and a handoff; no overlap with this
  UI lease. Open draft PR #763 is a paused Rules packet and its API/dependency
  paths do not overlap this lease. Recheck all open PRs immediately before code
  dispatch and again before PR creation.

### Agent identity blocker — explicit, not papered over

The existing Agent path is not currently compatible with the proper #788
World-owned Plan identity. `PlanAgentInteractionBar` and the managed `/api/live/query`
route use a campaign/session-shaped request: `campaign_id` is required, `session`
must be at least 1, and the route verifies a managed Plan document whose
campaign and target session equal those values. #788 World-owned Plan documents
instead have `campaign_id=null` and `target_session=null`. Agent thread storage
and `AgentInteractionScope` are also campaign-keyed.

ARCHITECTURE confirmed there is no accepted end-to-end Agent-turn endpoint for
this identity. Ownership is Buddy DEMO/J2, not MIND or WorldKeeper. Its
recommended smallest contract is a separately typed World-Plan Agent scope
(`world_id + document_id`, no campaign/session), with server verification of
the active exact World-owned Plan, World graph retrieval scoped by exact World
and optional revision, and thread/proposal identity isolated by World+document.
That is a distinct API/thread/persistence capability and is outside this
canvas-composition lease. ARCHITECTURE's assessment is routing evidence, not an
implementation authorization.

This implementation may not make Agent appear functional by sending a fake
campaign or session. Do not add a decorative Agent panel or inert Open button.
The user has clarified a DEMO minimum: **a real, surface-aware conversational
Agent entry and conversation on every DEMO surface**. This is baseline
capability, not optional polish. The baseline must receive truthful current
surface/World/document/object/selection context when present, handle absent
documents and graph heads honestly, and isolate multi-turn context so a World
or document change cannot silently keep routing to stale context. Advanced
authoring/action execution is a later capability and must not be bundled into
the baseline merely to expose the Agent.

Do not make an inert Agent panel/button or fake campaign/session identity. The
current composition implementation remains limited to its accepted UI lease;
before any Agent backend work, produce one reusable Plan/Play/Build/Ingest
surface-aware Agent contract proposal, with actual owner paths and owning-boundary
proofs, for PRIME and ARCHITECTURE review. Avoid a WorldPlan-only design that
would immediately need replacement on the next surface. No Agent/API paths are
leased by this handoff. Carry the user's all-surfaces minimum explicitly into
the roadmap and next substantive Agent handoff.

## §3 Required product behavior

1. **Canvas presentation:** World Plan content uses the established Plan editor
   canvas/presentation contract, including its visible boundary, reading width,
   registered Markdown component styling, and responsive behavior. Do not merely
   add more ad-hoc CSS to the current blank panel.
2. **Editor tools:** existing Plan formatting/edit tools act on the exact mounted
   World Plan editor. Tool generations are invalidated when World or document
   identity changes; no stale toolbar action can mutate another document.
3. **World Plan navigation:** Saved Plans, New blank Plan, and existing selector
   behavior remain scoped to the selected World. The URL and displayed document
   identity remain exact. Loading a document or changing Worlds cannot inherit a
   campaign/session selector.
4. **Save and recovery:** the #788 World-specific save, CAS/revision, recovery,
   create uncertainty, and cross-World protections remain authoritative. Editor
   toolbar commands must feed that existing World-owned writer; do not route them
   through campaign Plan persistence.
5. **Truthful Agent state:** this slice must not advertise usable World Plan Ask
   while the API rejects exact World/document/null-session identity. The accepted
   UI-02 no-plugin behavior remains: no fake Agent drawer or empty Ask sheet.
   Record the unresolved J2 Agent route as a successor blocker, not a J2 PASS.
6. **Legacy compatibility:** campaign Plan, Runbook, Play, Build, Ingest and
   global navigation retain their existing behavior.

## §4 ACTIVE write lease

| Path | Bounded role |
| --- | --- |
| `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` | Compose World-owned Plan with shared Plan canvas/editor affordances while retaining #788 World-specific lifecycle |
| `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` | World Plan canvas, toolbar, navigation, identity replacement, and persistence regressions |
| `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | Extract/reuse presentation and toolbar seam without passing fake `PlanSessionDescriptor` or campaign identity |
| `apps/live-control-ui/src/planSurface/components/PlanSurfaceContext.tsx` | Compose truthful World/document Plan context and invalidate it on identity changes without manufacturing campaign/session descriptors |
| `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | Guard established campaign Plan composition and shared toolbar compatibility |
| `apps/live-control-ui/src/styles.css` | Remove/retire only World-owned ad-hoc editor rules that conflict with the shared canvas; no app-wide theme redesign |
| `Docs/Plans/HANDOFF-DEMO-world-owned-blank-plan-v1.md` | Backward-looking completion record for #788; preserve its original authority and evidence |
| `Docs/Roadmaps/ROADMAP-demo.md` | Backward-looking #788 completion sync; record that visual/shell composition and J2 remain open |
| `Docs/Plans/HANDOFF-DEMO-J2-world-plan-canvas-composition-v1.md` | Keep this handoff's status, evidence, and successor proposal record current |

No unlisted production path is authorized. If the reusable seam needs another
file, stop and ask PRIME for a same-slice lease amendment before editing it.

## §5 Exclusions and collision boundaries

- No API/server, WorldKeeper, DungeonMind, provider, retrieval, graph projection,
  or Agent request/storage contract changes in this slice.
- No fake `campaign_id`, `session=1`, campaign descriptor, graph revision, or
  World-owned document adoption.
- No new Agent panel/drawer, provider endpoint, unsupported Ask button, or J2
  multi-turn acceptance claim. The Agent identity mismatch is explicitly routed
  for owner/architecture disposition; it must become its own accepted contract
  and write lease before implementation.
- No global Plan redesign, new theme, Canvas dependency, or UI substrate work.
- No rewrite of #788 persistence/recovery or campaign Plan/Runbook behavior.
- No edits to PR #781, #763, other repositories, or the user’s detached/dirty
  checkout.
- No model/provider calls. This is local presentation and editor composition.

### Runtime and persistent-state ownership

This implementation lane may use only the isolated API `127.0.0.1:8821`, UI
`127.0.0.1:5201`, disposable PostgreSQL port `55441`, database
`dmb_world_plan_demo`, and worktree-owned output roots for its product witness.
DEMO owns only the exact isolated API `8821`, UI `5201`, and disposable
PostgreSQL `55441` runtime for this lane, and may restore/restart them only after
verifying free/owned ports, PID, process/worktree, and logs. No shared process
may be stopped or replaced. Never write the persistent J1
databases `54330`/`54331` or any shared
rehearsal state. No migrations against an existing database; use only the named
disposable target after verifying identity.

## §6 Implementation constraints

- Prefer factoring a presentation-only Plan canvas/editor seam over mounting the
  campaign `PlanSurfaceShell` with a fabricated `PlanViewProjection`.
- The World-owned writer and `document_id` selection remain owned by
  `WorldOwnedPlanPage`; the reusable editor emits edits/tool intents to that
  owner. It does not become a second persistence authority.
- Preserve exact Markdown/component JSON round trips, editor generation keys,
  focus behavior, and AppChrome tool-generation invalidation on object change.
- A saved Plan and an unsaved blank Plan are different identities. Do not let a
  toolbar action from one remain valid after switching between them.
- The PR includes the backward-looking #788 handoff/roadmap sync but must not
  premark this composition slice, J2, J3, or the full local demo complete.

## §7 Required proof

### Automated

- World Plan page owning tests for blank editor, existing saved Plan, World switch,
  document switch, toolbar action binding, format/registered component behavior,
  Save/reload, CAS conflict, and #788 uncertain-create recovery.
- Existing `PlanSurfaceShell` owning tests prove campaign Plan toolbar and canvas
  behavior is unchanged.
- Scoped UI tests, project typecheck/build attempt, and `git diff --check`; report
  the inherited `ThreatPublicationPanel.tsx` JSX namespace failure honestly if it
  remains unchanged.

### Browser dogfood on exact implementation head

- Desktop and `390×844` screenshots of blank and authored World-owned Plans.
- Show an obvious editor/canvas boundary and the real toolbar; verify the editor
  remains legible without a content-derived height and without generic browser
  defaults.
- World A: open blank Plan, use a formatting/component tool, author, Save, reload,
  and reopen the exact document. World B: verify empty/different document state
  and that no A toolbar callback or draft leaks into B.
- Verify no-plugin behavior suppresses only unsupported Agent chrome; it must
  not suppress the supported Plan toolbar, truthful Plan context, or navigation.
  Do not claim Agent baseline acceptance from this composition slice. The
  universal surface-aware conversational Agent contract is a mandatory next
  capability and must be proposed for PRIME/ARCHITECTURE review before Agent
  backend implementation; advanced authoring/actions stay separate.
- Repeat the #788 ordinary persistence/recovery witness impacted by the editor
  composition; no database reset/deletion or user-data overwrite.

### Authority record

The implementation PR updates #788's handoff/roadmap with merge `eac67508…`,
reviewed code head `27bb1a76…`, five distinct review-head cycles and the bounded
acceptance evidence already recorded on #788. Preserve #788's accepted
persistence/recovery and bounded styling evidence. Record the later operator
dogfood as a distinct finding: the full integrated Plan composition remains
unaccepted because the World-owned route omits the shared canvas/tools/context;
this PR addresses that composition gap. Neither PR alone closes J1/J2 or LOCAL
DEMO ACCEPTED.

**Later authority sync (2026-09-29):** the required all-surface contract is
defined by PR #790 at accepted exact design head
`3fcc60de6159add04fe9455f5aee0a58816bfece` (PRIME Cycle 4 DESIGN PASS;
ARCHITECTURE exact-head focused PASS). Its bounded backend implementation
successor, PR #791, merged at `6501bfa5143592cec8d7a3f521e3f34d929a5a95`
from reviewed code head `40e7c5f81ab0a6faa53026ea571d2994f77d163c` after two
distinct review-head cycles (Cycle 1 HOLD `5349662805`; Cycle 2 APPROVE banner
`5350948969`). The backend remains only a baseline: shared UI/adoption for
Index, Plan, Play, Build, Ingest, and Combat, owner-to-backend end-to-end
witnesses, and human Plan visual acceptance remain open. This retrospective
update does not claim those successor outcomes are complete.

## §8 Handback

Return the PR URL, exact implementation head/base, changed-path table against
this lease, automated/browser evidence, runtime identity and process handoff,
remaining Agent contract owner/status, and concise proof that #788 persistence
and legacy campaign Plan behavior remain intact. Do not merge. PRIME reviews the
exact head and controls merge sequencing.

### Current execution evidence (2026-09-28)

- Product code remains based on the accepted #788 integration and is served from
  the isolated implementation worktree through the single UI listener at
  `127.0.0.1:5201`; it proxies to the existing isolated API `127.0.0.1:8821`.
  The exact old 5201 Vite PID was verified under the retired #788 worktree and
  gracefully replaced; shared ports/databases and API 8821 were not changed.
- Browser dogfood exercised the exact World A saved-document URL. Its existing
  `The Lantern Causeway` Plan was preserved. A separate `J2 Canvas Boundary
  Witness` document was created through the normal World-owned Plan writer,
  formatted with the mounted Heading tool, given a registered Read-aloud block,
  saved, and reloaded at exact document UUID
  `8e02715a-fc5b-48dc-ab7c-ba470a0909a8`. World B remained blank with no
  inherited A title, content, document or toolbar state. No source, campaign,
  session, graph head, provider call or Agent behavior was fabricated.
- The first implementation accidentally rebuilt a lookalike canvas frame in
  the World route. It has now been factored into `PlanSurfaceCanvasFrame` in
  `PlanSurfaceCanvas.tsx` and is used by both existing campaign Plan/Runbook
  views and the World route. This preserves the shared `plan-surface-canvas` /
  `tiptap-spike-editor` boundary while leaving the World-owned writer
  authoritative. The dark canvas rim and parchment sheet have separate,
  high-contrast edges rather than relying on default editor borders.
- Desktop blank and authored views show the shared framed dark workspace around
  a centered parchment canvas, visible toolbar, and readable component styling.
  At 390×844 the layout had `document.scrollWidth=375` (viewport390), canvas
  width335 and editor width307; the authored Read-aloud block remained readable.
  The existing no-plugin state suppresses Agent chrome without suppressing Plan
  tools, context or navigation. Browser console reported no errors/warnings.
- Exact owning tests: PlanSurfacePage + WorldPlanSurfaceContext + campaign
  PlanSurfaceShell, 115 passed. `npx vite build` passed (existing chunk-size
  warning). `npm run build`/typecheck remains blocked only by the inherited
  `ThreatPublicationPanel.tsx:553` JSX namespace error; the file blob is
  identical to #788 base `eac67508…` (`f1764cfa…`). `git diff --check` passes.
- PRIME and ARCHITECTURE have the proposed reusable all-six-surface
  conversational Agent context contract for review. That proposal is not
  accepted authority or implementation scope; no Agent/API files were changed.
