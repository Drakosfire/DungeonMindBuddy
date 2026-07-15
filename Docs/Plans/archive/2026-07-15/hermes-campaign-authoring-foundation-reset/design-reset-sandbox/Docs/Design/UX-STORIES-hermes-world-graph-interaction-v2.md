# UX stories — Hermes × World Graph interaction v2

**Status:** PROPOSED  
**Primary promise:**

> As a GM, I can talk to DungeonBuddy about my campaign as though I have a knowledgeable prep partner that explores the current graph with me, shows what it relied on, distinguishes graph fact from source detail and inference, and exposes gaps without becoming rigid or unhelpful.

## Product-wide interaction rules

1. A selected graph object is the strongest conversational referent.
2. A previously resolved thread referent is stronger than prose reconstruction.
3. Prior prose may resolve intent but never supplies current campaign facts.
4. Candidate matches, answer-used claims, opened sources, and available connections are visibly distinct.
5. Partial graph knowledge produces a useful partial answer, not a generic refusal.
6. Graph facts, source-verified details, Hermes inferences, and creative suggestions use distinct visual treatments.
7. Every factual turn uses one revision and one admissibility scope.

## Story A1 — orient me to an object

**User intent:** “What do we know about Tripod Null-Calf at the North Gate?”

**Visible behavior:** Hermes identifies Tripod, gives its battlefield role and relevant North Gate relationship, then highlights prep-relevant facts. The panel opens on Tripod and marks the claims used in the answer.

**Graph operations:** deterministic identity resolution → exact claim packet → bounded neighborhood expansion.

**Authority:** accepted node/attribute/relationship claims.

**Evidence behavior:** graph references always; source citations only for opened anchors. Unreadable source is disclosed without suppressing graph facts.

**Ambiguity:** if several Tripods match, show candidates and ask a focused clarification before stating object-specific facts.

**Failure:** graph miss becomes “not modeled,” not “source says nothing.” Execution failure is separate.

**Trace:** candidate IDs, selected identity, claims used, source availability, source read state.

**Revision:** current pinned head unless user explicitly asks historical.

**Future write implication:** missing role/statblock fields can become a typed proposal later.

## Story A2 — remember what matters for this session

**User intent:** “What should I remember about Tripod for tonight?”

**Visible behavior:** concise game-facing summary: encounter role, dependencies, relationships, open consequences, and mechanics links when present.

**Graph operations:** exact object → session-focused claims → related encounter/statblock/resource objects.

**Authority:** accepted current claims; prep implications are labeled inference.

**Evidence behavior:** no mandatory source read unless exact wording/mechanics are requested or claim policy requires it.

**Ambiguity:** current selected session and node resolve scope.

**Failure:** show known facts and name missing game-information classes such as “no statblock linked.”

**Trace:** claims used and why each was selected as session-relevant.

**Revision:** selected planning revision.

**Future write implication:** “link statblock” can become a proposed relationship.

## Story B1 — explore connections

**User intent:** “What is it connected to?”

**Visible behavior:** the answer groups meaningful game concepts—encounters, places, NPCs, resources, consequences—not raw edge counts. The panel highlights direct connections and permits expansion.

**Graph operations:** selected/resolved node → bounded neighborhood grouped by relation family and salience.

**Authority:** explicit accepted edges are graph facts; cross-edge interpretation is inference.

**Evidence behavior:** each direct connection has a graph reference; support/source available on demand.

**Ambiguity:** selected object wins; otherwise prior resolved referent; otherwise clarify.

**Failure:** distinguish “no modeled edges” from retrieval error.

**Trace:** traversal bounds, included/excluded relation groups, truncation.

**Revision:** same turn revision across all edges.

**Future write implication:** missing expected edge may become a proposed correction.

## Story B2 — compare two objects

**User intent:** “Compare Tripod Null-Calf and the Under-Hymn Brood as siege threats.”

