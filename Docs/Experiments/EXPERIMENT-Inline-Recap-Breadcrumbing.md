# EXPERIMENT — Inline Recap Breadcrumbing

**Date:** 2026-05-02
**Status:** Prototype active; routing-only cross-session baseline recorded 2026-05-08
**Purpose:** Test whether a recap-derived, machine-facing session memory index can make agentic planning and live-game retrieval more reliable without weakening the existing SourceAnchor direction.

---

## 1. Hypothesis

Inline recap breadcrumbs can make recap-derived memory easier for agents to query, route, and later ingest if:

1. the frontmatter is the machine-readable contract,
2. inline tags mark durable retrieval ownership over source-aligned recap spans rather than every mention,
3. party-level references use a collective party route instead of expanding to every PC,
4. unresolved durable entities become explicit new-hub candidates,
5. the artifact remains separable from the canonical source recap because the original recap is the prose artifact.

If the tags become noisy named-entity markup, the experiment fails even if routing coverage is high.

The artifact is not trying to be a prettier recap. It is a session memory index over
the recap: a parseable, routable surface that lets future agents find the right
session evidence and hub context for pre-session planning, live-play lookups, NPC/PC
continuity checks, unresolved-thread review, and corpus update proposals.

### Current direction (2026-05-03)

Use the benchmark harness as the primary proving surface. The lexical/event-keyword
retrieval path is working well enough for the current Session 20 natural-query slice
to justify expanding it; the planner-discovery path remains relevant, but it is now a
diagnostic comparator rather than the main route for this use case.

The next decision is not "can the planner discover the same files by itself?" It is:
"when a new recap lands, can the same breadcrumb/index machinery parse it, emit new
records, and retrieve newly introduced facts without scenario-specific hardcoding?"
The answer must be measured against a holdout recap, not inferred from Session 20.

### Current baseline (2026-05-08)

The routing-only generator is now good enough to treat as the active baseline, not
just a speculative path. The best current measurement is the four-lane refresh over
Campaign 1 Sessions 1, 2, 3, and 13:

