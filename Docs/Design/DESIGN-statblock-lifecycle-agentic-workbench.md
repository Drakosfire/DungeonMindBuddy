---
document_id: dmb-design-statblock-lifecycle-agentic-workbench
title: Statblock Lifecycle + Agentic Workbench Design
document_class: design
status: active
version: 1.0
created_at: "2026-06-09T00:00:00Z"
related:
  - Docs/Plans/REPORT-to-design-agent-statblock-v2-production-deploy-2026-06-09.md
  - Docs/Plans/HANDOFF-dungeonbuddy-statblockgenerator-proxy-client.md
  - Docs/Plans/PLAN-command-board-combat-statblock-generator-roadmap.md
  - Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md
---

# Statblock Lifecycle + Agentic Workbench Design

## 0. Thesis

The product is not only that DungeonBuddy can call StatBlockGenerator.

The product is that the existing full-page StatBlockGenerator workflow becomes an **API-driven, agent-operable statblock lifecycle** that can be projected into multiple dedicated interfaces:

```text
Planning Mode
Statblock Workbench
Statblock View
Combat Pane
Agent tools / scheduled tasks / command-board actions
```

The existing StatBlockGenerator page remains valuable as the rich/manual version of the workflow. DungeonBuddy should expose the same underlying capability through focused surfaces and typed commands.

The core lesson from the combat tracker is that dedicated interfaces matter. A dedicated combat interface was useful because it put the right state and controls on screen. Statblock generation should follow the same principle: build a dedicated lifecycle surface for humans, and expose the same lifecycle as commands for agents.

---

## 1. North-star story

As a GM, I can generate a creature statblock as markdown, review and edit it in a dedicated statblock interface, store it as a draft artifact, promote it into the campaign corpus, retrieve it from the command board, inspect it in Statblock View, and add it to the current combat with AC/HP/actions prefilled from combat defaults.

Expanded lifecycle:

```text
idea / planning need
→ description draft
→ human approval
→ statblock generation job
→ review surface
→ stored draft artifact
→ corpus promotion preview
→ corpus write
→ breadcrumb + semantic ingestion
→ command-board retrieval
→ statblock drilldown
→ add to combat
```

Follow-on stories:

```text
As a GM viewing a statblock, I can generate a variant or revision from that statblock and choose whether to keep it as a draft, promote it to corpus, or add it to combat.

As a GM in planning mode, I can generate a set of statblocks for an encounter or faction, review them as a batch, promote selected ones to corpus, and stage them for future combat.

As a GM running combat, I can generate a quick reinforcement from the current encounter context, review the draft, and add it to the initiative tracker without leaving the Combat Pane.
```

---

## 2. Production producer re-anchor

DungeonMindServer production now exposes the live v2 producer contract at `https://www.dungeonmind.net`:

```text
GET  /api/statblockgenerator/v2/health
POST /api/statblockgenerator/v2/generate-draft
POST /api/statblockgenerator/v2/render-draft
```

These endpoints require `X-DungeonBuddy-Internal-Key`, injected server-side only by Buddy. Browser clients must never receive or send the key.

The v2 producer returns or wraps a draft envelope containing:

- structured statblock;
- rendered markdown;
- deterministic combat defaults;
- warnings;
- provenance;
- lifecycle state;
- review status.

Buddy's existing planner statblock hook predates this contract and should not be treated as the command-board integration boundary.

---

## 3. Core object: StatblockDraftArtifact

The API response is a **draft**. Buddy should wrap that draft in a durable internal artifact object.

The artifact is the bridge between generation, human review, agent tasks, storage, corpus promotion, retrieval, and combat hydration.

Suggested Buddy-side type:

```ts
export interface StatblockDraftArtifact {
  artifact_id: string;
  draft_id: string;
  title: string;

  markdown: string;
  structured_statblock: unknown;
  combat_defaults: CombatDefaults;
  warnings: ReviewWarning[];
  provenance: DraftProvenance;

  review_status: StatblockReviewStatus;
  lifecycle_state: StatblockLifecycleState;
  storage_status: StatblockStorageStatus;
  corpus_status: StatblockCorpusStatus;

  source_refs: SourceRef[];
  breadcrumbs: StatblockBreadcrumb[];

  created_by: "human" | "agent" | "planning_task" | "combat_task";
  created_at: string;
  updated_at: string;
}
```

### 3.1 Lifecycle states

Not all states need implementation immediately. They should exist early so future PRs do not invent incompatible meanings.

```ts
export type StatblockLifecycleState =
  | "description_requested"
  | "description_drafted"
  | "description_approved"
  | "generation_requested"
  | "live_draft"
  | "needs_review"
  | "reviewed"
  | "stored_artifact"
  | "promotion_previewed"
  | "corpus_promoted"
  | "indexed"
  | "combat_ready";
```

