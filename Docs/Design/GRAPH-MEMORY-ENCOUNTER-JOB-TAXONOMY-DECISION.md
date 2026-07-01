# Graph Memory Encounter/Job Extraction Taxonomy Decision

**Status:** Accepted design decision  
**Created:** 2026-07-01  
**Workstream:** Graph Memory extraction spike  
**Depends on:** PR 00 baseline anchor, PR 01 vocabulary hygiene, PR 02 blocked-collision diagnostics, PR 03 cross-class policy v0  
**Next PR:** PR 05 candidate graph contract support for encounter/job  

## Decision

Graph Memory should represent jobs and combat scenes with a dedicated `encounter_job_pass`, not by further overloading `thread_pass`.

The first implementation slice should add exactly two first-class candidate node types:

- `combat_encounter`
- `quest`

Use `quest` as the canonical graph type for job/quest/task/mission work. Do not add a separate `job` node type in v0.

Do not add `adversary`, `monster`, `infrastructure`, `landmark`, `governance`, `resource`, or `ecology` node types in this slice.

## 1. Problem

The current extraction shape has separate category passes for actors, locations, collectives, objects, threads, beats, and edges. That shape is useful, but the recent dogfood beds show that jobs and combat scenes need a durable structural home rather than more contextual vocabulary or broader prompt language.

`thread_pass` is useful for mysteries, clues, warnings, unresolved phenomena, and narrative threads. It becomes overloaded when it must also represent jobs, scenes, warnings, unresolved phenomena, and combat structure. If every actionable job, tactical fight, vague warning, and unresolved mystery is represented as a thread-like object, `thread_pass` becomes a dumping ground and its quality for actual mysteries can regress.

`beat_pass` gives source-local scene scaffolding, but a beat is not the same thing as a durable graph identity for an encounter. A beat can help locate where a scene appears in a recap; it should not be the only object that future passes use when they need to attach participants, adversaries, locations, objectives, outcomes, or follow-up consequences.

`edge_pass` cannot reliably attach participants, objectives, outcomes, rewards, or locations if the job or encounter node does not exist. The edge extractor can only connect entities that the candidate graph has already made available or that the contract safely permits. Without a durable quest or combat encounter node, useful relationships either vanish, attach to the wrong thread, or collapse onto generic actors, objects, or places.

C1S1 exposes the issue cleanly:

- the rat-clearing job is not cleanly represented;
- the cellar rat fight is not cleanly represented;
- PC participation/action attachment is weak;
- the mage tower mystery should remain a thread, not become a quest or encounter.

The issue is not that the model lacks the words “job” or “fight.” The issue is that the current graph has no durable object for a job or combat scene to attach edges, participants, locations, outcomes, and future references to.

## 2. Alternatives considered

| Option | Description | Why not enough |
|---|---|---|
| Keep using `thread_pass` | Continue representing jobs, mysteries, warnings, hooks, and encounters as thread-like nodes. | Preserves simplicity but keeps making `thread_pass` a dumping ground and risks degrading mystery/thread quality. |
| Add many new node types immediately | Add `adversary`, `monster`, `job`, `quest`, `task`, `combat_encounter`, `social_encounter`, `infrastructure`, `resource`, and governance types. | Solves vocabulary gaps by type sprawl; too much contract churn before dogfood proves the shape. |
| Add only node types, no pass | Add `combat_encounter` and `quest` to existing passes. | Existing passes do not own the needed synthesis across beats, party anchors, adversaries, objectives, and outcomes. |
| Dedicated `encounter_job_pass` with minimal node types | Add a focused pass that extracts durable job/quest and combat encounter nodes after core entities and beats are known. | Chosen. Small enough to test, structurally targeted, and avoids broad taxonomy churn. |

## 3. Chosen approach

The chosen approach is dedicated `encounter_job_pass` + minimal candidate node-type expansion.

The `encounter_job_pass` should run after the core node passes and after `beat_pass`, with access to:

- source spans;
- consolidated candidate nodes;
- source-local beats;
- deterministic party anchors;
- pass-targeted vocabulary context when available.

In its first prototype, the pass should emit candidate nodes only, not edges. It should create durable graph objects that later edge or attachment passes can connect to participants, adversaries, locations, objectives, outcomes, rewards, and follow-up consequences.

Required v0 emitted node types:

- `combat_encounter`
- `quest`

The pass should not emit:

- `character`
- `location`
- `organization`
- `item`
- `thread`
- `mystery`

If the pass sees those concepts, it should bind to existing nodes later by edges or participation logic rather than recreating them. This keeps the pass focused on the missing durable job/encounter objects and avoids replacing the existing actor, location, collective, object, and thread passes.

## 4. Candidate node type: `combat_encounter`

A `combat_encounter` is a durable graph node for a discrete conflict scene or tactical confrontation. It is not the monster, not the location, not the quest, and not the recap beat. It is the encounter object that participants, adversaries, location, objective, outcome, and follow-up consequences can attach to.

