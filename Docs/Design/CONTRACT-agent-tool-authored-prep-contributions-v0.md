> Status: KEEP_CONTRACT / ACTIVE DESIGN CONTRACT
> Use for: Agent tool capabilities, authored-prep lifecycle, preview/confirmation semantics, content-pack contribution framing, and surface/write-path boundaries.
> Do not use for: Runtime tool registry implementation, Projection Engine, graph-backed retrieval, or PR006 materialization.
> Architecture authority: Docs/Design/ARCHITECTURE-campaign-supergraph.md
> Sequence authority: Docs/Plans/PR-TRACKER-campaign-supergraph.md
> Runtime implementation phase: PR011
> Last sync checked: 2026-07-11

# CONTRACT — Agent Tool + Authored Prep Contributions (v0)

Normative contract for how agents and authored prep may read, draft, preview, and—only after explicit revision-bound GM confirmation—contribute through the governed World Supergraph write path.

This document does **not** implement Hermes runtime, a tool registry, Projection Engine, or PR006 materialization. PR011 implements the runtime tool surface against this contract.

---

## A. Inherited invariants

These are normative:

1. **One World Supergraph per `worldId`.**
2. **Campaign is scope, not graph ownership.**
3. **Sessions are lenses.**
4. **Read and write paths remain separate.**
5. **Agents are not privileged graph writers.**
6. **No agent writes graph/storage internals.**
7. **No agent advances graph head directly.**
8. **No agent selects graph state** by latest-ingest, preview-source, manifest, or store path.
9. **No chat, UI thread, Hermes memory, summary, trace, or diagnostic becomes campaign canon.**
10. **Every durable write** uses governed source/decision records, `GraphContribution` where applicable, Kernel merge, validation, and **atomic graph-head** advancement.
11. **Every durable assertion** preserves authority, epistemic kind, acceptance state, temporal scope, visibility, campaign/world scope, evidence/provenance, and contribution lineage.

Dual authority (architecture §4):

- Corpus / source artifacts are **prose and evidentiary authority**.
- The World Supergraph head is **durable materialized knowledge state**.
- Governed authored assertions and identity decisions survive reconstruction.
- Hermes / UI / thread memory is **non-canonical continuity**.

---

## B. Capability taxonomy

Use exactly these categories:

| category | purpose | allowed inputs | allowed outputs | durable effect | required confirmation | allowed surfaces | required context / revision pin | audit expectations | implementation phase |
|---|---|---|---|---|---|---|---|---|---|
| `read_only` | Read projections, source units, diagnostics, node views, evidence, health, retrieval outputs, source anchors | world/campaign/focus, admissibility policy, optional graph revision pin, source locators | projected views, evidence units, diagnostics, health, retrieval packets | **no durable effect** | none | Plan, Play, Build, Graph Review/Ingest, Agent Interaction | graph revision pin or coherent request snapshot preferred | correlation id; what was read at which pin | PR011 (reads may land earlier via existing APIs) |
| `draft_only` | Produce speculative prep or artifacts | idea/prompt, surface context, optional draft pointers | draft text/objects; optional revisioned non-canonical draft artifact | **no durable graph effect** merely because text exists; optional non-canonical draft artifact save | none for ephemeral; explicit save for draft artifact | Plan, Build, Agent Interaction, Graph Review (prep drafts) | surface + world; campaign optional | draft id/version if saved; actor | PR011 |
| `preview_write` | Produce a reviewable proposed effect and diff | draft or proposed change, source/graph pins, identity candidates | proposal with human-readable diff + machine-readable effect summary | **no durable graph effect** | none (preview is not commit) | Plan (launch), Graph Review/Ingest (primary), Agent Interaction (invoke) | **expected parent graph revision**; source revision pins | proposal_id / version / digest; validation findings | PR011 |
| `confirm_commit` | Execute one bound proposal through the governed write path | proposal_id + version + digest, confirming principal, expected parent | merge/publish result or stale/conflict rejection; fresh read pointer | durable only via Kernel path (contribution / decision / source revision + atomic head) | **explicit GM confirmation bound to one current proposal** — not autonomous | Graph Review/Ingest (primary cockpit); Agent Interaction may invoke only with bound confirm | proposal digest + expected parent graph revision must match | confirming principal; proposal digest; parent revision; outcome | PR011 |
| `admin_diagnostic` | Read health / integrity / replay / conflict information | world id, revision pin, contribution/decision ids | integrity reports, conflict lists, replay diagnostics | **no durable effect** unless followed by a separate preview-confirm operation | none for read diagnostics | Graph Review/Ingest, admin tools, Agent Interaction (diagnostic tools) | revision pin preferred | correlation id; diagnostic scope | PR011 (health slices also PR002/PR005/PR006) |

