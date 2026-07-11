# Jumpstart Handoff — Docs Relevance First

> Status: ACTIVE REFERENCE / PROCESS TEMPLATE
> Use for: Starting fresh agents on DungeonBuddy documentation, roadmap, or architecture work.
> Canonical repo path: `Docs/Plans/JUMPSTART-docs-relevance-first.md`
> Canonical sync rule: GitHub is canonical; local/project-attached docs are draft or source context until reconciled.
> Last updated: 2026-07-10

## 0. Mandatory first step: reconcile source docs

Before implementing, editing roadmap language, or writing a new PR handoff, inspect the documents available in the agent/project source context and compare them to GitHub.

GitHub is canonical because it is the repository. Project-attached/local files are drafts, cached references, or agent-source inputs until verified against GitHub.

Do not assume a local/project-attached doc is current merely because it is directly available.

### Required actions

1. List the local/project-attached docs available to the agent.
2. Map each local doc to its intended GitHub repo path.
3. Fetch the current GitHub version of each mapped file.
4. Classify each file:

```text
MATCH
LOCAL_AHEAD
GITHUB_AHEAD
CONFLICT
LOCAL_ONLY
GITHUB_ONLY
SUPERSEDED
RESEARCH_ONLY
SOURCE_ANCHOR
```

5. Record whether the local document can direct work:

```text
ACTIVE_AUTHORITY
ACTIVE_REFERENCE
KEEP_CONTRACT
RESEARCH_ONLY
HISTORICAL
SUPERSEDED
DELETE_CANDIDATE
```

6. If a doc is stale but useful, preserve its useful content by extracting it into the current authority doc or a clearly labeled appendix.
7. If a doc is stale and dangerous, add or update a banner pointing to current authority.
8. Only after this reconciliation should the agent edit roadmap, architecture, or PR handoff content.

## 1. Canonical sync rule

GitHub is the source of truth.

The local/project-attached copy is the editing workspace.

The workflow is:

```text
local/project docs
→ compare with GitHub
→ classify
→ edit locally
→ preview diff
→ explicit approval
→ post/update GitHub
→ fetch GitHub again
→ verify match
```

No GitHub write should happen without explicit approval.

## 2. Authority banner rule

Every edited doc must begin with a clear status banner.

Examples:

```markdown
> Status: ACTIVE AUTHORITY
> Use for: Campaign Supergraph architecture decisions.
> Canonical repo path: Docs/Design/ARCHITECTURE-campaign-supergraph.md
> Last sync checked: YYYY-MM-DD
```

```markdown
> Status: SUPERSEDED / HISTORICAL
> This document is retained for context only.
> Do not use it to direct new implementation.
> Current authority: Docs/Design/ARCHITECTURE-campaign-supergraph.md
```

```markdown
> Status: ACTIVE REFERENCE
> Use for: product or implementation context only.
> Do not override: ARCHITECTURE-campaign-supergraph.md, ROADMAP-campaign-supergraph.md, PR-TRACKER-campaign-supergraph.md
```

## 3. Jumpstart purpose

This jumpstart exists to re-anchor the roadmap position and then produce the next safe PR.

For the current workstream, the immediate target is:

```text
PR005A — Agent Tool Contract + Authored Prep Contribution Design
```

This is a docs-first refinement after PR005 and before PR006. It defines how Hermes tools, Plan-authored prep, reusable content packs, and preview-write flows fit the World Supergraph architecture without creating a second memory system.

## 4. Initial local docs to reconcile

Start with the currently available project-source docs when present:

```text
LLM-graph-construction.md
dungeonbuddy_spec_architecture_v0_2.md
ARCHITECTURE-plan-surface-toolbox.md
GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md
GRAPH-MEMORY-PROJECT-LAYOUT.md
CORPUS-ANCHOR.md
```

Expected preliminary classification:

```text
LLM-graph-construction.md
  Likely RESEARCH_ONLY / KEEP_REFERENCE.
  Useful for extraction/eval patterns, not roadmap authority.

dungeonbuddy_spec_architecture_v0_2.md
  Likely SUPERSEDED / HISTORICAL.
  Useful conceptually, but replaced by current Campaign Supergraph architecture.

ARCHITECTURE-plan-surface-toolbox.md
  ACTIVE_REFERENCE but needs patching.
  Surface composition remains useful; graph/shadow-memory framing may be stale.

GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md
  SUPERSEDED / HISTORICAL unless GitHub says otherwise.
  Useful old roadmap evidence, not current authority.

GRAPH-MEMORY-PROJECT-LAYOUT.md
  ACTIVE_REFERENCE candidate, but must be checked.
  Rewrite or demote if it points to older architecture anchors.

CORPUS-ANCHOR.md
  SOURCE_ANCHOR / KEEP.
  Still useful for corpus path grounding unless GitHub has a newer generated index.
```

## 5. Roadmap re-anchor after reconciliation

After doc reconciliation, update the roadmap position:

```text
PR001 — Architecture reset: DONE
PR002 — Storage + immutable revision / graph-head contract: DONE
PR003 — Kernel public boundary: DONE
PR004 — Identity outcomes + split/unmerge: DONE
PR005 — Durable contribution merge: DONE
PR005A — Agent tool contract + authored prep contributions: NEXT
PR006 — Initial real materialization: next implementation slice after PR005A
PR007 — Projection Engine
PR008 — Plan migration
PR009 — Play migration
PR010 — Graph-backed retrieval
PR011 — Agent Context + Tool Runtime
PR012 — Obsolete-path cleanup safety net
```

Do not renumber the roadmap unless explicitly instructed. Insert PR005A as a bridge docs slice.

## 6. PR005A mission

Define the contract by which Hermes and future agents interact with graph memory.

Core rule:

```text
Agents are not privileged graph writers.
```

Hermes may:

```text
read through projections, retrieval, source units, and diagnostics;
draft non-canonical artifacts;
prepare preview-write proposals;
commit only after explicit GM confirmation through the same Kernel write path.
```

Hermes may not:

```text
write graph internals directly;
treat Hermes memory as campaign canon;
select graph state by latest-ingest / preview-source / manifest path;
silently mutate the World Supergraph;
invent identity, evidence, merge, or projection semantics.
```

## 7. Tool categories to document

```text
read_only
draft_only
preview_write
confirm_commit
admin_diagnostic
```

Durable writes must flow through one of:

```text
GraphContribution
source artifact revision
identity decision record
Kernel merge / publish
```

## 8. Authored prep model to document

Plan-authored or Hermes-drafted material may be:

```text
draft
planned
placed
played
world_canon
retracted
superseded
```

Do not collapse these into one truth state.

Example distinction:

```text
Draft:
A possible Mireward breach encounter.

Planned:
The GM intends to use it in Session 24.

Placed:
It is connected to Mireward north gate and Shepherd siege context.

Played:
The party actually encountered it.

World canon:
The encounter/threat is now durable Elderwyld knowledge.
```

## 9. Files likely to update in GitHub

After reconciliation, expected GitHub updates are likely:

```text
Docs/Design/ARCHITECTURE-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Reports/graph-document-audit.md
Docs/Design/ANCHOR-agent-interaction-hermes.md
Docs/Design/UX-STORIES-agent-interaction-hermes.md
Docs/Design/ANCHOR-plan-surface-agent-interaction.md
Docs/Design/ARCHITECTURE-plan-surface-toolbox.md
Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md
```

Do not update all of these blindly. Update only after local-vs-GitHub reconciliation.

## 10. Required output of this jumpstart

The agent should produce:

1. A doc relevance report.
2. A local-vs-GitHub sync matrix.
3. A proposed set of doc edits.
4. A PR005A handoff or branch plan.
5. A GitHub sync preview.
6. Only after approval, GitHub updates.
7. A post-sync verification report proving GitHub matches intended local content.

## 11. Non-goals

Do not implement:

```text
Hermes runtime
Agent tool registry code
Plan encounter builder
Projection Engine
Graph-backed retrieval
content-pack storage
autonomous writes
PR006 materialization
```

Do not let the docs cleanup become an implementation PR.

## 12. Exit criteria

The jumpstart succeeds when:

```text
The agent can say which docs are current, stale, superseded, or research-only.
The roadmap points clearly to PR005A next.
Stale local/project docs no longer look like active authority.
Hermes tool behavior is documented as contract-based, not memory-store-based.
Plan-authored prep has a documented contribution model.
GitHub is synced and verified after explicit approval.
PR006 remains the next implementation slice after this docs refinement.
```
