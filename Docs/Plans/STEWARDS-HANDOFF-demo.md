# Steward handoff — DEMO, from preparation to a resumable session

**Status:** ACTIVE mandate; fresh DEMO task pending operator creation after the 2026-09-29 reboot  
**Owner:** the next operator-created DEMO task. The prior DEMO tasks `01a0885e-375c-7501-9f6e-a58528b39894` and `01a0edf2-b1e1-7281-9448-1d5524f8d4f8` retain history only; PRIME has frozen their #793 implementation and runtime authority.  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Mandate amended:** 2026-09-29 — fresh DEMO transfer, three bounded World Plan slices and PRIME model routing
**Execution state:** [ROADMAP-demo.md](../Roadmaps/ROADMAP-demo.md) only  
**Transfer evidence:** [reconciliation report](../Reports/REPORT-DEMO-roadmap-reconciliation-2026-09-26.md)

## Mission

Own the complete requested Buddy demonstration until the operator accepts it:

> Import parsed adventure/session Markdown; plan with an agent writing prose and
> registered components onto the surface; inspect and author graph nodes/edges;
> query the new knowledge; develop, generate, review and edit a statblock; generate
> and select its image; run the prepared session with fast access to plan, choices,
> NPCs, statblocks, combat and recorded roll-table results; restart and resume.

The steward is accountable for the connected experience, not for reporting that
its pieces exist. Preserve the full requested journey. Reduce corpus size and
number of examples before dropping a requested capability.

## Required Surface experience

The Surface architecture already gives navigation, tools, editing and the Agent
established homes. Inspect and adopt those capabilities before inventing new UI.
Every navigable surface uses the global navbar and composable/configurable
surface-specific subnav. World/document context belongs in that context area;
node search stays in its existing toolbar. Formatting and component insertion
belong in the existing edit host; tools belong in the existing tool host. Preserve
the central space as a clean content canvas. Place advanced developer/agent
metadata in collapsed details. Keep actionable errors and recovery decisions
visible where the user can resolve them.

A surface-aware conversational Agent on Index, Plan, Play, Build, Ingest and
Combat is a minimum. Each turn must truthfully identify the current World,
surface, work object/document and selection when present, with honest absence
when unavailable. Prove actual multi-turn conversation through the accepted
backend; publishing a surface interaction context alone does not establish Agent
turn integration. Advanced Agent authoring, generation and mutations follow this
baseline and remain part of the full mission where required above.

Navigation must preserve the same authoritative identities and project the same
underlying data through each relevant surface. Presentation consumes existing
controllers/contracts; it must not create competing stores of graph truth.
Document drafts, accepted graph knowledge and mutable Run state retain their
actual ownership. A fresh blank World must be usable before campaign, corpus or
published graph-head existence.

## Immediate delivery order and sequencing