### Required semantics

**`read_only`**

- Reads projections, source units, diagnostics, node views, evidence, health, retrieval outputs, source anchors.
- No durable effect.
- May require an explicit graph revision pin or coherent request snapshot.

**`draft_only`**

- Produces speculative prep or artifacts.
- No durable graph effect merely because text exists.
- Saving a draft may create a revisioned non-canonical source artifact, but must not create accepted graph truth unless separately promoted through preview/confirmation.

**`preview_write`**

- Produces a reviewable proposed effect and diff.
- No durable graph effect.
- Must identify affected source records, assertions, identities, visibility/canon/epistemic fields, validation findings, expected parent graph revision, and conflicts.

**`confirm_commit`**

- Is **not** autonomous authority.
- May execute only with explicit GM confirmation bound to one current proposal.
- Invokes the normal governed write path.
- Must fail closed when the proposal, source revision, identity outcome, or expected parent graph revision is stale or materially changed.

**`admin_diagnostic`**

- Reads health/integrity/replay/conflict information.
- No durable effect unless followed by a separate preview-confirm operation.

---

## C. Common invocation context

Conceptual, implementation-neutral envelope (not a runtime schema):

| Field | Role |
|---|---|
| actor / confirming principal | who invoked; who confirmed (may differ) |
| surface | Plan / Graph Review / Agent Interaction / Build / Play |
| worldId | required world tenancy |
| campaignId? | scope, not ownership |
| focus? | session / prep window / node focus |
| admissibility / visibility policy | what the actor may see |
| graph revision pin or expected parent revision | coherence for reads; parent for writes |
| source artifact + revision pins | evidentiary / prose pins |
| thread/draft pointers | continuity only |
| tool capability category | one of the five categories |
| correlation / audit id | end-to-end audit |

Clarify:

- A **thread pointer is context, not authority.**
- A **surface context is scope, not ownership.**
- A **graph revision pin is coherence, not permission.**

---

## D. Draft-only flow

```text
human or agent idea
→ draft in UI/thread/tool
→ optional revisioned draft artifact
→ draft/prep projection only
→ no accepted graph assertion
```

| Outcome | When | Durable effect |
|---|---|---|
| Ephemeral / no durable write | Scratch text in thread or unsaved UI | none |
| Saved non-canonical source artifact revision | Explicit save of draft/prep artifact | draft artifact revision only; **not** accepted graph truth |
| Eligible for later `preview_write` | Draft is concrete enough to propose assertions/placements | still no graph effect until preview → confirm |

---

## E. Preview-write proposal contract

A proposal includes at least:

| Field | Purpose |
|---|---|
| `proposal_id` | stable identity of the proposal |
| `proposal_version` | monotonic version within that id |
| `proposal_digest` | content digest of the proposed effect |
| `created_by` | actor |
| `created_at` | timestamp |
| world/campaign target | tenancy + scope |
| source revision pins | prose/evidence pins |
| **expected parent graph revision** | fail-closed parent for confirm |
| proposed source artifact revisions | if prose/source edits are part of the effect |
| proposed `GraphContribution` assertions | durable graph claims if confirmed |
| proposed identity/alias decisions | merge/split/unmerge/create outcomes |
| visibility / canon / epistemic / temporal metadata | required assertion metadata |
| validation and collision diagnostics | pre-commit findings |
| human-readable diff | what the GM reviews |
| machine-readable effect summary | what runtime applies |
| confirmation requirement | always required for durable effect |
| stale/expiry behavior | when confirm must be rejected |

A preview is **not** canon, **not** a graph revision, and **not** a contribution accepted into the graph.

---

## F. Explicit confirmation contract

Normative rules:

1. A generic “yes” in chat is **not** sufficient durable authorization unless the product binds it to one visible proposal.
2. Confirmation must identify the **proposal id / version / digest** and **confirming principal**.
3. Confirmation must occur **after** the human-readable effect is available.
4. Confirmation does **not** waive validation, identity policy, visibility policy, or stale-parent checks.

### Stale confirmation behavior

If the source revision, **proposal digest**, identity outcome, or **expected parent graph revision** changes materially:

```text
reject confirm_commit
→ return a stale/conflict result
→ require refreshed preview and new confirmation
```

