---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J1
  - Direction: STEWARD → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DEMO-selected-world-context-v1.md
  - PR topology: serial

  ## Review contract
  Prove that one selected, server-verified World identity follows the imported
  source through Build, Graph Review, Plan, Ask and World reads. Preserve C1/C2.
  The exact handoff, cumulative diff and owning-boundary evidence govern review.
---

# HANDOFF — DEMO: one selected World context

**Created:** 2026-09-26
**Status:** ACTIVE — J1 selected-World context repair
**Canonical path:** `Docs/Plans/HANDOFF-DEMO-selected-world-context-v1.md`
**Flow / owner:** DEMO / Buddy product integration
**Design base:** `main@1ced31f774d62802893d46670eecebe91d37df60`; re-anchored after #772 at `397e60791f938a4662f134dbf8e11538f61cb51d`
**Activation gate:** none; J1 browser failure recorded in `ROADMAP-demo.md`
**Dispatch base:** fresh `main` containing this handoff; record exact SHA in PR
**PR topology:** serial; no other open DEMO implementation PR
**Authorized PR:** open/update one PR titled `DEMO: carry one selected World across preparation`
**Suggested branch:** `codex/demo-selected-world-context`
**No successor authorization:** a discovered extraction, publication, Play or generic-lens redesign is a stop/handback, not a second PR.

## §1 Mission and invariant

After importing an authored source into a managed World, the GM can navigate to
Plan, create/reopen an editable prep in that same World, and see the same World
identity in Build references, Graph Review, shared World status, Plan projection
and Plan Ask. The context is a **selection over existing authorities**, not a
new store of graph truth.

**One merge-ready invariant:** every claimed surface derives the selected
`world_id` and campaign scope from one verified context binding. An exact
source/document selection cannot silently fall back to Longmont C2 or
Eldyrwild. Missing/mismatched identity and a World with no published head stay
visible, non-mutating states. Existing C1/C2 selection and focused/union graph
behavior remain intact.

Pre-dispatch critique:

| Question | Answer |
|---|---|
| One invariant? | Yes: selected World identity and scope are coherent across the J1 transition. |
| Adversarial sequence | Import W → navigate Plan → stale C2 default → create prep or Ask under C2. |
| Owning proof | Browser flow plus Plan route/service, context resolver and graph-request tests. |
| Easy-to-miss boundary | Plan's legacy `plan-view` and Hermes `/query` both load the C2 live packet; changing a badge or nested graph request cannot change document/Ask authority. |
| Stop/split | A new DungeonMind/WorldKeeper contract or a generic extraction/Play redesign is required. |

## §2 Authority, topology and runtime

- Parent authority: `Docs/Plans/STEWARDS-HANDOFF-demo.md` and sole mutable
  `Docs/Roadmaps/ROADMAP-demo.md`. Exact J1 source/run IDs and failure are in
  that roadmap. #773 is merged; Rules #763 owns dependency files. Open #772
  owns process/AGENTS only; #760/#761 are blocked UI design and not leases here.
- Exact input: `WorkspaceDocumentRecord.document_id/campaign_id/world_id`,
  validated managed `WorldContainerRecord`, exact first-World run lineage and
  optional native World revision. C1/C2 continue through their accepted
  `longmont-c1|c2 → eldyrwild` mapping.
- Output: one typed, read-only selected-context result for Buddy consumers;
  a Plan document under the selected managed World; graph/Ask requests with
  the same world/campaign identity. Do not introduce a new durable authority.
- Managed Plan Ask must cross the existing Hermes runtime without loading the
  legacy C2 packet. Its minimal request packet may carry the verified managed
  campaign and the selected Plan document's *target* session as transport
  identity; it must contain no invented session events, state, or recap facts.
  Ask remains disabled without a selected durable Plan document and native
  World head. Existing C1/C2 `/query` behavior is unchanged.
- Explicitly false afterward: candidate publication, extraction quality,
  beats/encounters, Plan→Play Run creation, and final DEMO acceptance.
