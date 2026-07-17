---
pr_body_template: |
  ## Summary

  Define the governed agent-tool capability contract and authored-prep contribution lifecycle for the World Supergraph, re-anchor affected active-reference docs, and leave PR006 focused on initial materialization.

  ## Design deliverables

  - Added the normative agent-tool and authored-prep contract.
  - Defined draft-only, preview-write, and confirmed-write flows.
  - Defined revision-bound confirmation and stale-proposal behavior.
  - Defined authored-prep, content-pack, retraction, and supersession semantics.
  - Re-anchored Plan, Graph Review, Agent Interaction, and source-vocabulary boundaries.
  - Added the PR006 implementation handoff.
  - Updated the tracker only after all other deliverables were complete.

  ## Verification

  Paste the verbatim output from every command in §7.

  ## `git diff --stat` (§4 paths only)

  ```text
  Paste the filtered diff stat here.
  ```

  ## What stayed unchanged

  Confirm that no runtime code, graph data, corpus content, tests, schemas, APIs, Hermes runtime, Projection Engine, or PR006 materialization behavior changed.
---

# HANDOFF — PR005B: Agent Tool Contract + Authored Prep Contributions

**Created:** 2026-07-11 (UTC)  
**Status:** ACTIVE — dispatch to one external/Codex design agent. One docs/design PR. Do not split.  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Expected GitHub PR:** `#329`  
**Target base branch:** `main`  
**Suggested branch:** `campaign-supergraph/pr005b-agent-tool-authored-prep-contract`  
**Suggested PR title:** `docs(graph-memory): define agent tools and authored prep contributions`  
**Roadmap slice:** `PR005B — Agent Tool Contract + Authored Prep Contributions`  
**Tracker anchor:** `Docs/Plans/PR-TRACKER-campaign-supergraph.md`  
**Architecture anchor:** `Docs/Design/ARCHITECTURE-campaign-supergraph.md`  
**Predecessor:** GitHub PR `#328`, merged 2026-07-11 as `3c859d455cc3c63ddeae166370eb7e4cce3a9f3a`  
**Successor:** `PR006 — Initial World Supergraph Materialization`  
**Mode:** Documentation and architecture contract only. Inspect runtime seams only to avoid impossible abstractions. Do not implement them.

> The expected PR number is based on `#328` being the latest repository PR at handoff authoring time. If another PR takes `#329` before dispatch, rename this handoff to the actual planned PR number before the worker opens its PR.

---

## §1 Mission

Define the normative contract by which agents and authored prep may read, draft, preview, and—only after explicit revision-bound GM confirmation—contribute through the governed World Supergraph write path, while preserving Plan as a consumer, Graph Review/Ingest as the correction cockpit, Agent Interaction as non-canonical continuity, and PR006 as a clean initial-materialization slice.

---

## §2 Why this slice

PR328 completed `PR005A — Context Audit + Source Reanchor`. It established that GitHub is canonical, Project Sources are context inputs, the tracker is the sole sequence authority, stale architecture must not direct implementation, and the Agent Tool Contract belongs in a separate PR005B before PR006.

PR002–PR005 have already established the runtime foundations this design must respect:

```text
PR002
  World-owned persistent graph storage
  immutable revisions
  atomic graph head

PR003
  enforceable Graph Kernel public boundary

PR004
  explicit identity outcomes
  provisional identities
  merge / split / unmerge
  durable identity decisions

PR005
  GraphContribution
  idempotent merge
  supersession
  retraction
  rebuild
  approved correction replay
```

The repository now has several partial descriptions of future agent writes and authored prep:

- the tracker names five capability categories;
- Agent Interaction says writes are preview → GM confirm;
- Graph Object Authoring has a prepare/review/commit precedent;
- Plan can draft and launch workflows but must not own graph correction;
- the source vocabulary distinguishes source, lifecycle, canon, visibility, and evidence roles;
- the architecture requires all durable writes to use GraphContribution, governed identity decisions, validation, and atomic graph-head advancement.

Those pieces are directionally aligned but not yet one implementable contract. Active-reference documents still contain transitional phrases such as “corpus is canon,” “selected preview union store,” “graph as future shadow dependency,” and an immediate create-object commit exception. PR005B must reconcile those phrases without rewriting runtime code or pretending PR011 has been implemented.

This slice converts:

```text
scattered design intent
→ one normative capability and authored-prep contract
→ consistent surface boundaries
→ a clean implementation handoff for PR006
```

This slice explicitly does **not** implement:

```text
Hermes runtime
agent tool registry
autonomous graph writes
Projection Engine
graph-backed retrieval
Plan encounter builder
content-pack storage runtime
identity merge UI
new graph persistence
new source ingestion pipeline
Graph Review UX rewrite
PR006 materialization
```

---

## §3 Authoritative inputs

Read these in order before editing. GitHub `main` is canonical.

1. **`AGENTS.md`**
   - Handoff filename and PR-number convention.
   - Repo navigation and external-agent loop requirements.

2. **`.cursor/rules/external-agent-pr-loop.mdc`**
   - §4 allowlist, §5 denylist, §7 verification, and post-merge doc-sync invariants.