Do not invent cryptographic or transport details beyond this contract. Existing prepare-token / stale-confirm precedents in Graph Object Authoring are transitional implementations of the same fail-closed idea.

---

## G. Confirmed write flow

```text
draft or proposed change
→ preview_write proposal
→ GM reviews exact effect
→ explicit bound confirmation
→ confirm_commit request
→ governed source artifact revision and/or decision record
→ GraphContribution
→ Kernel identity resolution / merge
→ proposed immutable graph revision
→ validation
→ atomic graph-head advancement
→ audit result + fresh read pointer
```

Branches:

| Branch | Behavior |
|---|---|
| Source-text editing | Creates a source revision, then contributes through normal ingestion/merge |
| Authored graph assertions | May create governed authored source records and `GraphContribution`s **without** rewriting prose |
| Identity / alias / merge / split / unmerge | Uses governed **identity decision** records |
| Rejected validation | Leaves the **prior head** readable; no silent partial publish |
| UI or agent | **Never** writes graph files directly |

Agents are **not privileged** writers: they may only reach this path through categorized tools and bound confirmation.

---

## H. Authored-prep lifecycle

Use exactly these lifecycle labels:

```text
draft
planned
placed
played
world_canon
retracted
superseded
```

Do **not** model them as one simplistic mutable truth enum. Explicitly separate:

| Dimension | Owns |
|---|---|
| authored-prep lifecycle | draft → planned → placed → played → world_canon (+ retracted/superseded) |
| graph assertion acceptance state | candidate / accepted / rejected / etc. on durable assertions |
| epistemic kind | fact / plan / hypothesis / … |
| authority class | source-derived / GM-authored / … |
| visibility | gm / player / … |
| campaign/world scope | which scopes the claim applies to |
| temporal validity | when the claim holds |
| source/contribution status | active / superseded / retracted on `GraphContribution` |

### Lifecycle table

| state | meaning | source representation | graph representation | projection visibility | promotion trigger | required confirmation | retraction / supersession behavior |
|---|---|---|---|---|---|---|---|
| `draft` | speculative | optional draft artifact; often ephemeral | no accepted assertion required | draft/prep contexts only | save draft artifact (optional) | save if durable draft artifact | may discard or retract draft |
| `planned` | GM intends possible future use | prep/plan source or authored plan record | may appear as epistemic `plan`, not fact/played | normally GM-private prep projections | explicit save/confirm of plan intent | yes for durable plan | retract or supersede with newer plan |
| `placed` | linked to location/faction/session/encounter/node/prep window | placement metadata on prep record | scoped plan metadata edges/attrs; **not** proof it occurred | prep + placement-aware projections | explicit placement confirm | yes | retract placement; supersede placement target |
| `played` | supported by actual-play source, recap, or explicit GM played-event assertion | actual-play / recap / played-event source | played assertions with play evidence; **must not** be a mere relabel of `planned` | play-admissible projections | play evidence or explicit played-event confirm | yes | plan vs play divergence remains inspectable; retract/supersede with evidence |
| `world_canon` | explicit durable world-level acceptance | world-scoped source or promotion record | world-scoped accepted assertions | world-admissible projections | **explicit** promotion; never inferred from planned/placed/played alone | yes | must not silently universalize campaign-specific facts |
| `retracted` | withdrawn/invalidated | retained for audit | contribution/assertion retracted | excluded from current truth projections | retract confirm | yes | retained for audit and replay |
| `superseded` | replaced by newer source revision or contribution | historical revision retained | prior contribution superseded | historical only; not current truth | superseding write | via superseding confirm | remains historical; must not silently overwrite |

### Examples

**Mireward breach encounter**

```text
draft → planned → placed
actual table event differs → played record from recap
only durable surviving world consequences become world_canon
```

**NPC draft**

```text
draft → planned → placed at an inn
never used → retracted
```

**Content-pack statblock**

```text
pack revision v1 → placed in campaign
v2 replaces mechanics → superseded, not silently overwritten
```

---

## I. Transition-to-durable-object mapping

For every transition, identify one or more of:

```text
no durable write
source artifact revision
GraphContribution
authored assertion record
identity decision
alias decision
retraction record
supersession record
graph-head advancement
```

| Transition | Typical durable objects |
|---|---|
| idea → ephemeral draft | no durable write |
| save draft | source artifact revision (non-canonical) |
| draft → planned | source artifact revision and/or authored assertion record + optional `GraphContribution` (epistemic plan) + graph-head advancement if published |
| planned → placed | authored assertion / contribution with placement metadata + graph-head advancement |
| placed/planned → played | **new** play-evidenced source revision and/or played assertion contribution — not a label flip |
| * → world_canon | explicit promotion contribution / decision + graph-head advancement |
| retract | retraction record + contribution status + graph-head advancement |
| supersede | supersession record + new contribution + graph-head advancement |