- Runtime lease: use the existing isolated Of Conks DB pair and ports 8812/5192
  for live witness; do not mutate C1/C2 or another lane's runtime. The licensed
  source root under `corpus/of-conks-cons-demo-markdown/` is local-only and must
  never be staged or committed. No model call is needed; replay the saved run.
- State-authority sync: this handoff and `ROADMAP-demo.md` plus its active
  mirror may record already-completed predecessor facts, not pre-mark this PR
  accepted. After review/merge, guarded steward sync records exact merge and
  the next J1 frontier.

## §3 Observable paths

| Path | Required behavior |
|---|---|
| Build source W → Plan nav | Carry a verified W selection; no C2 default. |
| Plan with W selected | Show W, create/reopen W-scoped prep, and preserve exact document identity on reload/navigation. No invented live-session facts. |
| Plan Ask and graph read | Use W/campaign W with no C2/Eldyrwild request. Before W initialization, truthfully unavailable rather than another World's answer. |
| Build World references and chrome | Use W when source record says W. Before publication, say not initialized; after publication, read W. |
| Graph Review exact run | Retain artifact/source/world binding; never infer W from display label or selected C2 lens. |
| C1/C2 | Existing campaign/union/focus and document selection behavior unchanged. |
| Tampered URL/document | Mismatch/unknown World fails closed; no Plan creation, Ask or graph query under fallback identity. |

The implementation may use a URL selection plus server-owned world-container and
exact document validation. A URL, local-storage value or display label alone is
not authority. If navigation has no managed selection, the existing C2 default
may remain; an explicit but invalid managed selection must **not** fall back.

## §4 Files in scope — ACTIVE write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/selectedWorld/**` | One resolver/provider and focused tests. |
| Modify | `apps/live-control-ui/src/App.tsx`, `apps/live-control-ui/src/App.test.tsx` | Install verified selection before shared consumers. |
| Modify | `apps/live-control-ui/src/chrome/AppChrome.tsx`, `apps/live-control-ui/src/chrome/AppChromeWorldGraphStatus.tsx` and focused tests | Carry selected context through nav and status. |
| Modify | `apps/live-control-ui/src/graphLens/sessionCampaignContext.ts`, `apps/live-control-ui/src/graphLens/WorldGraphLensContext.tsx`, `apps/live-control-ui/src/graphLens/worldGraphContextFromLens.ts`, `apps/live-control-ui/src/graphLens/useWorldGraphLensProjection.ts`, `apps/live-control-ui/src/graphLens/GraphLoadPanel.tsx` and focused tests | Extend the existing lens to verified managed-world selection without changing C1/C2 meaning. |
| Modify | `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts` and focused tests | Exact request mapping and fail-closed managed-world admission. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx`, `apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.tsx`, `apps/live-control-ui/src/buildSurface/reference/useBuildWorldGraphProjection.ts` and focused tests | Consume selected context in Build; no unknown-scope false failure. |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`, `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx`, `apps/live-control-ui/src/planSurface/config/planSessionDescriptor.ts`, `apps/live-control-ui/src/planSurface/reference/planGraphContextRequest.ts`, `apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx` and focused tests | Bind Plan document and Ask to selected W. |
| Modify | `apps/live-control-ui/src/api/liveApi.ts`, `apps/live-control-ui/src/api/types.ts` | Optional validated managed-world Plan projection request/DTO. |
| Modify | `apps/live_control_server/routes/live.py` and focused route tests | Ground Plan's managed-world context in server-owned registry; retain legacy default. |
| Modify | `apps/live_control_server/services/live_agent_loop.py` and focused service tests | Accept a route-validated, minimal managed-World Hermes packet without loading C2; no change to legacy live/Hermes behavior. |
| Modify | `Docs/Roadmaps/ROADMAP-demo.md`, `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md` | Backward-looking evidence only. |