3. **`.cursor/skills/external-agent-pr-loop/SKILL.md`**
   - External PR procedure.
   - Review through `scripts/review_external_pr.py`.

4. **`Docs/Design/ARCHITECTURE-campaign-supergraph.md`**
   - Canonical architecture.
   - World-owned graph with campaign scopes.
   - Dual authority model.
   - GraphContribution lifecycle.
   - immutable graph-head contract.
   - mandatory epistemic, temporal, visibility, authority, and canon metadata.
   - surfaces as projection consumers.

5. **`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`**
   - PR005B is a docs/design bridge.
   - PR006 remains initial materialization.
   - PR011 remains runtime Agent Context + Tool Runtime.

6. **`Docs/Plans/PR-TRACKER-campaign-supergraph.md`**
   - Sole sequence authority.
   - Read its current stale PR005A/PR005B statuses, but do not edit it until the final task in §6.

7. **`Docs/Reports/graph-document-audit.md`**
   - Authority classifications.
   - Project Sources boundary.
   - Active-reference vs active-authority distinction.

8. **`Docs/Design/ANCHOR-agent-interaction-hermes.md`**
   - Pointer-only Agent Interaction.
   - non-canonical Hermes/UI memory.
   - source-grounded trust surfaces.
   - no autonomous writes.

9. **`Docs/Design/UX-STORIES-agent-interaction-hermes.md`**
   - Tool parity and preview-confirm stories.
   - thread continuity and freshness behavior.
   - current “corpus canon” shorthand that needs dual-authority refinement.

10. **`Docs/Design/DESIGN-graph-object-authoring-surface.md`**
    - Existing prepare/review/commit safety precedent.
    - Graph Review ownership.
    - transitional overlay/preview-union descriptions that must be clearly labeled transitional.

11. **`Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`**
    - Plan/Surface composition.
    - shared projection container and Agent Interaction target.
    - current Plan boundary.
    - stale lower-section corpus-only / shadow-ladder language to re-anchor.

12. **`Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md`**
    - `SourceArtifact → SourceAnchor → SourceUnit`.
    - existing `CanonState`, `LifecycleState`, `AuthorityState`, `VisibilityState`, and `EvidenceRole`.
    - this contract remains source-facing and must not become the authored-prep state machine.

13. **`Docs/Plans/JUMPSTART-docs-relevance-first.md`**
    - GitHub-first reconciliation process.
    - current-target language that should become timeless or point to the tracker/current handoff.

14. **GitHub PR #328**
    - Verify it is merged:
      ```bash
      gh pr view 328 --json number,state,mergedAt,mergeCommit,title
      ```

### Runtime context to inspect narrowly, read-only

Use SymDex or targeted symbol/file reads. Do not broadly dump directories.

```text
src/graph_memory/kernel/
src/graph_memory/evidence/
src/graph_memory/world_supergraph/
apps/live_control_server/services/graph_object_authoring_prepare.py
apps/live_control_server/services/graph_object_authoring_commit.py
apps/live_control_server/services/graph_authoring_event_log.py
apps/live_control_server/services/graph_authoring_overlay_projection.py
apps/live_control_server/services/live_agent_loop.py
apps/live-control-ui/src/planSurface/
```

Answer only these implementation-feasibility questions:

```text
What public Kernel concepts already exist for contributions and identity decisions?
What fields already identify source revisions and graph parent/head revisions?
What stale-confirm or prepare-token precedent exists?
Which existing authored-memory paths still target preview overlays/stores?
What Agent Interaction state is pointer-only vs content-bearing?
```

Do not change runtime files based on these reads.

---

## §4 Files in scope (allowlist)

