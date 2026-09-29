---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J2 — World Plan shell adoption
  - Flow: DEMO
  - Direction: STEWARD → CODE → PRIME
  - Handoff: `Docs/Plans/HANDOFF-DEMO-world-plan-shell-adoption-v1.md`
  - Topology: serial; amend existing #793
  - Design ref: `codex/demo-world-plan-shell-adoption` (exact revision in PR)

  ## Verification pointer
  - Base: `main@76239846c98797bb1455ffa22b2a273d64591205`; adopted #793 head `cba5dddcf2c482ec729e714cf75e6acd665b42e9`
  - Design/code seam inspection; mounted integration and live product evidence follow activation.

  Prior #793 visual witness is historical evidence for that exact implementation, not acceptance of shell adoption.
---
# HANDOFF — World Plan adopts Buddy's established editing shell

**Created:** 2026-09-29
**Status:** BLOCKED — PRIME must review the amended contract, settle #793's predecessor disposition, and explicitly activate the one serial implementation lane.
**Workstream / owner:** DEMO / World Plan composition
**Design base:** Buddy `origin/main@374d69d78ef58a062116de73e095b57f4a92ca15` (after #794 and #795 merged); the #793 implementation source head is `cba5dddcf2c482ec729e714cf75e6acd665b42e9`.
**Topology:** serial amendment of #793 only. No successor PR.
**PR title:** `DEMO: adopt the World Plan editing shell`
**PRIME:** owns review, predecessor disposition, activation and merge.

## §1 Mission and invariant

A GM authors a World-owned Plan in Buddy's clean central canvas while existing navigation and EditHost provide document and editing controls.

**Merge-ready invariant:** the selected World Plan surface, canvas work object, and singular AppChrome editing inventory always name the same exact World/work object. Commands resolve the editor and selection at invocation; they become inert when the selection, editor generation, save promotion or mounted surface is no longer current. Recovery stays visible and actionable.

One invariant covers blank, saved, switching, recovery and async-completion paths: the current World Plan work identity gates every control and editor intent. The easiest boundary to miss is mounted `AppChrome`/`EditHost`; existing `PlanSurfacePage.test.tsx` mocks AppChrome and cannot prove it. The adversarial sequence is hold an EditHost callback, switch document/World, reset to blank or promote by Save, then invoke it or finish an old async save. The new §7 test detects it.

## §2 Re-anchored authority and lane

- `AGENTS.md`, amended DEMO mandate in #794 and `Docs/Roadmaps/ROADMAP-demo.md` govern. Current `origin/main` is `374d69d78ef58a062116de73e095b57f4a92ca15`; #794 merged at that SHA and #795 policy cleanup merged at `83f25b1f9bfe70555a82b08ef4f5ca5af26a691d`. #793 remains OPEN at `cba5dddcf2c482ec729e714cf75e6acd665b42e9`. PRIME chose its deliberate amendment and retains predecessor disposition.
- Incoming DEMO task: `01a0edf2-b1e1-7281-9448-1d5524f8d4f8`. PRIME retired archived outgoing task `01a0885e-375c-7501-9f6e-a58528b39894` from DEMO implementation/design/runtime mutation. It was not restarted and did not acknowledge handback. `Docs/Plans/STEWARDS-HANDOFF-demo.md` now names the incoming task as owner under PRIME's explicit transfer authorization; its mission is unchanged. Preserve its refs/drafts as read-only evidence; do not claim its tool-backed goal state is known.
- Adopted source is isolated on `codex/demo-world-plan-shell-adoption`, based on #793's exact head. The detached user checkout stays off `main`. Proposed implementation uses this lane after PRIME activation; no lease is active while this handoff is BLOCKED.
- PRIME explicitly authorized the incoming owner-field update in `Docs/Plans/STEWARDS-HANDOFF-demo.md` after #794 merged. This assigned PR carries that backward-looking transfer with the roadmap and this handoff; the mission is unchanged.
- Separate open PRs #781 and Rules #763–#765 have distinct owners; recheck refs and active leases before dispatch.

## §3 Observable paths and identities

| Path | Required result | Owner |
|---|---|---|
| Blank Plan | Existing global navbar and `WorldPlanSurfaceContext` remain; a unique World-scoped local draft identity is published to canvas, context and EditHost. | World Plan |
| Saved Plan | Publish literal selected World UUID and exact saved document UUID/revision; matching editor inventory uses the same work-object target. | World Plan |
| New blank / World or document switch | New target cannot alias another World/document; prior callbacks are invalid immediately. | Plan page/context |
| Save promotion | On returned document UUID, transition canvas/context/inventory together from local token to saved identity; invalidate held local callbacks. | Plan save controller |
| Loading, failure or recovery | Honest disabled reason; visible recovery actions remain bound to the selected recovery state; existing save/conflict/CAS behavior remains. | Existing controller |
| Late completion / unmount | Existing selection-epoch fences prevent a displaced async write from mutating replacement UI. | Plan page |

Use saved work kind `world-plan-document`, target id structured as JSON tuple `("world-plan-document", worldId, documentId)`. Use local kind `world-plan-local-draft`, id tuple `("world-plan-local-draft", worldId, localDraftToken)`. The collision-resistant local token is generated once per draft, stored through edits/reload recovery, and replaced on deliberate New blank. Never derive identity from title/content. World is part of all target tuples.

The canvas work object, `WorldPlanSurfaceContext` instance identity and `AppChromeToolsGeneration.target` must encode the same tuple. Its selected Plan context carries literal World/document identity; no campaign/session aliases. Keep revision, edit generation, selection epoch, editor generation and local token as separate lifetimes. Save promotion changes the shared work-object identity atomically after the exact server document id exists.

## §4 Proposed write lease — inactive while BLOCKED

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` | Publish exact surface/work object; provide one matching AppChrome inventory; move title, pinned Save, format and insert actions to established hosts; remove duplicate inline controls; preserve visible recovery and callback guards. |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceContext.tsx` | Add local draft identity to the existing World Plan surface instance key, matching publication target. Preserve selector/New control and existing context host. |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` | Keep persistence, promotion, uncertainty and conflict regression coverage. |
| Create | `apps/live-control-ui/src/planSurface/PlanSurfacePage.editHost.test.tsx` | Mount real AgentInteractionProvider, selected World, AppChrome and EditHost; prove the §7 mounted boundary. |
| Modify only if needed | `apps/live-control-ui/src/styles.css` | Remove obsolete inline-control placement rules while retaining #793 canvas/page styles. |
| Modify | `Docs/Plans/HANDOFF-DEMO-world-plan-shell-adoption-v1.md` | Dispatch facts/evidence, without pre-marking completion. |
| Modify | `Docs/Plans/STEWARDS-HANDOFF-demo.md` | Record the PRIME-authorized incoming owner transfer; preserve mission and scope. |
| Modify | `Docs/Roadmaps/ROADMAP-demo.md` | Material predecessor sync, owner/next action and connected milestone state. |

No neutral publisher/provider/lease, AppChrome/EditHost implementation, global nav, shared context-host contract, API/persistence, graph or other repository paths are leased. If required, stop for owner review and an explicit lease amendment. Existing `WorldPlanSurfaceContext` and global navbar are reused. Do not add a second navigation bar or duplicate context.

## §5 Runtime and product boundary

Prior host inspection found no 5202/8821 listeners at that time; it found other Vite processes at 5198 (`/tmp/dmb-demo-j1-native-world-source-authority`) and 5201 (`/tmp/dmb-demo-world-plan-composition-work`), plus SERVER 7861. Those processes are outside this lane. Prior 5202/8821 rehearsal used `dmb_world_plan_demo` on `dmb-world-plan-pg-test` at 55441; graph authority was unset and projection returned 503. This is historical configuration, not a current runtime claim. PRIME/designated host owner must authorize one targeted live witness with exact worktree/ref, UI/API pair and disposable DB identity. No duplicate servers, shared DB edits or graph writes in this shell slice.

No conversational Agent turn/UI changes here. Agent UI integration across Index, Plan, Play, Build, Ingest and Combat is the separate next capability; surface publication alone proves no conversation. No source admission, graph confirmation/read-after-write, statblock/image, Run, or persistence contract changes. Full Of Conks mission remains active.

## §6 Host behavior and stale-command rules

- Publish one complete surface publication and one `AppChromeToolsGeneration`; `editorTools.target` exactly matches `publication.canvas.workObject`. Do not fall back to a blank/generic target.
- `WorldPlanSurfaceContext` retains the existing Plan selector and New blank. In the singular EditHost, expose title editing as its rich section panel, Save as a pinned action, and existing formatting/registered insertion groups. Remove their duplicate inline controls from the center. Keep the canvas for the parchment document and semantic registered components.
- Recovery states (uncertain create, preserved orphan draft, revision conflict, failed load/save) remain visible on the page with their current actionable recovery. Developer identity/revision/provenance details stay collapsed and secondary.
- Each action checks current-at-click World, encoded work target, mounted selection epoch, editor generation and current editor ref before invoking. A retained callback cannot rely on captured Editor alone. Invalidate old inventory on World/Plan selection, New blank, local→saved promotion and unmount, using the existing publisher bind/update lifecycle.
- Loading/error, absent editor and saving yield honest disabled actions/reasons. Save preserves all existing guards for uncertain creation, orphan recovery, conflict and nonempty content. Editing preserved local text remains limited to the current ready editor and cannot bypass a Save/recovery guard. Do not alter existing persistence or recovery semantics.

## §7 Required proof after activation

The new mounted test exercises real provider → Plan publication → AppChrome → EditHost. Prove:

1. Exact World/saved-document identity and exactly one matching inventory; unique persisted local token per World/draft; local→saved promotion; New blank creates a fresh identity.
2. Global navbar and existing `WorldPlanSurfaceContext` selector/New remain usable. Title, Save, formatting and insertion are in EditHost once and absent from central canvas. Recovery stays visible/actionable.
3. Loading, error, no editor, saving, uncertain create, recovered orphan and conflict states have truthful availability, with existing persistence tests still proving save/reload/CAS/recovery.
4. Held callbacks after document switch, World switch, New blank, promotion and unmount do not mutate/focus a replacement editor. Current actions operate on the current editor only. Delayed save completion remains fenced.

Then obtain one real amended-product witness at desktop and 390×844 on blank and authored content, after runtime owner approval: exact World/Plan identity, boundary and control placement visible, recovery visible, no horizontal overflow/console errors, no model or graph writes. Prior six visual cases are historical only. Run focused owning tests, relevant Campaign Plan compatibility and scoped UI checks; report inherited build failures exactly. Request PRIME review of the exact cumulative amended head. This slice does not prove multi-turn Agent, full journey or operator acceptance.

## §8 Pre-dispatch critique, state sync and handback

- **Merge-ready invariant:** one current work identity governs page/context/host/actions.
- **Most likely failure:** retained callback or delayed save crosses identity replacement; §7 explicitly exercises both.
- **PR topology:** serial amendment of existing #793 to preserve its visual code/evidence under one review; no extra implementation PR.
- **Stop/split:** any shared host/provider contract change, inability to match current target, second inventory, or a need to alter Plan persistence.
- **State sync:** the implementation PR updates this handoff and the sole roadmap with completed predecessor dispositions known at that time. PRIME authorized the owner transfer after #794 merged; the steward handoff records it in this same implementation PR. Never claim current work complete or invent future merge/review facts.
- **Return:** exact base/head, cumulative paths, focused and mounted-boundary evidence, authorized runtime/database identity, actual rendered operator disposition, remaining blockers and next connected user action.

## §9 Acceptance boundary

J2 shell adoption is one repaired transition. Full DEMO still requires fresh native Of Conks World → blank Plan → author/import → prepare/explicitly confirm graph knowledge → ordinary Agent retrieval → statblock/image preparation → run with Plan/choices/NPCs/statblocks/combat/roll results → restart/resume. Require two resettable full journeys, real generation, graph read-after-write and saved run state, then explicit operator acceptance. Tests and screenshots cannot substitute for those gates.