Rule:

```text
A lifecycle label alone never performs a graph mutation.
A governed record/contribution performs the durable effect.
```

---

## J. Content packs and reusable prep

**Content packs** are revisioned source artifacts or bundles that may contain:

- prose
- draft objects
- relationship templates
- statblocks/mechanics
- placement hooks
- visibility defaults
- proposed contribution material

Import / select / use must **not** automatically:

- create accepted world identities
- place every object
- declare events played
- promote lore to world canon
- overwrite existing identity or mechanics
- bypass evidence/authority metadata

Required flow:

```text
pack revision
→ select/import as draft
→ resolve identities and conflicts
→ preview scoped placement/promotion
→ GM confirms
→ governed source records / GraphContribution
→ Kernel validation and publish
```

Content packs must not silently auto-canonize. Content-pack storage runtime remains deferred (later than PR005B; not PR006).

---

## K. Surface responsibility matrix

| Surface | Responsibilities | Must not |
|---|---|---|
| **Plan** | Consumes projections; drafts prep; may launch `preview_write`; shows lightweight status; escalates correction | Own identity merge, evidence reassignment, or durable commit semantics |
| **Graph Review / Ingest** | Correction and authored-memory **correction cockpit**; reviews proposals; authors assertions/decisions; orchestrates confirmed commits and diagnostics | Become a second graph store |
| **Agent Interaction** | Pointer-only continuity and tool surface; may invoke categorized tools | Store campaign canon or graph internals |
| **Build** | May author source artifacts or proposed contributions | Own a separate graph |
| **Kernel** | Owns identity, contribution merge, retraction, supersession, validation, revision publication | Be bypassed by UI/agent file writes |
| **Projection Engine** | Reads pinned revisions and enforces admissibility; never mutates | Mutate graph head or contributions |
| **Corpus / source artifacts** | Evidentiary and prose authority | Be the sole store of identity decisions or authored graph corrections |

Plan is a **consumer surface**. Graph Review/Ingest is the **correction cockpit**. Agent Interaction is **pointer-only**.

---

## L. Never-canon inputs

These do **not** become accepted campaign/world truth without the governed path:

- chat history
- UI thread history
- Hermes session memory
- Hermes long-term memory
- agent summaries
- graph summaries without source evidence
- retrieval summaries
- tool traces
- diagnostics
- drafts
- unconfirmed proposals
- rejected candidates
- stale proposals
- retracted content
- superseded content as current truth
- content-pack defaults
- generated prose merely because it was saved

Some may remain useful context or audit records. They are **not** canon.

---

## M. Deferral matrix

| Concern | belongs in PR005B | belongs in PR006 | belongs in PR007 | belongs in PR011 | belongs in later dogfood |
|---|---|---|---|---|---|
| Normative capability + authored-prep contract | **yes** | no | no | no | no |
| Active-reference re-anchors (Plan, AI, authoring, vocab) | **yes** | no | no | no | no |
| PR006 materialization handoff | **yes** (handoff only) | implement | no | no | no |
| Named acceptance-corpus materialization, coverage, health, reconstruction, first representative graph head | no | **yes** | no | no | no |
| Revision-pinned projections and admissibility | no | no | **yes** | no | no |
| Runtime tool registry, context assembly, confirmation UI/runtime, audit plumbing | no | no | no | **yes** | no |
| Hermes runtime / agent tool implementation | no | no | no | **yes** | no |
| Content-pack storage runtime | no | no | no | later / dogfood | possible |
| Benchmarks, usability, consent-policy changes | no | no | no | no | **yes** |
| Autonomous write tiers | **never** under current invariant | — | — | — | only if product explicitly revises this contract |

---

## Runtime feasibility notes (read-only inspection, 2026-07-11)

Public Kernel already exposes contribution and identity concepts (`GraphContribution`, merge/retract/supersede/rebuild, identity decision records, expected parent revision on publish). Graph Object Authoring already has prepare → diff → confirm-token stale rejection, while several authored-memory paths still target transitional overlay / preview-union stores. Agent Interaction persistence is pointer-oriented (thread metadata, locators, freshness), not campaign-canon storage. This contract aligns target semantics with those seams without requiring PR005B to change runtime code.