The expected diff must be expressible entirely from this table.

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md` | Normative PR005B contract for capability categories, proposal/confirmation semantics, authored-prep lifecycle, content packs, surface boundaries, and deferrals. |
| Modify | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Add a concise normative Agent Tool / Authored Prep section and link to the detailed contract; preserve existing architecture decisions. |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Point Phase 2.5 and PR011 implementation language at the new contract; keep PR006 clean. |
| Modify | `Docs/Reports/graph-document-audit.md` | Classify the new contract as `KEEP_CONTRACT` / active design contract without changing sequence authority. |
| Modify | `Docs/Design/ANCHOR-agent-interaction-hermes.md` | Align Agent Interaction with dual authority, typed capability categories, revision-bound preview-confirm, and non-canonical continuity. |
| Modify | `Docs/Design/UX-STORIES-agent-interaction-hermes.md` | Refine user stories for draft, preview, confirmation, fresh reads, retraction, supersession, and content-pack use. |
| Modify | `Docs/Design/DESIGN-graph-object-authoring-surface.md` | Mark preview-union/overlay mechanics as transitional and align the target write flow with GraphContribution, Kernel validation, and graph-head advancement. |
| Modify | `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` | Re-anchor Plan away from corpus-only/shadow-ladder authority language; preserve Plan as a consumer that may draft and launch preview-write flows. |
| Modify | `Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md` | Add a mapping/boundary note: source-envelope lifecycle fields do not replace authored-prep or GraphContribution state. |
| Modify | `Docs/Plans/JUMPSTART-docs-relevance-first.md` | Remove stale “PR005A is the immediate target” state; make it a timeless reconciliation process and point current sequencing to the tracker/handoff. |
| Create | `Docs/Plans/HANDOFF-pr330-initial-world-supergraph-materialization.md` | Clean successor handoff for PR006, focused only on the named acceptance corpus, materialization, coverage, health, reconstruction, and runtime graph availability. |
| Modify last | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Final task only: record PR005A complete via GitHub #328 and PR005B as the current PR while leaving PR006 blocked until post-merge sync. |

> The tracker is deliberately listed as **Modify last**. Do not use a tracker edit as a substitute for completing the design contract and successor handoff.

If a listed active-reference file requires no semantic change after inspection, it may remain untouched. Do not add replacement files or broaden the allowlist without explaining the necessity in the PR body before opening the PR.

---

## §5 Files explicitly out of scope (denylist)

Do not touch any of these paths.

| Path | Why this PR must not touch it |
|---|---|
| `src/**` | PR005B is not runtime or Kernel implementation. |
| `apps/**` | No UI, API, Agent Interaction, Plan, Play, or Graph Review implementation in this slice. |
| `tests/**` | No runtime behavior is changing; verification is documentation-contract validation. |
| `evals/**` | No extraction, benchmark, or graph dogfood work. |
| `corpus/**` | No campaign/world source mutation or materialization. |
| `out/**` | No generated graph runs. |
| `integrations/hermes/**` | Hermes runtime/tool implementation belongs to PR011. |
| `.hermes.md` | Runtime policy changes are deferred to PR011. |
| `.cursor/**` | Do not modify workflow rules/templates while using them. |
| `scripts/**` | No tooling changes. |
| Graph revision, contribution, decision, or preview-store data | This PR defines contracts; it does not produce durable graph writes. |
| `Docs/Design/DESIGN-ingest-surface.md` | Current route boundary is already sufficient; link changes are not required for PR005B. |
| Any archive tree except where an existing link must remain valid | Historical evidence must not be rewritten into apparent current authority. |

If a denied path seems necessary, stop and explain the conflict in the PR description rather than editing it.

---

## §6 Implementation contract

### 6.1 Start with a short verification note

Before editing, record in the PR body or commit notes:

```text
PR328 merged: yes/no
main commit inspected:
tracker PR005A status before this PR:
tracker PR005B status before this PR:
authority docs read:
active-reference conflicts found:
```

If PR328 is not merged, stop. Do not silently proceed from the uploaded jumpstart.

### 6.2 Create the central normative contract

Create:

```text
Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md
```

Required banner:

```markdown
> Status: KEEP_CONTRACT / ACTIVE DESIGN CONTRACT
> Use for: Agent tool capabilities, authored-prep lifecycle, preview/confirmation semantics, content-pack contribution framing, and surface/write-path boundaries.
> Do not use for: Runtime tool registry implementation, Projection Engine, graph-backed retrieval, or PR006 materialization.
> Architecture authority: Docs/Design/ARCHITECTURE-campaign-supergraph.md
> Sequence authority: Docs/Plans/PR-TRACKER-campaign-supergraph.md
> Runtime implementation phase: PR011
> Last sync checked: 2026-07-11
```

The contract must include the following sections.

#### A. Inherited invariants

State these as normative:

```text
One World Supergraph per worldId.
Campaign is scope, not graph ownership.
Sessions are lenses.
Read and write paths remain separate.
Agents are not privileged graph writers.
No agent writes graph/storage internals.
No agent advances graph head directly.
No agent selects graph state by latest-ingest, preview-source, manifest, or store path.
No chat, UI thread, Hermes memory, summary, trace, or diagnostic becomes campaign canon.
Every durable write uses governed source/decision records, GraphContribution where applicable, Kernel merge, validation, and atomic graph-head advancement.
Every durable assertion preserves authority, epistemic kind, acceptance state, temporal scope, visibility, campaign/world scope, evidence/provenance, and contribution lineage.
```

#### B. Capability taxonomy

Use exactly these categories:

```text
read_only
draft_only
preview_write
confirm_commit
admin_diagnostic
```

Provide a table with at least:

```text
category
purpose
allowed inputs
allowed outputs
durable effect
required confirmation
allowed surfaces
required context/revision pin
audit expectations
implementation phase
```

Required semantics:

- `read_only`
  - Reads projections, source units, diagnostics, node views, evidence, health, retrieval outputs, source anchors.
  - No durable effect.
  - May require an explicit graph revision pin or coherent request snapshot.
- `draft_only`
  - Produces speculative prep or artifacts.
  - No durable graph effect merely because text exists.
  - Saving a draft may create a revisioned non-canonical source artifact, but must not create accepted graph truth unless separately promoted through preview/confirmation.
- `preview_write`
  - Produces a reviewable proposed effect and diff.
  - No durable graph effect.
  - Must identify affected source records, assertions, identities, visibility/canon/epistemic fields, validation findings, expected parent graph revision, and conflicts.
- `confirm_commit`
  - Is not autonomous authority.
  - May execute only with explicit GM confirmation bound to one current proposal.
  - Invokes the normal governed write path.
  - Must fail closed when the proposal, source revision, identity outcome, or expected parent graph revision is stale or materially changed.
- `admin_diagnostic`
  - Reads health/integrity/replay/conflict information.
  - No durable effect unless followed by a separate preview-confirm operation.

#### C. Common invocation context

Define a conceptual, implementation-neutral envelope. Do not add runtime schemas.

It must cover:

```text
actor / confirming principal
surface
worldId
campaignId?
focus?
admissibility / visibility policy
graph revision pin or expected parent revision
source artifact + revision pins
thread/draft pointers
tool capability category
correlation / audit id
```

Clarify:

```text
A thread pointer is context, not authority.
A surface context is scope, not ownership.
A graph revision pin is coherence, not permission.
```

#### D. Draft-only flow

Required flow:

```text
human or agent idea
→ draft in UI/thread/tool
→ optional revisioned draft artifact
→ draft/prep projection only
→ no accepted graph assertion
```

Define when the result is:

- ephemeral/no durable write;
- a saved non-canonical source artifact revision;
- eligible for a later preview-write proposal.

#### E. Preview-write proposal contract

Define a proposal that includes at least:

```text
proposal_id
proposal_version
proposal_digest
created_by
created_at
world/campaign target
source revision pins
expected parent graph revision
proposed source artifact revisions
proposed GraphContribution assertions
proposed identity/alias decisions
visibility/canon/epistemic/temporal metadata
validation and collision diagnostics
human-readable diff
machine-readable effect summary
confirmation requirement
stale/expiry behavior
```

A preview is not canon, not a graph revision, and not a contribution accepted into the graph.

#### F. Explicit confirmation contract

State clearly:

```text
A generic “yes” in chat is not sufficient durable authorization unless the product binds it to one visible proposal.
Confirmation must identify the proposal id/version/digest and confirming principal.
Confirmation must occur after the human-readable effect is available.
Confirmation does not waive validation, identity policy, visibility policy, or stale-parent checks.
```

Require stale confirmation behavior:

```text
If the source revision, proposal digest, identity outcome, or expected parent graph revision changes materially:
  reject confirm_commit
  return a stale/conflict result
  require refreshed preview and new confirmation
```

Do not invent cryptographic or transport implementation details beyond what the contract needs.

#### G. Confirmed write flow

Include this diagram or equivalent:

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

Clarify branches:

- source-text editing creates a source revision, then contributes through normal ingestion/merge;
- authored graph assertions may create governed authored source records and GraphContributions without rewriting prose;
- identity/alias/merge/split/unmerge uses governed identity decision records;
- rejected validation leaves the prior head readable;
- no UI or agent writes graph files directly.

#### H. Authored-prep lifecycle

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

```text
authored-prep lifecycle
graph assertion acceptance state
epistemic kind
authority class
visibility
campaign/world scope
temporal validity
source/contribution status
```

Required lifecycle table columns:

```text
state
meaning
source representation
graph representation
projection visibility
promotion trigger
required confirmation
retraction/supersession behavior
```

Required semantics:

- `draft`
  - speculative;
  - no accepted graph assertion required;
  - visible only in draft/prep contexts.
- `planned`
  - the GM intends possible future use;
  - represented as `plan`, not fact or played event;
  - may be durable after explicit save/confirmation;
  - normally GM-private.
- `placed`
  - linked to a location, faction, session, encounter, node, or prep window;
  - placement is scoped plan metadata, not proof that it occurred.
- `played`
  - supported by an actual-play source, recap, or explicit GM played-event assertion;
  - must not be produced by merely relabeling the original plan;
  - divergences between plan and play remain inspectable.
- `world_canon`
  - explicit durable world-level acceptance;
  - must not be inferred automatically from `planned`, `placed`, or `played`;
  - promotion must preserve campaign-specific facts rather than making them world-universal.
- `retracted`
  - withdrawn/invalidated;
  - retained for audit and replay;
  - excluded from current truth projections.
- `superseded`
  - replaced by a newer source revision or contribution;
  - remains historical;
  - is not current truth.

Include examples for:

```text
Mireward breach encounter:
draft → planned → placed
actual table event differs → played record from recap
only durable surviving world consequences become world_canon

NPC draft:
draft → planned → placed at an inn
never used → retracted

content-pack statblock:
pack revision v1 → placed in campaign
v2 replaces mechanics → superseded, not silently overwritten
```

#### I. Transition-to-durable-object mapping

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

Include the rule:

```text
A lifecycle label alone never performs a graph mutation.
A governed record/contribution performs the durable effect.
```

#### J. Content packs and reusable prep

Define content packs as revisioned source artifacts or bundles that may contain:

```text
prose
draft objects
relationship templates
statblocks/mechanics
placement hooks
visibility defaults
proposed contribution material
```

Import/select/use must not automatically:

```text
create accepted world identities
place every object
declare events played
promote lore to world canon
overwrite existing identity or mechanics
bypass evidence/authority metadata
```

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

Content-pack storage runtime remains deferred.

#### K. Surface responsibility matrix

Define responsibilities for:

```text
Plan
Graph Review / Ingest
Agent Interaction
Build
Kernel
Projection Engine
Corpus / source artifacts
```

Normative boundaries:

- **Plan**
  - consumes projections;
  - drafts prep;
  - may launch preview-write;
  - shows lightweight status;
  - escalates correction;
  - does not own identity merge, evidence reassignment, or durable commit semantics.
- **Graph Review / Ingest**
  - correction and authored-memory cockpit;
  - reviews proposals;
  - authors assertions/decisions;
  - orchestrates confirmed commits and diagnostics.
- **Agent Interaction**
  - pointer-only continuity and tool surface;
  - may invoke categorized tools;
  - stores no campaign canon or graph internals.
- **Build**
  - may author source artifacts or proposed contributions;
  - owns no separate graph.
- **Kernel**
  - owns identity, contribution merge, retraction, supersession, validation, revision publication.
- **Projection Engine**
  - reads pinned revisions and enforces admissibility;
  - never mutates.
- **Corpus/source artifacts**
  - evidentiary and prose authority;
  - not the sole store of identity decisions or authored graph corrections.

#### L. Never-canon inputs

List explicitly:

```text
chat history
UI thread history
Hermes session memory
Hermes long-term memory
agent summaries
graph summaries without source evidence
retrieval summaries
tool traces
diagnostics
drafts
unconfirmed proposals
rejected candidates
stale proposals
retracted content
superseded content as current truth
content-pack defaults
generated prose merely because it was saved
```

Some may remain useful context or audit records. They do not become accepted campaign/world truth without the governed path.

#### M. Deferral matrix

Required columns:

```text
belongs in PR005B
belongs in PR006
belongs in PR007
belongs in PR011
belongs in later dogfood
```

At minimum:

- PR005B: docs/design contracts only.
- PR006: named acceptance-corpus materialization, coverage, health, reconstruction, first representative graph head.
- PR007: revision-pinned projections and admissibility.
- PR011: runtime tool registry, context assembly, confirmation UI/runtime, audit plumbing.
- later dogfood: benchmarks, usability, possible future consent-policy changes.

### 6.3 Update canonical architecture concisely

In `ARCHITECTURE-campaign-supergraph.md`:

- add a concise section that:
  - points to the new detailed contract;
  - names the five capability categories;
  - states no agent is a privileged writer;
  - defines explicit revision-bound confirmation;
  - distinguishes authored prep from played/world canon;
  - states that PR011 implements the contract;
  - preserves the existing dual-authority and write-path model.
- do not duplicate the full contract.
- do not change tenancy, graph-head, contribution, identity, or PR006 decisions.

### 6.4 Re-anchor Agent Interaction docs

In the Agent Interaction anchor and UX stories:

Replace compressed phrases such as:

```text
corpus remains canon
every thread reads and writes live corpus state
```

with the precise model:

```text
corpus/source artifacts are prose and evidentiary authority
the World Supergraph head is durable materialized knowledge state
governed authored assertions and identity decisions survive reconstruction
Hermes/UI/thread memory is non-canonical continuity
```

Add/refine stories for:

```text
draft without commit
save draft artifact
preview exact effect
explicit proposal-bound confirmation
stale preview rejection
fresh post-commit reads across threads
retraction
supersession
content-pack import and placement
```

Do not claim the runtime already supports these.

### 6.5 Re-anchor Graph Object Authoring

In `DESIGN-graph-object-authoring-surface.md`:

- preserve the current implementation checkpoint as historical/transitional truth;
- clearly label these as transitional:
  - authored overlay/event log as current implementation destination;
  - selected preview union store materialization;
  - selected live store preference;
  - immediate create-object commit.
- state the target write path from the new contract;
- eliminate any apparent exception to explicit confirmation:
  - a create-object wizard may be a compact review+confirm interaction;
  - object creation itself is not implicit confirmation;
- preserve Graph Review as the correction cockpit;
- do not redesign the UI.

### 6.6 Re-anchor Plan Surface Toolbox

In `ARCHITECTURE-plan-surface-toolbox.md`:

- preserve SurfaceConfig, shared resolver, one projection container, edit capability, and Plan composition;
- update stale lower-section statements that imply:
  - corpus-on-disk is the only durable authority;
  - graph is merely future shadow infrastructure;
  - ontology ladder remains the current owner of production graph semantics.
- use the current boundary:
  - source editing → source revision path;
  - prep drafting → draft-only;
  - proposed memory change → preview-write;
  - correction/commit → Graph Review / governed Kernel path;
  - Plan does not own durable commit semantics.

### 6.7 Map the source vocabulary without merging state machines

In `CONTRACT-surface-vocabulary-boundary-v0.md`:

Add a clear note/table:

```text
SourceArtifact/SourceAnchor/SourceUnit lifecycle fields
  describe source-facing envelopes and evidence roles.

Authored-prep lifecycle
  describes draft/planned/placed/played/world-canon history.

GraphContribution status
  describes contribution activation/supersession/retraction.

Assertion acceptance/epistemic/visibility metadata
  describes durable graph meaning and admissibility.
```

No one enum replaces the others.

Do not redesign the existing source envelope.

### 6.8 Make the docs-relevance jumpstart timeless

In `JUMPSTART-docs-relevance-first.md`:

- preserve the reconciliation process;
- remove stale wording that says PR005A is the immediate current slice;
- point current work selection to the tracker;
- point PR005B-specific starts to:
  - this handoff while active;
  - the new contract after merge.
- do not create a second sequence.

### 6.9 Add the clean PR006 handoff

Create:

```text
Docs/Plans/HANDOFF-pr330-initial-world-supergraph-materialization.md
```

Follow the repository §1–§9 handoff structure.

Its mission must remain:

```text
Materialize the first representative Eldyrwild World Supergraph from the named Longmont Campaign 2 acceptance corpus and prove coverage, provenance, reconstruction, health, and runtime graph-head availability without implementing projection or agent tooling.
```

It must include:

```text
Eldyrwild worldId
Longmont Campaign 2 scope
canonical C2 Sessions 1–23
all approved C2 PC hubs
required Mirathorn and Mireward world hubs
needed C2 NPC/faction/location hubs
required statblocks/encounters
approved Graph Review assertions / identity decisions in scope
requested / ingested / skipped inventory
entity/edge counts by source domain
identity diagnostics
evidence coverage
unsupported projection requirements
what Plan can and cannot trust
graph-head advancement
reconstruction/replay proof
removal/quarantine of preview runtime availability dependence
```

It must explicitly exclude:

```text
Agent Interaction runtime
tool registry
preview-confirm UX
Projection Engine
Plan migration
content-pack runtime
autonomous writes
```

Do not let the PR006 handoff turn into a continuation of PR005B.

### 6.10 Final content edit: update the tracker

This is the final deliverable and final content edit of the worker’s PR.

Only after all earlier documents and the PR006 handoff are complete and §7 contract checks pass, edit:

```text
Docs/Plans/PR-TRACKER-campaign-supergraph.md
```

Required state:

```text
PR005A
  Status: DONE
  GitHub #328
  merged 2026-07-11
  note that Context Audit + Source Reanchor completed

PR005B
  Status: DOING (GitHub #329) if the PR number exists
  otherwise READY while the branch/handoff is prepared

PR006
  remains BLOCKED on PR005B
```

Important:

```text
Do not mark PR005B DONE inside its own branch.
Do not mark PR006 READY inside this PR.
Those are post-merge doc-sync actions after #329 merges.
```

Do not renumber PR006–PR012.

### 6.11 Post-merge dispatcher obligation

The external worker does not perform this while authoring the PR. The dispatcher must perform atomic post-merge doc-sync:

```text
PR005B → DONE (GitHub #329, merge date/hash)
PR006 → READY
archive/update this handoff status
ensure the PR006 handoff is the next active dispatch
```

Use `scripts/review_external_pr.py merge 329` and the external-agent doc-sync procedure.

---

## §7 Verification commands

The worker must run every command and paste verbatim output into the PR body. The reviewer reruns them.

```bash
# 1. Confirm predecessor state.
gh pr view 328 --json number,state,mergedAt,mergeCommit,title
```

```bash
# 2. Documentation whitespace and patch sanity.
git diff --check
```

```bash
# 3. Exact allowlist enforcement.
uv run python -c '
from pathlib import Path
import subprocess
allowed = {
    "Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md",
    "Docs/Design/ARCHITECTURE-campaign-supergraph.md",
    "Docs/Roadmaps/ROADMAP-campaign-supergraph.md",
    "Docs/Reports/graph-document-audit.md",
    "Docs/Design/ANCHOR-agent-interaction-hermes.md",
    "Docs/Design/UX-STORIES-agent-interaction-hermes.md",
    "Docs/Design/DESIGN-graph-object-authoring-surface.md",
    "Docs/Design/ARCHITECTURE-plan-surface-toolbox.md",
    "Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md",
    "Docs/Plans/JUMPSTART-docs-relevance-first.md",
    "Docs/Plans/HANDOFF-pr330-initial-world-supergraph-materialization.md",
    "Docs/Plans/PR-TRACKER-campaign-supergraph.md",
}
changed = set(subprocess.check_output(
    ["git", "diff", "--name-only", "origin/main...HEAD"],
    text=True,
).splitlines())
extra = sorted(changed - allowed)
assert not extra, f"Files outside §4 allowlist: {extra}"
assert "Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md" in changed
assert "Docs/Plans/HANDOFF-pr330-initial-world-supergraph-materialization.md" in changed
assert "Docs/Plans/PR-TRACKER-campaign-supergraph.md" in changed
print("allowlist ok")
print("\n".join(sorted(changed)))
'
```

```bash
# 4. Central-contract required vocabulary and flows.
uv run python -c '
from pathlib import Path
p = Path("Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md")
text = p.read_text()
required = [
    "read_only",
    "draft_only",
    "preview_write",
    "confirm_commit",
    "admin_diagnostic",
    "draft",
    "planned",
    "placed",
    "played",
    "world_canon",
    "retracted",
    "superseded",
    "proposal_id",
    "proposal_digest",
    "expected parent graph revision",
    "GraphContribution",
    "identity decision",
    "atomic graph-head",
    "Plan",
    "Graph Review",
    "Agent Interaction",
    "content pack",
    "PR006",
    "PR007",
    "PR011",
]
missing = [s for s in required if s.lower() not in text.lower()]
assert not missing, f"Missing contract terms: {missing}"
print("central contract vocabulary ok")
'
```

```bash
# 5. Explicit safety invariants are present.
rg -n \
  "not privileged|must not silently|explicit.*confirm|proposal.*digest|stale|prior head|no durable effect|not.*canon|does not.*canon" \
  Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md
```

```bash
# 6. Cross-document dual-authority and surface-boundary reanchor.
rg -n \
  "prose.*authority|evidentiary authority|materialized knowledge|governed authored|GraphContribution|correction cockpit|consumer surface|pointer-only" \
  Docs/Design/ARCHITECTURE-campaign-supergraph.md \
  Docs/Design/ANCHOR-agent-interaction-hermes.md \
  Docs/Design/UX-STORIES-agent-interaction-hermes.md \
  Docs/Design/DESIGN-graph-object-authoring-surface.md \
  Docs/Design/ARCHITECTURE-plan-surface-toolbox.md
```

```bash
# 7. Source vocabulary remains a separate envelope/state dimension.
rg -n \
  "SourceArtifact.*SourceAnchor.*SourceUnit|authored-prep|GraphContribution|does not replace|separate.*lifecycle|separate.*state" \
  Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md
```

```bash
# 8. PR006 successor handoff remains materialization-only.
uv run python -c '
from pathlib import Path
p = Path("Docs/Plans/HANDOFF-pr330-initial-world-supergraph-materialization.md")
text = p.read_text().lower()
required = [
    "sessions 1–23",
    "mirathorn",
    "mireward",
    "coverage",
    "health",
    "reconstruction",
    "graph head",
    "what plan can",
    "projection engine",
    "agent",
]
missing = [s for s in required if s not in text]
assert not missing, f"Missing PR006 handoff terms: {missing}"
for forbidden_claim in [
    "implement hermes runtime",
    "implement agent tool registry",
    "implement projection engine",
    "autonomous graph writes",
]:
    assert forbidden_claim not in text, forbidden_claim
print("PR006 handoff scope ok")
'
```

```bash
# 9. Tracker final-state check.
uv run python -c '
from pathlib import Path
text = Path("Docs/Plans/PR-TRACKER-campaign-supergraph.md").read_text()
assert "PR005A — Context Audit + Source Reanchor" in text
section_a = text.split("## PR005A — Context Audit + Source Reanchor", 1)[1].split("---", 1)[0]
section_b = text.split("## PR005B — Agent Tool Contract + Authored Prep Contributions", 1)[1].split("---", 1)[0]
section_6 = text.split("## PR006 — Initial World Supergraph Materialization", 1)[1].split("---", 1)[0]
assert "`DONE`" in section_a and "#328" in section_a
assert ("`DOING`" in section_b and "#329" in section_b) or "`READY`" in section_b
assert "`BLOCKED` on PR005B" in section_6
print("tracker state ok")
'
```

```bash
# 10. No roadmap renumbering and no accidental runtime paths.
rg -n "^PR00(6|7|8|9)|^PR01(0|1|2)" Docs/Plans/PR-TRACKER-campaign-supergraph.md
test -z "$(git diff --name-only origin/main...HEAD | grep -v '^Docs/')"
```

```bash
# 11. Reviewer-facing diff.
git diff --stat origin/main...HEAD -- \
  Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md \
  Docs/Design/ARCHITECTURE-campaign-supergraph.md \
  Docs/Roadmaps/ROADMAP-campaign-supergraph.md \
  Docs/Reports/graph-document-audit.md \
  Docs/Design/ANCHOR-agent-interaction-hermes.md \
  Docs/Design/UX-STORIES-agent-interaction-hermes.md \
  Docs/Design/DESIGN-graph-object-authoring-surface.md \
  Docs/Design/ARCHITECTURE-plan-surface-toolbox.md \
  Docs/Design/CONTRACT-surface-vocabulary-boundary-v0.md \
  Docs/Plans/JUMPSTART-docs-relevance-first.md \
  Docs/Plans/HANDOFF-pr330-initial-world-supergraph-materialization.md \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md
```

---

## §8 Reporting contract

The PR body must include:

1. **Predecessor verification**
   - PR328 merged status, date, and merge commit.
   - tracker state before this PR.

2. **Contract summary**
   - one paragraph explaining the capability taxonomy;
   - one paragraph explaining authored-prep lifecycle;
   - one paragraph explaining proposal-bound confirmation and stale behavior.

3. **Surface-boundary summary**
   - Plan;
   - Graph Review/Ingest;
   - Agent Interaction;
   - Kernel;
   - Projection Engine;
   - corpus/source artifacts.

4. **State-machine separation**
   - explain why source-envelope lifecycle, authored-prep lifecycle, GraphContribution status, and assertion epistemic/canon metadata remain separate.

5. **PR006 protection**
   - state exactly how the successor handoff excludes Agent Tool Runtime and Projection Engine.

6. **Tracker final edit**
   - show PR005A `DONE (#328)`;
   - PR005B `DOING (#329)` or `READY`;
   - PR006 still blocked.

7. **`git diff --stat`**
   - filtered to §4 allowlist only.

8. **Verbatim §7 outputs**

9. **What stayed unchanged**
   - no runtime code;
   - no APIs or schemas;
   - no graph/corpus data;
   - no materialization;
   - no tool registry;
   - no Projection Engine;
   - no autonomous write policy.

10. **Retain / rewrite / delete**
    - Retained: runtime/transitional paths unchanged.
    - Rewritten: documentation authority and target semantics only.
    - Deleted: no runtime paths; stale wording may be removed.
    - Required future deletion: preview runtime selectors remain owned by PR006–PR008/PR012 per tracker.

---

## §9 Acceptance rubric

The reviewer accepts only if every item is true.

- [ ] The new central contract contains all five exact capability categories and defines their allowed inputs, outputs, durable effects, confirmation requirements, surfaces, revision context, audit expectations, and implementation phase — verified by §7 commands 4 and 5.
- [ ] `confirm_commit` is explicitly non-autonomous and requires proposal-bound GM confirmation identifying proposal version/digest and expected parent graph revision — verified by §7 commands 4 and 5.
- [ ] Stale proposals fail closed and require a refreshed preview when source revisions, identity outcomes, proposal digest, or parent graph revision materially change — verified by §7 command 5.
- [ ] The authored-prep lifecycle uses all seven required states and does not collapse lifecycle, epistemic kind, acceptance, authority, visibility, scope, and contribution status into one enum — verified by §7 commands 4 and 7.
- [ ] `played` requires actual-play evidence or an explicit played-event assertion and is not implemented conceptually as a direct relabel of `planned` — verified by inspection of the central contract and §7 command 4.
- [ ] `world_canon` requires explicit promotion and does not automatically universalize campaign-scoped plans or played events — verified by inspection of the central contract and §7 command 4.
- [ ] Content packs are revisioned draft/source bundles whose import, placement, identity resolution, and promotion require preview-confirm; they never auto-canonize — verified by §7 commands 4 and 5.
- [ ] Plan remains a projection consumer and draft/preview launcher, not the owner of identity merge, evidence reassignment, or durable commit semantics — verified by §7 command 6.
- [ ] Graph Review/Ingest remains the correction and authored-memory cockpit — verified by §7 command 6.
- [ ] Agent Interaction remains pointer-only and non-canonical; Hermes/UI/thread memory is not campaign truth — verified by §7 command 6.
- [ ] Active-reference docs use the current dual-authority model rather than the compressed claim that corpus-on-disk is the only authority — verified by §7 command 6.
- [ ] Preview-union/overlay/immediate-commit language in Graph Object Authoring is clearly transitional and does not appear as the target architecture — verified by inspection and §7 command 6.
- [ ] The source vocabulary contract explicitly remains a source/evidence envelope and does not replace authored-prep or contribution state machines — verified by §7 command 7.
- [ ] The PR006 handoff is complete, implementation-ready, and remains focused on initial materialization, coverage, health, reconstruction, and runtime world-head availability — verified by §7 command 8.
- [ ] The tracker update is the final content edit, records PR005A `DONE (#328)`, keeps PR005B current rather than done, and leaves PR006 blocked until post-merge sync — verified by §7 command 9 and commit/diff inspection.
- [ ] PR006–PR012 are not renumbered — verified by §7 command 10.
- [ ] No runtime, test, eval, corpus, Hermes, script, or graph-data files changed — verified by §7 commands 3 and 10.
- [ ] Every changed file is inside the §4 allowlist — verified by §7 command 3.
- [ ] `git diff --check` passes — verified by §7 command 2.

---

## §10 Out-of-band notes

- This is a design PR, but it must be concrete enough that PR011 can implement typed tools without re-litigating confirmation, state ownership, or canon semantics.
- Do not “future-proof” by inventing autonomous-write tiers. The current invariant is explicit human confirmation for every durable agent-proposed write.
- Do not turn every draft save into a GraphContribution. The contract must preserve an inexpensive draft-only path.
- Do not make `played` or `world_canon` a convenience boolean on a prep object. Preserve provenance and divergent histories.
- Do not require corpus prose rewrites for every graph correction. The architecture already supports durable authored assertions and identity decisions.
- Do not treat graph summaries as evidence. Evidence still resolves to source-grounded units where factual support matters.
- Do not update Project Sources. This PR changes GitHub docs only.
- The post-merge dispatcher must complete the external-agent cycle atomically: merge, mark PR005B done, mark PR006 ready, and set the PR006 handoff active.