| Lane | Source mode | Report | Result |
| --- | --- | --- | --- |
| C1S1 | original recap + frontmatter seed | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s1_routing_refresh_retrieval_only.json` | 14/16 |
| C1S2 | original recap + frontmatter seed | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s2_routing_refresh_retrieval_only.json` | 15/15 |
| C1S3 | original recap + frontmatter seed | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s3_routing_refresh_retrieval_only.json` | 12/13 |
| C1S13 | normalized recap + normalized frontmatter seed | `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s13_routing_refresh_retrieval_only.json` | failing holdout, but diagnostically useful |

**Cost:** four-run routing-refresh sum was about `$0.136347`:
C1S1 `$0.021429`, C1S2 `$0.012705`, C1S3 `$0.046594`, C1S13
`$0.055619`. C1S13 was about +6.8% vs its prior routing-only sidecar
(`$0.052079`), below the project cost-regression threshold.

The important result is not the headline pass count. The failure shape is now sharp:

- **Roster / identity bundle under-tagging:** C1S1 fails two questions because the
  generated unit carries the collective party route but omits individual PC routes on
  the same roster sentence. The source text is retrieved and answer evidence is
  present; route coverage is the gap.
- **Location hierarchy vs same-unit co-tags:** C1S3 finds Grishna records, but they are
  tied to `rivers_edge_pub`, not co-tagged with parent `stonebridge`. Do not paper this
  over with broad parent-location tagging until the design decides whether hierarchy
  belongs in routing, record expansion, or the location-entity query path.
- **Alias / identity bridge loss:** C1S13 regressed `necromancer_question_identity_trap`
  because the refreshed routing-only artifact omitted the `draven` route on the
  necromancer kill unit. This is a true generator regression relative to the prior
  routing-only artifact, not a gold drift.

This is a strong baseline because the remaining failures are local and falsifiable.
The next fix should be targeted by failure family, with sentinel coverage before any
prompt/default change is promoted.

---

## 1.1 Canonical Objective

Given a raw session recap, generate a parseable, routable, source-grounded retrieval
surface that tells future agents:

- which source spans carry durable memory value,
- which existing hub or proposed hub owns that memory,
- which party-level spans should route to the collective party rather than to six PCs,
- which unresolved subjects should become explicit review or hub-creation candidates,
- and which routes can be used directly by downstream tools for querying, retrieval,
  and dry-run corpus updates.

The success question is not "is the artifact pleasant to read?" The canonical recap
already carries prose readability. The success question is "does this artifact improve
agentic querying and retrieval for planning and live-game interaction enrichment?"

---

## 2. Prototype Artifact

Current prototype:

`evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md`

Source recap:

`corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`

The prototype is a derivative markdown copy for convenience while the format is tested.
It should be judged on parseability, routability, and downstream retrieval usefulness,
not on whether it replaces or improves the readable recap.

Current framing correction: the prototype should not replace the canonical recap at all.
If this format graduates, it should become a sibling retrieval/index artifact or a
rendered view over source anchors. The canonical recap remains the prose source of truth.

---

## 3. Breadcrumb Contract

### 3.1 Inline Tags

Allowed inline tags:

- `[PC][corpus-relative hub route]`
- `[NPC][corpus-relative hub route]`
- `[Location][corpus-relative hub route]`
- `[Party][corpus-relative or proposed party hub route]`
- `[NewHubCandidate][proposed corpus-relative route]`

Placement rule: append tags immediately after the smallest source-aligned span that should be retrievable from that hub.

Selectivity rule: do not tag every mere mention. Tag table-significant actions, discoveries, relationship beats, location-state changes, reputation beats, collective decisions, and unresolved durable entities.

Agentic retrieval rule: a tag is justified when it would help a future planning or
live-play agent answer a real continuity question, choose the right hub/context to
load, or propose a downstream corpus update. Background presence alone is not enough.

### 3.2 Functional Frontmatter

The frontmatter is the durable schema surface. It should include:

- schema id,
- source recap path,
- campaign/session metadata,
- breadcrumb semantics,
- inline tag grammar,
- entity index grouped by subject type,
- party/group routing policy,
- unresolved/open questions,
- subject-type counts.

The inline tags are anchors for downstream tools. The frontmatter defines what the tags
mean, which routes are canonical or proposed, and how party/new-hub candidates should
be interpreted.

### 3.3 Party Routing

`Questionable Company` is the canonical collective party entity for Campaign 2.

Proposed route:

`Longmont Campaign/Campaign 2/Parties/questionable_company/`

Current hub status: proposed; do not create the hub as part of this experiment.

Routing policy:

Use the `Party` breadcrumb only when the span has durable retrieval value for the party as a collective actor, witness, decision-maker, reputation target, or affected group. Do not tag every generic `group` / `heroes` / `team` sentence merely because the party is probably present. If specific PCs are acting separately, tag those PCs instead. If any PC is explicitly elsewhere, do not infer all-six participation from group language unless the sentence clearly says so.

Aliases to recognize:

- `Questionable Company`
- `the heroes`
- `the group`
- `the team`
- `the rest of the team`
- `the rest of the group`
- `the others`

Default members for Session 20:

- `baergrom`
- `bonogo`
- `caelynn`
- `ephanna`
- `karsemine`
- `stafl`

---

## 4. Evaluation Rubric

Evaluate the artifact as a machine-facing session memory index:

### 4.1 Hard Gates

1. **Parseability:** frontmatter boundaries, schema marker, body, and inline tags parse deterministically.
2. **Tag vocabulary:** every inline tag type is one of `PC`, `NPC`, `Location`, `Party`, or `NewHubCandidate`.
3. **Route validity:** existing-hub tags resolve to real corpus routes; proposed routes are explicitly marked as proposed or `NewHubCandidate`.
4. **Index consistency:** every route used in body tags appears in the frontmatter entity index or unresolved/open questions.
5. **Source alignment:** every body tag attaches to a source-derived recap span. The tag should not summarize or invent facts absent from the recap.
6. **Writer/routing safety:** PC/NPC tags that claim existing hubs can be dry-run routed to timeline append previews when the hub exposes `timeline.md`; skipped timelines are surfaced explicitly.

### 4.2 Diagnostic Metrics

1. **Baseline overlap:** exact-route precision/recall against the manual baseline artifact.
2. **Tag density:** counts by subject type and per source line; flag mechanical NER density.
3. **Party discipline:** `[Party]` count and exact spans; flag generic group over-routing.
4. **Open-loop capture:** count and inspect `NewHubCandidate` / unresolved questions for durable prep hooks and live-play enrichers.
5. **Routability:** missing existing routes, invented route families, append dry-run success/skips/failures.
6. **Agent-query utility:** sampled planning/live-play questions should retrieve the expected source spans and hub routes without rereading the whole recap.
7. **Cross-session generalization:** a fresh recap can be converted into the same
   machine-facing index shape, queried with newly written gold questions, and retrieve
   new facts by lexical/event-keyword evidence rather than Session 20-specific aliases
   or hand-seeded paths.

### 4.3 Promotion Shape

The manual prototype is the current gold retrieval index, not a prose-quality baseline.
Model outputs should be compared to it for route correctness and selectivity, but
differences are adjudicated by retrieval usefulness: did the model capture or omit a
span that would matter to future planning/live-play agents?

---

## 5. Risks

1. **Tag noise.** The model may drift into named-entity recognition and make retrieval noisy even when coverage looks high.
2. **False precision.** A hand-authored breadcrumb can look machine-verifiable even when no source anchor/hash proves it.
3. **Parallel citation system.** Breadcrumbs must eventually converge with `SourceAnchor`, not replace it.
4. **Over-routing.** Party aliases like `the group` can cause every sentence to look party-owned unless the routing policy is strict.
5. **Hub path drift.** Proposed routes, especially `Parties/questionable_company/`, need lint or registry support before becoming canonical.
6. **Query illusion.** High baseline overlap does not prove downstream usefulness unless sampled planning/live-play queries retrieve the right source spans.
7. **Session-specific hardcoding.** Session 20 can pass while the system has quietly
   baked in known filenames, expected routes, or query-specific keyword aliases. The
   holdout test must fail if the next recap's facts are not discoverable from the
   generated index itself.

---

## 6. Subagent Instructions

Use this prompt for a worker that labels or revises the prototype.

```text
Mission:
Revise the Campaign 2 Session 20 breadcrumb artifact as a machine-facing session memory index with robust functional frontmatter and selective inline hub-route breadcrumbs for PC, NPC, Location, Party, and NewHubCandidate subjects.