### 3.2 Review / storage / corpus status

```ts
export type StatblockReviewStatus =
  | "needs_dm_review"
  | "warnings"
  | "failed"
  | "approved"
  | "rejected";

export type StatblockStorageStatus =
  | "not_stored"
  | "stored_draft"
  | "exported"
  | "archived";

export type StatblockCorpusStatus =
  | "not_promoted"
  | "promotion_previewed"
  | "promotion_confirmed"
  | "write_failed"
  | "indexed"
  | "retrievable";
```

### 3.3 Breadcrumb shape

Breadcrumbs should be attached before corpus ingestion so the Semantic Knowledge Layer can retrieve generated statblocks with context.

```ts
export interface StatblockBreadcrumb {
  id: string;
  kind:
    | "campaign"
    | "session"
    | "encounter"
    | "faction"
    | "location"
    | "npc"
    | "source_statblock"
    | "planning_task"
    | "combat_state";
  label: string;
  route?: string;
  corpus_path?: string;
  reason: string;
}
```

Breadcrumb examples:

```text
campaign:c2
session:23
location:mireward_north_gate
faction:shepherds_flock
encounter:mireward_gate_siege
source_statblock:tripod_null_calf
planning_task:generate_siege_reinforcement
```

---

## 4. Agent-facing command model

Agents and UI should operate the same lifecycle. The agent should not screen-scrape the statblock page or use a parallel hidden flow.

Command names can be defined before all behaviors exist.

```text
statblock.generator.health
statblock.description.request
statblock.description.approve
statblock.draft.generate
statblock.draft.render
statblock.draft.review
statblock.draft.store
statblock.corpus.preview_promote
statblock.corpus.confirm_promote
statblock.corpus.ingest
statblock.combat.add
```

Immediate implementation may only support:

```text
statblock.generator.health
statblock.draft.generate
statblock.draft.render
```

But the command namespace should show the intended lifecycle.

### 4.1 Agent task story

Planning Mode should eventually support a flow like:

```text
GM: I need a fungal siege scout for Session 24.
Agent creates a description draft.
GM approves / edits description.
Agent calls generate-draft.
Buddy creates a StatblockDraftArtifact.
Workbench shows markdown + warnings + combat defaults.
GM reviews.
Buddy stores draft artifact.
GM previews corpus promotion.
Corpus writer previews path + frontmatter + breadcrumbs.
GM confirms.
Ingestion adds it to the Semantic Knowledge Layer.
Command board can retrieve it later.
```

---

## 5. Dedicated surfaces

### 5.1 Statblock Workbench

The Workbench is the dedicated lifecycle interface. It should manage:

- prompt / intent;
- description draft;
- generated markdown;
- structured statblock summary;
- combat defaults;
- warnings;
- provenance;
- breadcrumbs;
- review state;
- storage state;
- corpus state;
- available actions.

Possible Workbench actions:

```text
Approve description
Generate statblock
Regenerate
Render existing statblock
Edit markdown
Store draft
Preview corpus promotion
Promote to corpus
Ingest / reindex
Open in Statblock View
Add to combat
```

This surface should exist before inline combat generation becomes the main UX. It teaches the lifecycle and prevents the Combat Pane from becoming the home for unfinished workflows.

### 5.2 Statblock View

Statblock View is the read/drilldown surface for corpus-backed statblocks and pending drafts.

Long-term actions:

```text
Generate variant
Revise existing
Render as draft artifact
Add to combat
Open Workbench
Preview corpus status
```

Current server limitation: `generate_from_source_statblock` and `revise_existing` return 501. UI should not present those as production-ready actions until the producer implements them.

### 5.3 Combat Pane

Combat Pane should be a constrained consumer of the lifecycle, not the full lifecycle manager.

Combat flow:

```text
Generate reinforcement
→ compact draft review
→ add to initiative
→ optionally store/promote later
```

Combat should hydrate from `combat_defaults` first:

```text
name
armor_class
hit_points
initiative_bonus
passive_perception
speed_summary
primary_actions
suggested_tactics
```

Markdown remains the drilldown display. Structured statblock remains the full source object.

### 5.4 Planning Mode

Planning Mode should support more expansive generation:

- encounter packet statblocks;
- faction variants;
- terrain-linked monster sets;
- session threat rosters;
- queued generation tasks;
- batch review and promotion.

Planning Mode should create draft artifacts, not anonymous text blobs.

---

## 6. Storage and corpus promotion

There are two storage levels:

```text
Draft storage
Corpus storage
```

### 6.1 Draft storage