Examples:

- Glowkindle cellar rat fight
- Mireward north-gate defense
- Tripod Null-Calf gate pressure sequence

Non-examples:

- The rats as creatures
- The cellar as a location
- The general existence of danger in the swamp
- A vague warning that enemies are coming
- A mystery about the mage tower

Minimum future candidate fields:

- `node_id`
- `label`
- `node_type: "combat_encounter"`
- `description`
- `importance`
- `evidence_refs`
- `semantic_state`
- `proposed_action`
- `confidence`
- `warnings`

PR 05 should map `combat_encounter` into identity resolution as a temporal/phenomenon-like class unless a better existing contract already exists. It should not be treated as `thread`.

For identity purposes, `combat_encounter` should initially behave closer to a concrete temporal phenomenon than to a narrative thread. It may share some behavior with `event`, but it needs a distinct candidate node type so downstream passes can attach combat-specific relationships.

## 5. Candidate node type: `quest`

A `quest` is a durable graph node for an accepted, offered, assigned, discovered, or pursued objective. In this project, `quest` is the canonical candidate graph type for jobs, tasks, missions, bounties, errands, and requests.

Examples:

- Clear rats from Glowkindle’s cellar
- Investigate the mage tower
- Carry a warning to Mireward
- Defend the north gate
- Find the missing contact

Non-examples:

- The job board as a physical object
- The employer NPC
- The reward item
- The combat encounter that occurs while pursuing the quest
- A general unresolved mystery with no actionable objective

Use `quest`, not `job`, as the candidate graph node type. `job`, `task`, `mission`, `bounty`, and `errand` are labels or aliases in prose, not separate node types in v0.

`quest` may remain in the broad thread/hook identity family for v0 if that is what current identity-resolution mapping already expects. Even if its coarse identity behavior stays thread-like initially, it still needs first-class candidate graph support if not already present so later passes can distinguish actionable objectives from mysteries and warnings.

## 6. Why not `adversary` / `monster` yet

Do not add `adversary` or `monster` as first-class node types in this slice.

An adversary is often a role in an encounter, not an identity class. The same entity can be an adversary in one scene and an ally, neutral faction, environmental pressure, or ordinary actor in another. Treating adversary as a durable node type too early risks encoding a scene-relative role as a global identity.

Monsters and creatures are still real entities, and the actor extraction path may already emit actor/creature-like nodes for them when the source supports it. However, adding a creature/adversary taxonomy now would expand the slice too far. This decision is deliberately limited to durable objects for jobs and combat scenes, not every participant role within those objects.

PR 06 can attach opposition roles to existing actor/creature-like nodes when present, or leave the relationship for a later edge/attachment slice when the node is absent. A later adversary/creature design may be warranted after encounter/job dogfood shows which roles and creature identities need durable support.

In v0, “adversary” should be modeled as a relationship or participation role relative to a `combat_encounter`, not as a durable node type.

## 7. Pass boundary

`encounter_job_pass` owns:

- identifying discrete combat encounters;
- identifying actionable jobs/quests/tasks/missions;
- separating the job from the encounter that may occur while pursuing it;
- naming the durable encounter/quest node;
- citing evidence for each node;
- leaving participants, locations, adversaries, outcomes, and rewards for later edge/attachment passes unless the existing contract already supports safe references.

`encounter_job_pass` does not own:

- discovering PCs;
- rediscovering party members;
- replacing actor/location/object/collective passes;
- extracting all threats;
- solving governance/institution modeling;
- solving resource/ecology modeling;
- merging duplicate places/objects;
- promoting anything to canon.

Deterministic PC participation attachment belongs to a later slice, not this design note. This decision only creates the structural place where future participation attachment can land.

## 8. Expected C1S1 dogfood shape

C1S1 is the concrete first dogfood target because it is small, already reviewed, and exposes both missing job representation and missing combat encounter representation without requiring broad taxonomy expansion.

| Source situation | Desired graph shape | Type |
|---|---|---|
| Party accepts or pursues rat-clearing work connected to Glowkindle / cellar problem. | One durable quest node, e.g. `Clear rats from Glowkindle’s cellar`. | `quest` |
| The actual rat fight in the cellar. | One durable combat encounter node, e.g. `Glowkindle cellar rat fight`. | `combat_encounter` |
| Rats / rat swarm / hostile creatures. | Existing actor/creature-like node if emitted by actor extraction; otherwise attach later when supported. | not new in this slice |
| Glowkindle’s cellar. | Existing location node from location extraction. | not new in this slice |
| Party PCs participating. | Deterministic PC attachment in later PR. | not rediscovered |
| Mage tower mystery. | Remains a thread/mystery. | not quest unless explicit objective is extracted |

Manual review questions for C1S1:

- Is the rat-clearing job represented separately from the rat fight?
- Does the rat fight have a durable encounter node?
- Did the pass avoid turning every mystery or warning into a quest?
- Did the pass avoid creating duplicate PC nodes?
- Did the pass avoid creating duplicate locations/items/employers?
- Can a future edge pass attach participants, location, adversaries, outcome, and reward to these nodes?

## 9. Expected C2 dogfood shape

The live-campaign bed should be used more generally after the C1S1 shape is understood. It should validate that the decision can handle siege-pressure recap text without mistaking every threat, warning, or broad battle state for a durable encounter or quest.

Expected C2 behavior:

- `Mireward north-gate defense` can be a `combat_encounter`.
- A specific assigned defense objective can be a `quest` if the text frames it as an accepted/assigned objective.
- Siege threats such as Tripod Null-Calf or Under-Hymn Brood are not themselves `combat_encounter` nodes.
- A general warning that the swamp is erupting is not automatically a `quest`.
- A broad siege state may eventually need another model, but not in this slice.

The C2 bed does not need to be fully implemented in this PR. It is a future dogfood check that the C1S1-oriented shape generalizes to live campaign recap pressure without authorizing runtime integration.

## 10. Implementation implications for PR 05

PR 05 should add candidate graph contract support for `combat_encounter` and `quest`, without adding the extraction pass.

Likely files PR 05 will inspect/change:

- `src/graph_memory/candidate_graph_preview.py`
- `src/graph_memory/identity_resolution.py`
- `evals/graph_memory_layer/taxonomy_registry.json`
- tests related to candidate graph preview / identity resolution / taxonomy registry

PR 05 should:

- ensure `combat_encounter` is an allowed candidate node type;
- ensure `quest` is an allowed candidate node type if not already supported in the candidate graph contract;
- map `combat_encounter` to an appropriate coarse identity class, likely phenomenon/event-like for v0;
- preserve existing `quest` identity behavior if already mapped to thread/hook;
- add tests proving the new types validate and serialize;
- avoid adding the `encounter_job_pass`;
- avoid adding new edge predicates unless current validation absolutely requires a tiny placeholder.

PR 05 should not:

- add extraction prompts;
- call an LLM;
- regenerate artifacts;
- modify corpus;
- wire runtime ingest;
- add `adversary`, `monster`, `job`, `task`, `infrastructure`, `resource`, or `governance` node types.

## 11. Implementation implications for PR 06

PR 06 should prototype `encounter_job_pass` in eval/dogfood paths only, after PR 05 adds contract support.

PR 06 should:

- add an eval-only prompt/pass for extracting `combat_encounter` and `quest` nodes;
- consume source spans, consolidated nodes, beats, deterministic party context, and pass-targeted vocabulary context when available;
- emit candidate nodes only in the first prototype;
- compare baseline vs pass-enabled output in Manual Review UI or equivalent checked-in artifact path;
- focus first on C1S1.

PR 06 should not:

- wire the pass into production runtime ingest by default;
- add PC participation attachment;
- add encounter/job edge-family extraction;
- solve governance/resource modeling;
- mutate corpus;
- promote canon.

## 12. Deferred decisions

Deferred:

- Whether to add `adversary`, `creature`, or `monster` as first-class node types.
- Whether to add `social_encounter`.
- Whether `combat_encounter` should eventually be its own identity class rather than phenomenon/event-like.
- Whether infrastructure/landmark should be first-class.
- Whether governance/institution modeling needs its own pass.
- Whether resource/ecology modeling needs its own pass.
- Whether quests need lifecycle states such as offered/accepted/completed/failed.
- Whether rewards should become structured relationships or remain ordinary object/edge facts.

These decisions are deferred, not permanently rejected. The point of this slice is to dogfood the smallest structural change that can represent jobs and combat encounters before expanding the taxonomy.

## 13. Non-goals

This decision does not authorize:

- changing runtime graph ingestion;
- mutating corpus files;
- promoting candidate graph memory to canon;
- adding new extraction behavior in this PR;
- adding broad taxonomy expansion;
- changing merge policy;
- treating every thread as a quest;
- treating every dangerous situation as a combat encounter;
- rediscovering PCs through LLM extraction.

## 14. Acceptance checklist for this decision

The decision is accepted if a future reviewer can answer yes to all of these:

- Does the document clearly choose `encounter_job_pass` over more `thread_pass` overloading?
- Does it add exactly two first-slice node types: `combat_encounter` and `quest`?
- Does it reject `job` as a separate v0 node type?
- Does it defer `adversary` / `monster` as node types?
- Does it define what `combat_encounter` is and is not?
- Does it define what `quest` is and is not?
- Does it make C1S1 dogfood expectations concrete?
- Does it make PR 05 contract work mechanical?
- Does it make PR 06 eval-pass work mechanical?
- Does it avoid authorizing corpus mutation, canon promotion, runtime wiring, or LLM extraction?