Files in scope:
- Read:
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`
  - `evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md`
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_party_registry.json`
  - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json`
  - C2 PC/NPC README files and relevant location README/dossier files needed to resolve hub routes.
- Write:
  - `evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md`

Files explicitly out of scope:
- Do not edit the canonical source recap.
- Do not edit corpus hubs, timelines, dossiers, seeds, statblocks, registries, prompt files, or gold JSON.
- Do not create the proposed `Parties/questionable_company/` hub.

Output contract:
1. Treat the output as a machine-facing session memory index over the recap. The canonical source recap remains the prose artifact.
2. When source prose is rendered in the artifact body, keep the source wording for those spans; do not optimize for readability or rewrite the recap as a new prose artifact.
3. Use frontmatter schema `dmb_recap_breadcrumbs_v1`.
4. Ensure frontmatter includes:
   - source recap path,
   - campaign/session metadata,
   - breadcrumb semantics,
   - inline tag grammar,
   - `entity_index.parties.questionable_company`,
   - entity index grouped by `pcs`, `npcs`, `locations`, and `new_hub_candidates`,
   - unresolved/open questions,
   - counts by subject type.
5. Use inline tags:
   - `[PC][corpus-relative hub route]`
   - `[NPC][corpus-relative hub route]`
   - `[Location][corpus-relative hub route]`
   - `[Party][Longmont Campaign/Campaign 2/Parties/questionable_company/]`
   - `[NewHubCandidate][proposed corpus-relative route]`
6. Party rule:
   - Canonical party display name: `Questionable Company`.
   - Proposed party route: `Longmont Campaign/Campaign 2/Parties/questionable_company/`.
   - Treat `Questionable Company`, `the heroes`, `the group`, `the team`, `the rest of the team`, `the rest of the group`, and `the others` as possible party aliases.
   - Use the Party tag only when the span has durable retrieval value for the party as a collective actor, witness, decision-maker, reputation target, or affected group.
   - Do not tag every generic group/heroes/team sentence merely because the party is probably present.
   - If specific PCs are acting separately, tag those PCs instead.
   - If any PC is explicitly elsewhere, do not infer all-six participation from group language unless the sentence clearly says so.
7. Do not tag every mere mention. Tag only spans with durable retrieval value for future planning/live-play querying, hub context retrieval, or downstream corpus-update proposal.
8. If a span belongs to multiple hubs, include multiple tags.
9. If no hub exists but the entity/place seems durable, use `NewHubCandidate` and add it to frontmatter open questions.
10. Add no explanatory prose outside the indexed artifact except frontmatter.

Verification:
- Confirm only `evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md` changed.
- Run `git diff --stat -- evals/sentence_routing_retrieval_falsification/manual_labels/Session\ 20\ -\ Recap.breadcrumbed.md`.
- Report:
  - output path,
  - counts by subject type,
  - unresolved/open question count,
  - filtered diff stat,
  - any places where the Party policy was hard to apply.
```

---

## 7. Measurement Slices

Before promoting inline breadcrumbs as a Step 1 ingestion output:

1. Write a parser/lint smoke that reads the frontmatter and all inline tags.
2. Verify every inline route appears in the frontmatter entity index or open questions.
3. Verify every tag type is one of the allowed values.
4. Count tags by type and flag obvious over-routing, especially `[Party]`.
5. Compare generated artifacts against the manual baseline retrieval index for exact-route precision/recall.
6. Dry-run route/appends for PC/NPC tags so missing timelines, bad hub paths, and invented route families are visible before any write.
7. Evaluate sampled planning/live-play retrieval questions against the artifact: can an agent find the right source span and hub route without rereading the whole recap?

The first gate is deterministic parsing/routability. The second gate is retrieval utility:
whether the artifact improves agentic querying and enrichment for future planning or live play.