Draft storage is for generated or rendered work that is not yet corpus canon.

It preserves:

- markdown;
- structured statblock;
- combat defaults;
- warnings;
- provenance;
- breadcrumbs;
- review status.

Draft storage may begin as local/test artifacts or live/prep artifacts. It should be typed as if it will later become durable storage.

### 6.2 Corpus storage

Corpus storage is durable markdown in the corpus tree, with frontmatter and indexing.

Promotion path:

```text
generate-draft / render-draft
→ StatblockDraftArtifact
→ review/edit
→ store draft artifact
→ preview corpus write
→ confirm corpus write
→ markdown file with frontmatter
→ README/index update if needed
→ ingestion / reindex
→ retrieval smoke
```

Corpus promotion must use Buddy's safe write pattern: preview, confirm token, allowlisted path, and no silent hub mutation.

### 6.3 Semantic Knowledge Layer ingestion

Corpus promotion is not complete until retrieval works.

Minimum ingestion obligations:

- write markdown file;
- add required frontmatter;
- attach breadcrumbs;
- run or trigger ingestion;
- verify retrieval by title and breadcrumb route;
- make available to Statblock View and command-board search.

---

## 7. Request mapping

Buddy should map product intents to v2 producer requests.

### 7.1 Supported now

| Product intent | v2 mode / route | Status |
|---|---|---|
| New creature from prompt | `generate_from_prompt` → `generate-draft` | live |
| Quick combat reinforcement | `quick_reinforcement` → `generate-draft` | live |
| Terrain-aware creature | `terrain_pressure` → `generate-draft` | live |
| Wrap existing structured statblock | `render-draft` route | live |

### 7.2 Deferred until server support

| Product intent | v2 mode / route | Status |
|---|---|---|
| Generate variant from source statblock | `generate_from_source_statblock` → `generate-draft` | 501 |
| Revise existing statblock | `revise_existing` → `generate-draft` | 501 |

Do not design production UI that depends on the 501 modes until DungeonMindServer implements them.

### 7.3 Request mapping inputs

A generator request should be assembled from structured context, not only a prompt string:

```text
intent summary
target CR / challenge band
role
complexity
tone
encounter context
terrain context
source refs
breadcrumbs
output options
```

---

## 8. Response mapping

`StatBlockDraftResponse` should map into three layers:

### 8.1 Draft artifact

```text
response.draft → StatblockDraftArtifact
```

Preserve markdown, structured statblock, combat defaults, warnings, provenance, and source refs.

### 8.2 Review surface

```text
markdown + warnings + provenance + combat_defaults → Workbench / review UI
```

Review is first-class. Do not silently auto-promote or auto-insert as the default behavior.

### 8.3 Combat entity

```text
combat_defaults → CombatEntity defaults
markdown / artifact id → statblock drilldown source
```

Suggested hydration:

```text
entity.name = combat_defaults.name
entity.ac = combat_defaults.armor_class
entity.hp = combat_defaults.hit_points
entity.maxHp = combat_defaults.hit_points
entity.notes includes speed_summary / primary_actions / warnings summary
entity.pendingStatblockMarkdown = artifact.markdown until corpus-backed
entity.source = generated_pending | corpus
```

---

## 9. Next implementation slice

Rename the next Buddy slice from a narrow proxy/client to a lifecycle seam:

```text
Buddy statblock lifecycle seam: v2 producer client + draft artifact bones
```

The PR should still be small. It should include:

- typed v2 producer client/provider for health/generate/render;
- mock provider;
- server-side HTTP provider or proxy that injects internal key;
- `StatblockDraftArtifact` type;
- lifecycle/status enums;
- command-name constants for future agent operations;
- fixtures for generated and rendered draft responses;
- tests for provider behavior, error envelopes, key handling, and artifact mapping.

The PR should not include:

- full Workbench UI;
- Combat Pane generation UI;
- corpus writes;
- ingestion jobs;
- combat mutation;
- browser-side internal key exposure.

### 9.1 Acceptance criteria for next PR

- Buddy can call or mock v2 health/generate/render.
- Internal key is injected server-side only.
- V2 response maps to `StatblockDraftArtifact`.
- Draft artifact preserves markdown, structured statblock, combat defaults, warnings, provenance, source refs, and initial lifecycle/status fields.
- Agent command names/constants exist for the lifecycle.
- No UI depends on the seam yet.
- No corpus or combat mutation occurs.

---

## 10. Design distinction

The API call produces a **draft**.

Buddy turns the draft into an **artifact**.

Corpus promotion turns the artifact into **campaign knowledge**.

The Semantic Knowledge Layer makes that knowledge **retrievable**.

The command board makes it **usable at the table**.

That is the spine of the system.