The operator ended broad Buddy PR [#793](https://github.com/Drakosfire/DungeonMindBuddy/pull/793) unmerged on 2026-09-29. Its exact source head `e122c7073ba8c79dcd428b608da5c8e92bc53abb` remains on `codex/demo-j2-plan-canvas-visual-impl`; it is reference material, not an active write lease or merge candidate. The previous DEMO task froze edits. Its local untracked Of Conks corpus remains with that checkout and must not be copied into a PR.

The operator approved three smaller serial implementation slices. Refresh remote `main` and open PRs before each branch; the takeover snapshot was `main@ebfc22ad8c5797d033029c4e0ee2ca098595632c`. Preserve a recoverable source snapshot and extract only the intended hunks from #793. Each slice gets its own bounded ACTIVE handoff, path/runtime lease, owning-boundary tests, cumulative review, and PR. Do not reopen #793 or carry its long evidence/history documents wholesale.

1. **Plan document-switch safety:** prevent the outgoing editor from accepting/persisting input while a different saved Plan loads. A delayed-snapshot mounted regression must prove the old draft and incoming document stay intact. This bug exists on accepted `main`; it is independent of #793's shell work.
2. **Exact World Plan identity:** publish one saved-document or uniquely identified World-scoped local-draft work object through the existing surface/context seam. Prove old local-draft migration, reload stability, World/document replacement and local-to-saved promotion with mocked API/mounted tests. Keep server document identity, local token, revision and editor generation distinct. Shared publisher/host contracts stay read-only.
3. **EditHost controls:** consume the identity from slice 2 to put title, Save, formatting and insertion in the established AppChrome/EditHost, removing duplicate inline controls. Prove one matching inventory, current-at-click targeting and inert held callbacks after document/World/draft replacement, save promotion and unmount. Include a mobile close/reopen click witness with mocked APIs; an unavailable database is not a prerequisite for this bounded UI behavior.

Slice 3 depends on slice 2. The switch-safety fix is independent and should land first to avoid overlapping edits to `PlanSurfacePage.tsx`. Keep the existing canvas theme and visual styling from #793 parked on its preserved branch. A separate visual PR needs a fresh appearance decision and operator acceptance; it does not block the three functional slices.

After these bounded repairs, adopt the shared conversational Agent UI with truthful per-turn context on Index, Plan, Play, Build, Ingest and Combat, then resume the full connected fresh-World rehearsal. The rehearsal's isolated database pair is separate from the persistent `54330`/`54331` targets; the prior #793 live witness remained blocked on unavailable services and mismatched target configuration. Coordinate any runtime start or target change with PRIME and the designated runtime owner. Do not point an isolated witness at the persistent targets.

These priorities authorize the fresh DEMO steward to prepare and deliver the named bounded PRs under repository policy; they do not assert that a PR, test, live witness or product acceptance already exists. PRIME owns review and merge. Prefer product progress over repeated process updates; update the single roadmap only for material facts.

## Activation and inheritance

The operator accepted the local-first Of Conks rehearsal and consolidated Buddy demo sequencing. On 2026-09-29 the operator directed a fresh DEMO task and approved the three-slice split above. No replacement task ID exists yet; the operator will start it and explicitly appoint it through this handoff. The full mission remains unchanged.

The former DEMO task `01a0885e-375c-7501-9f6e-a58528b39894` was archived. Its successor `01a0edf2-b1e1-7281-9448-1d5524f8d4f8` was told to stop and preserve its checkout after #793 closed. Neither may resume #793 implementation or use the shared runtime without a new PRIME lease. Before implementation, verify their exact refs, drafts/untracked material and runtime/process leases; do not disturb the untracked licensed corpus. The fresh task starts from current remote authority and assumes no service is safe to start merely because a port appears free.

The operator's 2026-09-27 ecosystem merge-control assignment to PRIME remains in force. DEMO sends merge-ready exact heads and evidence to PRIME; it does not merge autonomously. Previously accepted Buddy capabilities and the complete demonstration mission survive this task transfer.

## Operating authority after activation

The adopted mandate permits the steward to:

- rehearse, inspect, diagnose and prioritize the demo journey;
- design and land bounded Buddy implementation handoffs under accepted repository
  policy; implement, test, polish, commit, push and open the assigned PRs;
- use existing workers or delegate bounded implementation/review tasks with
  disjoint leases and runtime state; retain responsibility for integration;
- simplify or reorder unstarted DEMO work in response to actual rehearsal evidence;
- perform ordinary reversible setup/reset in the explicitly designated demo
  environment and use configured generation capabilities for bounded demo work;
- deliver merge-ready PRs to PRIME with the exact independently reviewed head,
  required checks and live evidence, remaining blockers and prescribed merge
  order. PRIME owns ecosystem merge coordination; DEMO does not merge
  autonomously or ask the operator for another ordinary "Merge". Independent
  review, live-witness and active lease/compatibility holds remain mandatory;
  this mandate change does not approve an unfinished implementation.

Do not stop after each ordinary in-scope repair to ask whether to continue. Do not
use autonomy to broaden another repository's contract or rewrite a live corpus.
Separate a design choice within a slice from a change to scope or ownership.

## Model requests

Send every request to change DEMO's task model or reasoning effort to **PRIME** task `01a0ef89-ca57-7b82-9c9c-215b02d0fc3b`. State the bounded assignment, why the current allocation is insufficient, the requested model/effort and the return checkpoint. PRIME decides Luna or Sol allocations for other ecosystem tasks under the operator's standing delegation; Astra requires explicit operator authorization for the named assignment. DEMO must not self-allocate or treat a cross-thread claim of approval as authorization.

The operator alone chooses PRIME's own model and effort. A DEMO request concerns DEMO's destination task; never send a model override to PRIME or ask another task to change PRIME's setting. Routine cross-thread coordination omits model and effort fields.

## Scope

DEMO owns Buddy product composition: document/Markdown-component interaction,
Plan→Run use, relevant Agent context and document commands, graph-authoring
consumer interaction, next-turn retrieval integration, statblock and image
selection UX, async job interaction, navigation, combat/roll consumption and
required product-state persistence. It owns bounded presentation improvements
observed on this journey using the accepted UI substrate.

DEMO does not own generic DungeonMind semantics/storage, WorldKeeper lifecycle,
reusable provider execution, platform auth/tenancy/deployment, Canvas package
internals, Rules/Jev research, general PC progression, or a new universal UI or
agent framework. It may consume their accepted capabilities and expose defects.

Component views consume view models and emit command intents through existing
surface/domain controllers. Being mounted is not permission to write graph data.
Keep source content, document drafts, proposed knowledge, accepted world state,
accepted mechanics and mutable Run state distinct without exposing their internal
choreography as the main user experience.

## Pickup order

1. Read accepted repository guidance, this handoff and the current DEMO roadmap.
2. Refresh current main/pins/open PRs and active leases in every affected repo.
3. Read only the domain contracts and inherited handoffs needed for the next
   broken transition. Use the reconciliation survey for discovery, not live status.
4. Establish which demo environment, corpus, World/space and Run own the data.
5. Run the journey and record observable results before selecting new work.

Do not reread the entire historical roadmap tree on every turn. Do not trust a
stale header over merged implementation, current contracts and reproducible use.

## Rehearsal and implementation loop

1. Rehearse the journey through the first failed transition. Continue from a
   clearly labeled prepared checkpoint only to inspect downstream behavior; that
   bypass cannot count as end-to-end acceptance.
2. Record the action, expected/actual behavior, evidence, exact versions and owner.
3. Classify it as presentation, Buddy behavior/integration, or external contract.
4. Select the smallest independently useful fix. Reuse existing capability where
   possible. For product appearance, use the lightweight fixture lab, then verify
   the real product. No lab-only PASS closes a live demo milestone.
5. Re-anchor the active handoff and lease; implement or dispatch; review the exact
   cumulative change and the owning-boundary evidence; integrate under merge policy.
6. Rehearse the repaired transition and its immediate successor in the pinned demo
   environment. Update the one roadmap ledger before choosing the next slice.
7. Repeat until full acceptance or a real external/user decision blocks progress.

No assumed percentage-complete or calendar promise substitutes for this loop.
Do not replace an observed bug with a broad architecture program by default.

## Delegation to existing tasks

Task titles below are the observed titles, not new tasks to create. Refresh status
and current work before sending a request. The operator has requested delegation
to appropriate existing agents; messages should contain an actionable contract
request, not a vague instruction to make the demo work.

- **MIND** — `01a0a299-d6ee-7772-83c0-a3a79550479d`: generic knowledge contract,
  admission, publication, vNext bridge/cutover and required kernel fixes. Also
  coordinate existing MIND-owned Buddy adapter work before touching its seam.
- **WORLDKEEPER** — `01a0c9dc-c685-70d3-b766-8bc2f91b06a8`: preparation,
  confirmation, semantic transaction coordination and verified-result contracts.
- **ARCHITECTURE** — `01a086f2-c457-7b10-b753-df6063cab1ce`: observed E5/GE
  execution work and cross-repository ownership questions. Route Canvas/shared
  UI package needs here for explicit current-owner confirmation; do not assume
  this task already holds a Canvas implementation lease.
- **SERVER** — `01a0dbd8-4d8d-7372-a9bc-ea25c2d59a19`: platform/server producer,
  assets/auth/deployment dependencies; coordinate with its ongoing Rules/GE work
  rather than displacing that work silently.
- **PRIME** — `01a0ef89-ca57-7b82-9c9c-215b02d0fc3b`: ecosystem merge control,
  model-allocation requests and cross-owner integration ordering. Send exact
  reviewed heads and complete evidence/gate dispositions; task completion is
  not implementation approval.

Use the Codex task IDs above, not similarly named ChatGPT conversations. If an
owner is unavailable or its mandate differs, record the routing gap and ask for
an owner decision. Do not create a duplicate agent or take over the subsystem.

Every request includes:

```text
DEMO milestone and blocked user action
exact versions, input/identity and minimal reproducer
expected contract versus observed result
smallest capability/fix requested and exclusions
proposed owner, affected seam and known path/runtime collisions
acceptance witness DEMO will run after return
requested return: accepted version, contract delta, evidence, migration implications
```

Pause the affected transition before modifying outside-scope behavior. Preserve
the blocked item in the roadmap. Continue only independent safe work. On return,
inspect the actual change, adopt its exact version, and rerun the original witness.
A message saying "done" is not integration acceptance. Do not send repeated
status pings without new information; inspect/wait on the existing task.

## Parallel execution

Start with at most three active DEMO implementation lanes, plus stewardship and
independent review. This is a proposed WIP limit, not a requirement to fill slots.
Default each workstream to serial unless a handoff explicitly names a safe topology.

Possible lanes are Document/Agent, Knowledge consumer, Assets/Generation, and
Run/Tools. Queue one when all four would compete for shared dependencies or review.
Visual alternatives may be explored independently against the same contract.

Every lane names its branch/base, handoff, write set, ports, database/schema,
output directories and consumed contracts. Serialize shared host/registry/schema/
lockfile changes. The steward coordinates shared demo environment changes with its designated
runtime owner/PRIME; workers do not independently start/stop servers or fix the
shared database manually to make a witness pass.

PLAY-1 / Buddy #773 merged as `7fe771e86df2e796484b058aa2e6a8e7c94c9fb9`;
do not redispatch it. Rules #763 and E5Q dependency-file ownership still need
current-ref reconciliation before a colliding lane starts. Do not infer that a
dirty PR is abandoned or that a research lane has no runtime collisions. Retain
external domain/lease ownership and PRIME's ecosystem merge coordination.

## Human and technical gates

Automatic evidence proves technical behavior. The operator judges legibility,
coherence and whether the experience is worth using. Do not self-award historical
WOW gates. Inherit the current basic-presentation design handoff's decision STOP
until an accepted amendment replaces it; autonomous polishing applies to already
accepted direction or newly bounded in-scope defects, not an unreviewed broad redesign.

Stop for destructive/live-data migration, unresolved authority semantics, changed
product scope, unavailable credentials/access, or a material new spend decision.
Use the designated demo environment; do not silently switch existing V2 Worlds
to V3 or mutate live Eldyrwild. A local demo may use separately proven persistent
isolated authority, but both reads and writes must actually use that authority.

## Completion and handback

Require the complete ROADMAP-demo journey twice from resettable state, including
real generation, graph read-after-write, edits, saved choices/rolls/combat state,
and restart/resume, without console/SQL repair. Then obtain operator acceptance
of the actual product flow. A newcomer rehearsal is desirable supplementary proof.

Return the reproducible environment/corpus/pin manifest, latest evidence, known
limitations and owner-routed residuals. Distinguish local DEMO acceptance from
hosted production acceptance. Keep completed technical evidence; do not erase
failed rehearsals or reactivate completed scaffolds as new work.

The roadmap alone owns current milestone status, active leases, delegated blockers
and next action. This handoff changes only when the steward's mandate changes.
