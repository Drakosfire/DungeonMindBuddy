---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J2 — World Plan shell adoption
  - Flow: DEMO
  - Direction: STEWARD → CODE → PRIME
  - Handoff: `Docs/Plans/HANDOFF-DEMO-world-plan-shell-adoption-v1.md`
  - Topology: serial; amend existing #793
  - Accepted design head: `5a44f42041415dea783e3082e504a185f2e241c7`
  - Implementation: PR #793, branch `codex/demo-j2-plan-canvas-visual-impl`

  ## Verification pointer
  - Base: `main@ebfc22ad8c5797d033029c4e0ee2ca098595632c` (merged #797); current implementation head before this state sync: `51da734df050ab062613941f8d700c83a25abffe`
  - Focused Plan/editor-host suite: 122 passed in serial execution after the EditHost title-style repair; cumulative diff-check passed. The exact route's post-#797 pointer witness remains pending.

  Prior #793 visual witness is historical evidence for that exact implementation, not acceptance of shell adoption.
---
# HANDOFF — World Plan adopts Buddy's established editing shell

**Created:** 2026-09-29
**Status:** ACTIVE — PRIME DESIGN PASS on exact head `5a44f42041415dea783e3082e504a185f2e241c7`; #793 amendment is the sole serial implementation lane.
**Workstream / owner:** DEMO / World Plan composition
**Design authority:** accepted design head `5a44f42041415dea783e3082e504a185f2e241c7`, authored against main after #794/#795. Current implementation base is `main@ebfc22ad8c5797d033029c4e0ee2ca098595632c`; the reviewed implementation-code head before this state sync is `51da734df050ab062613941f8d700c83a25abffe`. The PR body records the exact head after the documentation sync.
**Topology:** serial amendment of #793 only. No successor PR.
**PR title:** `DEMO: adopt the World Plan editing shell`
**PRIME:** owns review, predecessor disposition and merge.

## §1 Mission and invariant

A GM authors a World-owned Plan in Buddy's clean central canvas while existing navigation and EditHost provide document and editing controls.

**Merge-ready invariant:** the selected World Plan surface, canvas work object, and singular AppChrome editing inventory always name the same exact World/work object. Commands resolve the editor and selection at invocation; they become inert when the selection, editor generation, save promotion or mounted surface is no longer current. Recovery stays visible and actionable.

One invariant covers blank, saved, switching, recovery and async-completion paths: the current World Plan work identity gates every control and editor intent. The easiest boundary to miss is mounted `AppChrome`/`EditHost`; existing `PlanSurfacePage.test.tsx` mocks AppChrome and cannot prove it. The adversarial sequence is hold an EditHost callback, switch document/World, reset to blank or promote by Save, then invoke it or finish an old async save. The new §7 test detects it.

## §2 Re-anchored authority and lane

- `AGENTS.md`, amended DEMO mandate in #794 and `Docs/Roadmaps/ROADMAP-demo.md` govern. Current `main` is `ebfc22ad8c5797d033029c4e0ee2ca098595632c`; #794 merged at `374d69d78ef58a062116de73e095b57f4a92ca15`, #795 policy cleanup at `83f25b1f9bfe70555a82b08ef4f5ca5af26a691d`, #796 preceded the current base, and #797 merged at current `main`. PRIME selected amendment of #793; reviewed code head before this state sync was `51da734df050ab062613941f8d700c83a25abffe` on `codex/demo-j2-plan-canvas-visual-impl`, merged with current `main` without rewriting history. The PR body records the exact head after the documentation sync. PRIME owns review, predecessor disposition and merge.
- Incoming DEMO task: `01a0edf2-b1e1-7281-9448-1d5524f8d4f8`. PRIME retired archived outgoing task `01a0885e-375c-7501-9f6e-a58528b39894` from DEMO implementation/design/runtime mutation. It was not restarted and did not acknowledge handback. `Docs/Plans/STEWARDS-HANDOFF-demo.md` now names the incoming task as owner under PRIME's explicit transfer authorization; its mission is unchanged. Preserve its refs/drafts as read-only evidence; do not claim its tool-backed goal state is known.
- The shell-adoption implementation is active in the sole serial #793 lane under the §4 write lease. The detached user checkout stays off `main`; no successor implementation lease is active. Keep shared shell contracts and runtime/DB state outside this lease.
- PRIME explicitly authorized the incoming owner-field update in `Docs/Plans/STEWARDS-HANDOFF-demo.md` after #794 merged. This assigned PR carries that backward-looking transfer with the roadmap and this handoff; the mission is unchanged.
- Separate open PRs #781 and Rules #763–#765 have distinct owners; recheck refs and active leases before dispatch.

## §3 Observable paths and identities

| Path | Required result | Owner |
|---|---|---|
| Blank Plan | Existing global navbar and `WorldPlanSurfaceContext` remain; a unique World-scoped local draft identity is published to canvas, context and EditHost. | World Plan |
| Saved Plan | Publish literal verified server-issued World ID (opaque string, not necessarily UUID-shaped) and exact saved document ID/revision; matching editor inventory uses the same work-object target. | World Plan |
| New blank / World or document switch | New target cannot alias another World/document; prior callbacks are invalid immediately. | Plan page/context |
| Save promotion | On returned document ID, transition canvas/context/inventory together from local token to saved identity; invalidate held local callbacks. | Plan save controller |
| Loading, failure or recovery | Honest disabled reason; visible recovery actions remain bound to the selected recovery state; existing save/conflict/CAS behavior remains. | Existing controller |
| Late completion / unmount | Existing selection-epoch fences prevent a displaced async write from mutating replacement UI. | Plan page |

Treat World IDs as opaque server-issued strings; never assume UUID format or validate by shape. Use the literal verified World ID and exact server-issued document ID. Use saved work kind `world-plan-document`, target id structured as JSON tuple `("world-plan-document", worldId, documentId)`. Use local kind `world-plan-local-draft`, id tuple `("world-plan-local-draft", worldId, localDraftToken)`. Add an optional `local_draft_id` field only to the existing browser-local `dmb_plan_promotion_recovery_v2` record; do not change server persistence or CAS. Mint and persist a collision-resistant token once per World draft, retain it through edits/reload and backward-compatible recovery, and replace it on deliberate New blank. Existing records without the field are migrated in place by materializing a token while preserving title, Markdown, World/document identity, revision, edit generation, pending write and uncertain/orphan recovery fields. Never derive identity from title/content. World is part of all target tuples.

The canvas work object, `WorldPlanSurfaceContext` instance identity and `AppChromeToolsGeneration.target` must encode the same tuple. Its selected Plan context carries literal World/document identity; no campaign/session aliases. Keep revision, edit generation, selection epoch, editor generation and local token as separate lifetimes. Save promotion changes the shared work-object identity atomically after the exact server document id exists. Invalidation follows World/document/local-draft/host ownership replacement, not ordinary caret or text selection movement; formatting resolves TipTap’s current caret selection when clicked against the current editor.

## §4 ACTIVE implementation write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx` | Publish exact surface/work object; provide one matching AppChrome inventory; move title, pinned Save, format and insert actions to established hosts; remove duplicate inline controls; preserve visible recovery and callback guards. |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceContext.tsx` | Add local draft identity to the existing World Plan surface instance key, matching publication target. Preserve selector/New control and existing context host. |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx` | Keep persistence, promotion, uncertainty and conflict regression coverage. |
| Create | `apps/live-control-ui/src/planSurface/PlanSurfacePage.editHost.test.tsx` | Mount real AgentInteractionProvider, selected World, AppChrome and EditHost; prove the §7 mounted boundary. |
| Modify only if needed | `apps/live-control-ui/src/styles.css` | Remove obsolete inline-control placement rules while retaining #793 canvas/page styles. |
| Preserve | `Docs/Plans/HANDOFF-DEMO-J2-plan-canvas-visual-acceptance-v1.md` | Existing #793 visual evidence; historical witness only, unchanged in this shell slice. |
| Preserve | `Docs/Plans/HANDOFF-DEMO-J2-world-plan-canvas-composition-v1.md` | Existing #793 design record; unchanged in this shell slice. |
| Preserve | `apps/live-control-ui/src/tiptap/prepMarkdownThemes.css` | Existing #793 canvas theme implementation; unchanged in this shell slice. |
| Modify | `Docs/Plans/HANDOFF-DEMO-world-plan-shell-adoption-v1.md` | Dispatch facts/evidence, without pre-marking completion. |
| Modify | `Docs/Plans/STEWARDS-HANDOFF-demo.md` | Record the PRIME-authorized incoming owner transfer; preserve mission and scope. |
| Modify | `Docs/Roadmaps/ROADMAP-demo.md` | Material predecessor sync, owner/next action and connected milestone state. |

No neutral publisher/provider/lease, AppChrome/EditHost implementation, global nav, shared context-host contract, API/persistence, graph or other repository paths are leased. If required, stop for owner review and an explicit lease amendment. Existing `WorldPlanSurfaceContext` and global navbar are reused. Do not add a second navigation bar or duplicate context.

## §5 Runtime and product boundary

The post-#796 exact-head witness ran on the authorized isolated UI 5202/API 8821 pair at PR #793 head `a9426d244af3d60b9b630a6e382f6b31c4c28b4e`, using disposable APP-STATE database `dungeonbuddy_application_state_of_conks_demo`; World Graph authority was unset and untouched. Through the product UI it created fresh native World `of-conks-plan-shell-witness-2026-09-29` (display name “Of Conks Plan Shell Witness 2026-09-29”), opened a blank Plan, authored “The First Bell at the Tollhouse” with body “At dusk, a single bell answers from the old tollhouse.”, saved document `bb116c42-8862-4c28-b379-831871b48dc0`, and reloaded the exact World/document URL with title and body intact. APP-STATE create/read/write/snapshot calls returned 200. Desktop 1440×900 showed global nav, World Plan selector, EditHost and paper canvas. At 390×844 the saved title/body fit without horizontal overflow, but after closing EditHost a real pointer tap on the visible Edit launcher at x=18,y=721 did not reopen it. The transparent `.app-edit-toolbox-backdrop[hidden]` covered the launcher because the mobile rule then forced it to `display:block !important`. Interaction Map fixed this shared shell defect in PR #797, merged to current `main` at `ebfc22ad8c5797d033029c4e0ee2ca098595632c`. That code-level fix does not replace a post-merge pointer witness on this exact Plan route; it is authorized and pending below.

Automatic graph-projection requests returned 503 because `DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL` was unset; the World badge reported attention. Automatic source-bundle reads for `campaign-ingested&campaign_id=longmont-c2` returned 200, but are unrelated to Of Conks and are not evidence of retrieval. No graph knowledge was prepared or confirmed, no Graph/model write occurred, and the Of Conks source was not admitted in this witness. The API log showed only expected Plan and World routes plus those automatic requests; the UI emitted a Vite/Babel large-file notice. These facts do not establish client error-free acceptance, graph read-after-write, multi-turn Agent behavior, or operator acceptance. I stopped only the two UI/API sessions launched for that witness; the database container/volume were left running. During the earlier sandboxed run, host socket inspection was unavailable. PRIME later verified ports 5202/8821 have no listeners and authorized one exact-route replay after both DB targets match. Current read-only environment inspection shows APP-STATE database `dungeonbuddy_application_state`, not the authorized witness database `dungeonbuddy_application_state_of_conks_demo`; `pg_isready` reports no response on either APP-STATE port 54331 or separate Graph authority port 54330. No new UI/API process was started and no database, source, corpus or graph data was read or changed. Wait for PRIME/designated database owner to resolve the target mismatch and service availability before continuing the witness.

No conversational Agent turn/UI changes here. Agent UI integration across Index, Plan, Play, Build, Ingest and Combat is the separate next capability; surface publication alone proves no conversation. No source admission, graph confirmation/read-after-write, statblock/image, Run, or persistence contract changes. Full Of Conks mission remains active.

## §6 Host behavior and stale-command rules

- Publish one complete surface publication and one `AppChromeToolsGeneration`; `editorTools.target` exactly matches `publication.canvas.workObject`. Do not fall back to a blank/generic target.
- `WorldPlanSurfaceContext` retains the existing Plan selector and New blank. In the singular EditHost, expose title editing as its rich section panel, Save as a pinned action, and existing formatting/registered insertion groups. Remove their duplicate inline controls from the center. Keep the canvas for the parchment document and semantic registered components.
- Recovery states (uncertain create, preserved orphan draft, revision conflict, failed load/save) remain visible on the page with their current actionable recovery. Developer identity/revision/provenance details stay collapsed and secondary.
- Each action checks current-at-click World, encoded work target, mounted selection epoch, editor generation and current editor ref before invoking. A retained callback cannot rely on captured Editor alone. Invalidate old inventory on World/Plan selection, New blank, local→saved promotion and unmount, using the existing publisher bind/update lifecycle.
- Loading/error, absent editor and saving yield honest disabled actions/reasons. Save preserves all existing guards for uncertain creation, orphan recovery, conflict and nonempty content. Editing preserved local text remains limited to the current ready editor and cannot bypass a Save/recovery guard. Do not alter existing persistence or recovery semantics.

## §7 Required proof and current evidence

The new mounted test exercises real provider → Plan publication → AppChrome → EditHost. Prove:

1. Exact opaque World/saved-document identity and exactly one matching inventory; unique persisted local token per World/draft; local→saved promotion; New blank creates a fresh identity. Migrate an old v2 local record without `local_draft_id` while retaining all content/pending/recovery fields, then reload and confirm the same token.
2. Global navbar and existing `WorldPlanSurfaceContext` selector/New remain usable. Title, Save, formatting and insertion are in EditHost once and absent from central canvas. Recovery stays visible/actionable.
3. Loading, error, no editor, saving, uncertain create, recovered orphan and conflict states have truthful availability, with existing persistence tests still proving save/reload/CAS/recovery and local-identity migration/recovery reload.
4. Held callbacks after saved-document replacement, World switch, New blank, local→saved promotion and unmount do not mutate/focus a replacement editor. Current actions operate on the current editor only. Delayed save completion remains fenced. The mounted regression retains the actual published “Read aloud” EditHost command across each ownership change and proves it neither alters editor markup nor moves focus.


The focused Plan/editor-host suite was rerun after the title-style repair and #797 re-anchor: serial execution passed 122/122 across `PlanSurfacePage.editHost.test.tsx`, `PlanSurfacePage.test.tsx`, `PlanSurfaceShell.test.tsx` and `EditHost.test.tsx`. The merged base includes #797's stylesheet and visual-contract changes. `git diff --check origin/main...HEAD` passed. The exact route's post-#797 desktop and 390×844 pointer witness is still pending runtime target verification below.

The following commands remain useful for full local verification after any code change (the mounted test is already present):

```bash
npm --prefix apps/live-control-ui test -- --maxWorkers=1 src/planSurface/PlanSurfacePage.editHost.test.tsx src/planSurface/PlanSurfacePage.test.tsx src/planSurface/PlanSurfaceShell.test.tsx src/surfaceInteraction/editHost/EditHost.test.tsx
npm --prefix apps/live-control-ui run typecheck
npm --prefix apps/live-control-ui run build
git diff --check origin/main...HEAD
```

With PRIME's runtime authorization, rerun the exact saved World/Plan route at desktop and 390×844: verify title styling, exact World/Plan identity, EditHost placement, recovery visibility, canvas fit, and physical Edit close/reopen taps with no console errors or model/Graph writes. Validate the APP-STATE DB and separate Graph authority targets before startup; do not create/delete databases or start duplicate services. Current preflight found APP-STATE configured for database `dungeonbuddy_application_state`, while the prior witness and PRIME's authorization name `dungeonbuddy_application_state_of_conks_demo`; no service was started. Wait for PRIME to resolve this identity mismatch. Prior six visual cases remain historical. Report unavailable checks and inherited build failures exactly. Request PRIME review of the exact cumulative amended head. This slice does not prove multi-turn Agent, full journey or operator acceptance.

### Current implementation evidence (2026-09-29)

- PR #793 is based on `ebfc22ad8c5797d033029c4e0ee2ca098595632c`; reviewed code head before this state sync was `51da734df050ab062613941f8d700c83a25abffe`. The preserved implementation sequence merges current main without rewriting history. The PR body records the exact post-sync head.
- The focused four-file command completed with **122 passed** after the title-style repair. The earlier parallel timeout is historical and was cleared by serial reruns.
- The real AppChrome/EditHost tests verify opaque World identity, fresh empty-storage token creation/persistence through first edit and reload, legacy local-draft migration/reload, actionable visible recovery, one matching edit inventory, and local-token → exact server-document promotion across publication identity and commands.
- Cumulative `git diff --check origin/main...HEAD` passes against the current base/head. The exact-tree typecheck remains blocked by inherited `ThreatPublicationPanel.tsx(553,77): TS2503 Cannot find namespace 'JSX'`. The mounted test now retains a real EditHost command across saved-document replacement, promotion, saved-document→blank, World replacement and unmount, proving no replacement-editor mutation or focus theft. The title input label/focus styles now target its EditHost location, and dead inline-toolbar rules are removed. The exact-route post-#797 pointer witness and runtime database-target match remain open; full connected DEMO acceptance remains open.
- PRIME Cycle 1 HOLD at `51da734df050ab062613941f8d700c83a25abffe` confirmed the held-command implementation and identified the moved title label/input/focus selectors still scoped beneath the old canvas ancestor. This sync moves those styles to EditHost and removes obsolete inline-toolbar rules. PRIME also authorized the exact-route post-#797 pointer witness after verifying 5202/8821 are unowned; runtime startup remains gated by the APP-STATE DB identity match above.

## §8 Pre-dispatch critique, state sync and handback

- **Merge-ready invariant:** one current work identity governs page/context/host/actions.
- **Most likely failure:** retained callback or delayed save crosses identity replacement; §7 explicitly exercises both.
- **PR topology:** serial amendment of existing #793 to preserve its visual code/evidence under one review; no extra implementation PR.
- **Stop/split:** any shared host/provider contract change, inability to match current target, second inventory, or a need to alter Plan persistence.
- **State sync:** the implementation PR updates this handoff and the sole roadmap with completed predecessor dispositions known at that time. PRIME authorized the owner transfer after #794 merged; the steward handoff records it in this same implementation PR. Never claim current work complete or invent future merge/review facts.
- **Return:** exact base/head, cumulative paths, focused and mounted-boundary evidence, authorized runtime/database identity, actual rendered operator disposition, remaining blockers and next connected user action.

## §9 Acceptance boundary

J2 shell adoption is one repaired transition. Full DEMO still requires fresh native Of Conks World → blank Plan → author/import → prepare/explicitly confirm graph knowledge → ordinary Agent retrieval → statblock/image preparation → run with Plan/choices/NPCs/statblocks/combat/roll results → restart/resume. Require two resettable full journeys, real generation, graph read-after-write and saved run state, then explicit operator acceptance. Tests and screenshots cannot substitute for those gates.
