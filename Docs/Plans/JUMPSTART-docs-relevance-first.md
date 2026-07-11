# Jumpstart Handoff — Docs Relevance First

> Status: ACTIVE REFERENCE / PROCESS TEMPLATE
> Use for: Starting fresh agents on DungeonBuddy documentation, roadmap, or architecture work.
> Canonical repo path: `Docs/Plans/JUMPSTART-docs-relevance-first.md`
> Canonical sync rule: GitHub is canonical; local/project-attached docs are draft or source context until reconciled.
> Sequence authority: If this jumpstart and `Docs/Plans/PR-TRACKER-campaign-supergraph.md` disagree, the tracker wins.
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

This jumpstart exists to re-anchor documentation authority and then produce the next safe PR.

For the current workstream, the immediate target is:

```text
PR005A — Context Audit + Source Reanchor
```

followed by:

```text
PR005B — Agent Tool Contract + Authored Prep Contributions
```

**If the tracker and this jumpstart disagree, the tracker wins.**

PR005A is docs/process: classify Project Sources and local docs, banner stale authority, and lock the GitHub-canonical rule before any agent-tool design work. PR005B is the subsequent docs/design bridge for Hermes tool categories and authored prep — still before PR006 materialization, and still without runtime implementation.

## 4. Initial local docs to reconcile

Start with the currently available project-source docs when present:

```text
PROJECT-SOURCES-OPERATING-TEMPLATE.md
PROPOSAL-context-audit-source-reanchor.md
LLM-graph-construction.md
dungeonbuddy_spec_architecture_v0_2.md
ARCHITECTURE-plan-surface-toolbox.md
GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md
GRAPH-MEMORY-PROJECT-LAYOUT.md
CORPUS-ANCHOR.md
```

Expected preliminary classification:

```text
PROJECT-SOURCES-OPERATING-TEMPLATE.md
  ACTIVE OPERATING TEMPLATE / local process rule.
  Process only; cannot override the PR tracker.

PROPOSAL-context-audit-source-reanchor.md
  PROPOSAL.
  Useful intent; not authority until absorbed into tracker/audit.

LLM-graph-construction.md
  RESEARCH_ONLY.
  Useful for extraction/eval patterns, not roadmap authority.

dungeonbuddy_spec_architecture_v0_2.md
  SUPERSEDED / HISTORICAL.
  Useful conceptually, but replaced by current Campaign Supergraph architecture.

ARCHITECTURE-plan-surface-toolbox.md
  ACTIVE_REFERENCE.
  Surface composition remains useful; not Campaign Supergraph sequencing authority.
  Corpus-index resolution is a valid fallback, not the final graph architecture.

GRAPH-MEMORY-SUPERGRAPH-ARCHITECTURE-ROADMAP.md
  SUPERSEDED / HISTORICAL.
  Useful old roadmap evidence, not current authority.

GRAPH-MEMORY-PROJECT-LAYOUT.md
  ACTIVE_REFERENCE.
  Layout note; sequencing lives in the tracker.

CORPUS-ANCHOR.md
  SOURCE_ANCHOR / KEEP.
  Still useful for corpus path grounding unless GitHub has a newer generated index.
```

## 5. Roadmap re-anchor after reconciliation

After doc reconciliation, update the roadmap position from the **tracker** (not from this jumpstart alone):

```text
PR001 — Architecture reset: DONE
PR002 — Storage + immutable revision / graph-head contract: DONE
PR003 — Kernel public boundary: DONE
PR004 — Identity outcomes + split/unmerge: DONE
PR005 — Durable contribution merge: DONE
PR005A — Context Audit + Source Reanchor: NEXT (this jumpstart / docs bridge)
PR005B — Agent Tool Contract + Authored Prep Contributions: after PR005A
PR006 — Initial real materialization: next implementation slice after docs bridges
PR007 — Projection Engine
PR008 — Plan migration
PR009 — Play migration
PR010 — Graph-backed retrieval
PR011 — Agent Context + Tool Runtime
PR012 — Obsolete-path cleanup safety net
```

Do not renumber PR006–PR012. Insert PR005A / PR005B as docs/design bridge slices only.

## 6. PR005A mission

Reconcile Project Sources, local handoffs, active references, historical docs, and repo authority so agents cannot treat stale context as GitHub truth.

Core rule:

```text
GitHub repo docs are canonical.
Project Sources are context inputs.
Prepared replacement files are not active Project Sources until the human operator uploads them.
Historical / research / proposal docs cannot direct implementation.
```

## 7. PR005B preview (do not implement in PR005A)

After PR005A lands, PR005B documents Hermes/agent tool contracts.

Core rule:

```text
Agents are not privileged graph writers.
```

Tool categories:

```text
read_only
draft_only
preview_write
confirm_commit
admin_diagnostic
```

Authored prep lifecycle:

```text
draft
planned
placed
played
world_canon
retracted
superseded
```

Durable writes must flow through:

```text
GraphContribution
source artifact revision
identity decision record
Kernel merge / publish
```

## 8. Files likely to update in GitHub for PR005A

After reconciliation, expected GitHub updates for **this** slice are likely:

```text
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Reports/graph-document-audit.md
Docs/Plans/JUMPSTART-docs-relevance-first.md
Docs/Design/dungeonbuddy_spec_architecture_v0_2.md
Docs/Design/ARCHITECTURE-plan-surface-toolbox.md   # optional clarifying patch only
```

PR005B (later) may additionally update architecture / Agent Interaction UX / anchors. Do not update all of these blindly. Update only after local-vs-GitHub reconciliation.

## 9. Required output of this jumpstart

The agent should produce:

1. A doc relevance report.
2. A local-vs-GitHub sync matrix.
3. A proposed set of doc edits.
4. A PR005A handoff or branch plan (Context Audit + Source Reanchor).
5. A GitHub sync preview.
6. Only after approval, GitHub updates.
7. A post-sync verification report proving GitHub matches intended local content.
8. A follow-up pointer to PR005B (Agent Tool Contract).

## 10. Non-goals

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

## 11. Exit criteria

The jumpstart succeeds when:

```text
The agent can say which docs are current, stale, superseded, research-only, or proposal-only.
The roadmap/tracker points clearly to PR005A then PR005B before PR006.
Stale local/project docs no longer look like active authority.
Project Sources are treated as context inputs, not repo authority.
GitHub is synced and verified after explicit approval.
PR006 remains Initial World Supergraph Materialization and is not renumbered.
```