**Visible behavior:** aligned comparison by role, pressure, mobility, target structures, chronology, and known mechanics; missing fields remain visibly blank.

**Graph operations:** resolve both identities → retrieve comparable claim classes → optional neighborhoods.

**Authority:** accepted claims per object; comparison synthesis is not a new canon claim.

**Evidence behavior:** references attached per comparison row, not dumped at answer end.

**Ambiguity:** candidate selection is independent for each object.

**Failure:** partial comparison proceeds with explicit asymmetric coverage.

**Trace:** claim-class alignment and gaps.

**Revision:** one shared revision.

**Future write implication:** uncovered structured fields suggest schema/graph enrichment proposals.

## Story B3 — trace a path

**User intent:** “How is Tripod connected to the cure line?”

**Visible behavior:** show the shortest meaningful accepted path and then explain the game implication separately.

**Graph operations:** typed path search with allowed predicates/depth → claim packet for path edges.

**Authority:** path edges are graph facts; “therefore alternate access matters” is inference.

**Evidence behavior:** graph references for every path edge; optional source reads.

**Ambiguity:** several paths are ranked and labeled, not merged silently.

**Failure:** known endpoints plus missing relationship produces a precise graph-gap report.

**Trace:** candidate paths, selected path, depth/predicate constraints.

**Revision:** one revision.

**Future write implication:** operator may propose the missing edge.

## Story C1 — prepare an encounter

**User intent:** “What should affect encounter design here?”

**Visible behavior:** Hermes translates graph facts into actionable prep: positional pressures, dependencies, likely consequences, linked statblocks, relevant NPCs/resources, and unresolved threads.

**Graph operations:** focus object/location/scene → neighborhood + claim families + linked mechanics artifacts.

**Authority:** facts labeled graph-grounded; prep implications labeled inference; new ideas labeled suggestion.

**Evidence behavior:** source read only when exact mechanics/detail is needed.

**Ambiguity:** uses selected scene/location and asks only if the focus cannot be resolved.

**Failure:** missing mechanics do not prevent lore/relationship prep advice.

**Trace:** fact → implication mapping.

**Revision:** current prep revision.

**Future write implication:** save an implication as draft only, never canon automatically.

## Story C2 — find unresolved threads

**User intent:** “What unresolved threads around Mireward could I use?”

**Visible behavior:** grouped thread candidates with direct graph support, status, connected actors/places, and why each is usable.

**Graph operations:** location/focus neighborhood → open-thread claim class → chronology/status filtering.

**Authority:** explicit open/resolved state is graph fact; narrative opportunity is inference.

**Evidence behavior:** graph references; optional source detail.

**Ambiguity:** “Mireward” candidate selection shown if multiple scopes exist.

**Failure:** distinguishes no modeled threads from incomplete extraction.

**Trace:** filters and excluded resolved/stale threads.

**Revision:** current revision with optional historical comparison.

**Future write implication:** new prep thread stays draft until confirmed.

## Story D1 — inspect what the answer used

**User intent:** “Why are you saying that?” or click support.

**Visible behavior:** an answer-support drawer lists claim-by-claim graph references, opened source citations, inferences, gaps, and conflicts.

**Graph operations:** none required unless user expands provenance/source.

**Authority:** support state is deterministic from the retrieval ledger.

**Evidence behavior:** clearly marks `available`, `unreadable`, `opened`, `integrity failed`.

**Ambiguity:** each answer sentence/section maps to support IDs.

**Failure:** missing support is a product defect surfaced as unsupported, not hidden.

**Trace:** user-friendly ledger; raw developer details remain secondary.

**Revision:** displayed for every support item.

**Future write implication:** unsupported claim cannot be proposed as correction without explicit evidence/reason.

## Story D2 — request a source quotation

**User intent:** “Show me the exact source text.”

**Visible behavior:** open a bounded admitted source anchor and show the excerpt with artifact/locator/digest metadata.