**2026-09-26 steward rebrief:** tracing `/query` showed that the old server
requires the loaded C2 packet before interpreting nested graph context. The
service path above is included explicitly so the implementation cannot use a
C2 packet as a managed-World workaround. This is the same selected-context
capability and the existing Hermes wire contract, not a new query API.

**Bounded discovery:** up to 8 additional focused tests or immediate
presentation adapters under the listed frontend directories, only when the
listed consumer cannot compile/prove §1 without them. Name each in the PR
handback. No additional production route, registry, schema, migration, package
or lockfile without steward rebrief.

## §5 Explicit exclusions

No edits to `pyproject.toml`, `uv.lock`, DungeonMind/WorldKeeper, APP-STATE
schema, extraction profiles/prompts, candidate graph, first-World
prepare/confirm semantics, Play/Run/Combat, generic search, Canvas, UI theme,
licensed source Markdown or C1/C2 authority data. Do not publish all 63
candidate changes to make a green demo. First-World review remains an explicit
governed human-facing step.

## §6 Contract and failure behavior

```text
exact selected document + managed-world registry / legacy campaign mapping
→ verified SelectedWorldContext (world, campaign, selection provenance)
→ existing Plan, Build, Graph Review, World-lens and Ask consumers
```

| Input/state | Result |
|---|---|
| No explicit managed selection | Legacy C2 default unchanged. |
| Valid W + matching document | W context; Plan may create W-scoped prep; all graph/Ask requests use W. |
| Valid W, no graph head | Plan authoring remains usable; graph/Ask truthfully unavailable. |
| Unknown W or document/W mismatch | Visible error; no C2 fallback or cross-World request. |
| Route to another known World | In-flight old projection/Ask must not be accepted as new World result. |
| C1/C2 focus/union | Same requests and labels as base. |

Selection is not publication authority. The managed-world record proves that W
is an admitted Buddy destination; only native DungeonMind revision/receipt
proves published graph content. A candidate preview does neither.

## §7 Merge evidence

| Guarantee | Owning proof |
|---|---|
| Verified W and fail-closed mismatch | Pure resolver tests + Plan route/service tests with unknown W and document mismatch. |
| Plan create/reopen under W | Plan surface integration test, not helper-only. |
| Build/Graph Review/Plan/Ask one context | App/surface integration test asserting exact requests and no C2/Eldyrwild call. |
| No head is honest | Test native missing-head response; no stale projection or enabled graph answer. |
| C1/C2 preserved | Existing graph lens, Build, Plan, Ingest tests. |
| Real product | Rehearse saved Of Conks source/document and exact extraction run on isolated ports; W Plan editable, C2 absent, first-World candidate still unconfirmed. |

Run focused Vitest and server tests, frontend typecheck/build, scoped Ruff,
`git diff --check`, and compare changed paths to §4. If inherited full-build
failures remain, show the same command/base failure and the exact changed-file
scope. No paid extraction rerun is acceptance evidence for this PR.

## §8 Review handback and acceptance

Give PRIME and the code reviewer: PR URL, exact head/base, handoff path, changed
paths/lease audit, test commands/results, browser witness, saved source/run
identities, explicit non-publication, inherited failures, and any stop/follow-up.
The only merge-ready claim is the §1 selected-context invariant; J1/J2–J6 and
the full demo remain open.

- [ ] Handoff was on `main` and ACTIVE before implementation branch.
- [ ] One selected World governs all claimed paths; mismatches fail closed.
- [ ] Managed-world Plan create/reopen and uninitialized graph behavior proven.
- [ ] Existing C1/C2 behavior proven unchanged.
- [ ] Exact-head tests and browser witness recorded; no model calls.
- [ ] Only §4 paths changed; licensed source remains untracked/local.
- [ ] Independent review passes before merge.

## Stop conditions

Stop/rebrief if this requires a new public durable context store, a new
DungeonMind/WorldKeeper rule, a second implementation PR, a path outside §4, a
conflicting active lease, a generic rewrite of all review campaigns, or if the
Plan/Ask behavior cannot share one verified W without inventing session facts.
