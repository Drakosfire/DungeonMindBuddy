# Steward handoff — DEMO, from preparation to a resumable session

**Status:** ACTIVE — operator adopted the DEMO stewardship mandate on 2026-09-26  
**Owner:** existing Codex task DEMO (`01a0885e-375c-7501-9f6e-a58528b39894`)  
**Repository:** `Drakosfire/DungeonMindBuddy`  
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

## Activation and inheritance

The operator accepted the local-first Of Conks rehearsal, consolidated Buddy
demo sequencing, and a standing merge rule for reviewed in-scope DEMO work.
The roadmap records that decision once. Existing authorized work continues under
its current handoffs until explicitly transferred; adoption does not revoke it.

The receiving task is `01a0885e-375c-7501-9f6e-a58528b39894` on host `local`.
It was renamed from PLAY to DEMO. Retain its history and active work.
In particular, inherit PLAY-1 / Buddy #773 on its existing branch with its current
limited consumer-proof contract. Check its current state before any action;
do not reopen it if it has since merged. Reconcile successors PLAY-2/3 with the
DEMO knowledge milestone rather than opening competing implementations.

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
- merge bounded in-scope DEMO PRs after independent exact-head review passes,
  required checks pass, and active lease/compatibility concerns are settled.
  Cross-owner PRs retain their owner's merge authority.

Do not stop after each ordinary in-scope repair to ask whether to continue. Do not
use autonomy to broaden another repository's contract or rewrite a live corpus.
Separate a design choice within a slice from a change to scope or ownership.

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
lockfile changes. The steward alone updates the shared demo environment. Workers
do not fix the shared database manually to make a witness pass.

At adoption, explicitly settle #773 versus Rules #763 and E5Q dependency-file
ownership. Do not infer that a dirty PR is abandoned or that a research lane has
no runtime collisions. Retain external owners' merge authority.

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