**Graph operations:** resolve supporting anchors → read selected anchor.

**Authority:** opened source content.

**Evidence behavior:** source citation created only after successful read.

**Ambiguity:** if several sources support the claim, show choices/summaries.

**Failure:** unreadable, unavailable, and integrity failure have distinct messages; graph fact remains visible where safe.

**Trace:** anchor selected, read result, digest/truncation.

**Revision:** source anchor bound to current revision.

**Future write implication:** disagreement may start a correction proposal.

## Story E1 — click a node and continue talking

**User intent:** click Tripod, then ask “Why does this matter?”

**Visible behavior:** selected node becomes an explicit thread referent chip. Hermes receives the durable ID, label, revision, and selection origin—not just prose.

**Graph operations:** exact object claim packet; model may expand.

**Authority:** selected identity is navigation context; fresh current claims remain factual authority.

**Evidence behavior:** normal claim/source rules.

**Ambiguity:** selected object outranks lexical pronoun resolution.

**Failure:** stale/deleted selection is shown as stale and re-resolved or cleared; never silently rebound.

**Trace:** referent source `ui_selection`.

**Revision:** selection pointer is revalidated against turn revision.

**Future write implication:** selected object anchors future correction proposals.

## Story F1 — handle incomplete graph coverage

**User intent:** asks for role, mechanics, and history where only role/history exist.

**Visible behavior:** answer known role/history, list missing mechanics, and offer reasoning only within supported bounds.

**Graph operations:** object claims + coverage diagnostic by claim family.

**Authority:** known claims remain usable.

**Evidence behavior:** source gaps and graph gaps are separate.

**Ambiguity:** none if identity resolved.

**Failure:** no generic abstention unless nothing useful remains.

**Trace:** requested dimensions versus covered/missing dimensions.

**Revision:** current.

**Future write implication:** missing mechanics becomes an enrichment target, not invented content.

## Story F2 — handle graph/source disagreement

**User intent:** “The source says X, but the graph says Y. Which is current?”

**Visible behavior:** state current graph canon, show contradictory source content, explain revision/timestamps, and mark conflict for review.

**Graph operations:** claim + support anchors + source reads + revision history.

**Authority:** accepted current graph governs current canon; source remains authoritative evidence of its own content.

**Evidence behavior:** both graph reference and source citation.

**Ambiguity:** no silent reconciliation.

**Failure:** source integrity failure prevents comparison.

**Trace:** conflict record and precedence rule.

**Revision:** current and source-associated revision shown.

**Future write implication:** launch a typed correction proposal preview.

## Story G1 — propose a correction later

**User intent:** “That relationship is wrong.”

**Visible behavior:** no immediate write. Show current claim, support, requested correction, affected objects, and proposed new revision preview.

**Graph operations:** exact claim read + impact analysis.

**Authority:** user statement is a proposed change, not current fact until confirmed/published.

**Evidence behavior:** existing support plus optional new evidence/reason.

**Ambiguity:** correction target must be exact.

**Failure:** conflicting/foreign revision blocks proposal.

**Trace:** proposal lifecycle.

**Revision:** based on exact head; stale head requires rebase/review.

**Future write implication:** explicit GM confirmation publishes through PR011 successor.

## Story H1 — maintain conversation safely

**User intent:** pronouns, shorthand, parallel threads, reload.

**Visible behavior:** referent priority:

```text
current explicit IDs > current UI selection > thread pinned referents > prior resolved turn referents > bounded visible prose > clarification
```

**Graph operations:** current claims always retrieved at current revision.

**Authority:** no continuity state is factual authority.

**Evidence behavior:** current-turn only.

**Ambiguity:** never leak referents across threads/campaigns/focus/admissibility.

**Failure:** stale referent becomes explicit stale-selection state.

**Trace:** referent resolution source.

**Revision:** continuity pointers revalidated each turn.

**Future write implication:** none directly.
