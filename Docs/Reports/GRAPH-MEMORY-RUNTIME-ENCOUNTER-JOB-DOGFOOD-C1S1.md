# Runtime Encounter/Job Dogfood Report — Longmont C1S1

**Status:** Dogfood complete
**Mode:** Manual dogfood / evaluation / decision support
**Preview-only:** yes. This run performed no corpus mutation, no canon promotion, no approved
graph-memory write, and no production retrieval. It is not a memory approval, a UI ship, or a
default-behavior change.

## 1. Source recap selected

`corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md`

Chosen per the handoff's "Dogfood A" recommendation: the simplest real recap with an NPC-given
job, a location, a combat, and a partial result. C1S1 has all four: Glowkindle posts a rat-cleanup
job → party travels to the Wizard's Tower Brewing Company → fights giant rats → job outcome is
left open (deferred, not stated as resolved in-session).

## 2. Command/path/config used

Runtime entry point used (matches the handoff's recommended manual gate, `apps/live_control_server/services/recap_graph_preview_ingest.py::build_recap_graph_preview_bundle`):

```bash
python3 -m evals.graph_memory_layer.run_encounter_job_dogfood \
  --campaign-id longmont-c1 --session 1 \
  --recap-path "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md"
```

which calls `build_recap_graph_preview_bundle(extract_graph=True, force_graph_run=True, graph_extraction_profile="category_encounter_job_preview")`.
A small CLI wrapper (`evals/graph_memory_layer/run_encounter_job_dogfood.py`) was added since no
existing script exercised this runtime path with live model extraction; the wrapper does not
change extraction behavior — it only calls the existing service function.

Run directory: `out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/` (git-ignored,
preview-only).

No `candidate_graph_path` was supplied (real model extraction, not a fixture bypass). No dynamic
vocabulary context was enabled or invented.

## 3. Manifest/profile verification

From `graph_ingest_run_manifest.json`:

```text
diagnostics.graph_extraction_profile = "category_encounter_job_preview"                    ✓
diagnostics.graph_extraction_profile_options.enable_encounter_job_pass = true               ✓
diagnostics.graph_extraction_profile_options.enable_party_participation_attachment = true   ✓
diagnostics.graph_extraction_profile_options.enable_encounter_job_edge_guidance = true       ✓
diagnostics.graph_extraction_profile_options.enable_dynamic_node_vocabulary_packet = false   ✓
diagnostics.candidate_extraction = true                                                      ✓
diagnostics.extraction_mode = "category_decomposed"                                          ✓
diagnostics.canon_promotion = false                                                          ✓
diagnostics.approved_memory_write = false                                                    ✓
diagnostics.corpus_mutation = false                                                          ✓
diagnostics.production_retrieval = false                                                     ✓
status = "candidate_validation_ready"
```

Health block:

```text
node_count = 49          edge_count = 34         beat_count = 8
evidence_ref_count = 101 resolvable_evidence_ref_count = 101 (100%)
model_id = gpt-5.4-mini   estimated_cost_usd = $0.059385
```

Verdict: runtime invocation is correct. The profile is exactly what was requested, options match
the expected mapping table from PR #244, and none of the forbidden lifecycle flags are set. This
rules out Category A (profile/runtime failure) entirely — everything below is genuine extraction
signal.

## 4. Node summary

| node_type | count |
|---|---:|
| item | 13 |
| character | 11 |
| location | 8 |
| mystery | 6 |
| group | 5 |
| organization | 2 |
| quest | 2 |
| faction | 1 |
| combat_encounter | 1 |
| **total** | **49** (42 from the 8 passes + 7 deterministic party-context anchors) |

`nodes_before_dedup` in `consolidation_diagnostics.json` is 42, and zero nodes were merged
(`merged_nodes: []`, `cross_class_merged_nodes: []`) — every one of the 42 model-produced nodes
survived to the candidate graph untouched. This matters for section 6 below.

## 5. Edge summary

34 edges total: 25 from `edge_pass`, 6 deterministic party-membership anchors (PC → Heroes/party),
and 3 deterministic party-participation edges (Heroes/party → quest/combat, inserted by PR #239's
attachment logic, not the LLM). `dropped_edges_missing_endpoints` is empty — no edge referenced a
node that failed to survive consolidation. `edge_predicate_issues` flagged 4 edges (all
`present_at` under the `visibility` predicate family — a pre-existing predicate-catalog mismatch,
not something the encounter/job profile introduced).

## 6. Quest/encounter findings

Two `quest` nodes and one `combat_encounter` node were produced:

- `quest_glowkindle_rat_cleanup_001` — "Glowkindle's rat cleanup request" (high importance). **Correct.** This is exactly the durable job/task object the spike targeted.
- `combat_rat_fight_brewery_001` — "Fight with giant rats at the brewery" (high importance). **Correct.** This is exactly the durable combat object the spike targeted.
- `quest_follow_brewery_directions_001` — "Reach the brewery using Grishna's directions" (medium importance). **Quest overgeneration.** Following NPC-given directions to a location is travel flavor, not a playable objective with a giver/reward/target. This is precisely the "Quest overgeneration" risk the handoff called out in advance (§10, encounter_job_pass known risks). It also received a deterministic `pursues` edge from the party (since party-attachment fires for every quest node regardless of quality), which compounds the noise rather than containing it.

No `job`, `task`, `mission`, `monster`, or `adversary` node types were emitted — the taxonomy
decision from PR #236 held. `thread_pass` did **not** swallow the rat-cleanup job (the risk
flagged in the handoff §10 for `thread_pass`); it correctly held only true mysteries (unnamed
river, ambiguous statue/boulder, the excavation-wall breach, the giant-rat assault itself as an
open thread, and the cat-owl mystery) plus one `deferred_item` for the unresolved job outcome.
That separation worked exactly as designed.

Encounter/job edges connecting these nodes to the rest of the graph were all present and correctly
typed: `quest → mission_targets → creature`, `quest → mission_focus → location`,
`npc → hires → quest`, `creature → participates_in → combat`, `combat → located_in → location`,
and — a genuinely nice touch the fixture comparison (PR #242) didn't even test — `combat →
results_in → quest`, tying the fight's resolution back to the job that spawned it.

## 7. Party attachment findings

Deterministic party attachment worked as intended and did **not** duplicate anything:

- All 6 named PCs (Baergrom, Bonogo, Caelynn, Ephanna, Karsemine, Stafl) were inserted once each as
  `context_anchor` nodes resolved to their corpus hub paths, with a single `member_of → Heroes /
  party` edge each.
- `thread_pass`'s own `ignored_items` explicitly records that the model saw the party roster in the
  recap text and chose not to re-extract it as session-novel nodes ("Deterministic party anchors
  were provided in the prompt and should not be re-extracted") — the intended, and no fallback re-extraction happened.
- `party_participation_attachment.inserted_edge_count = 3`: one `participates_in` (party →
  combat) and two `pursues` (party → each quest node, including the noisy travel-quest above).
- No duplicate `Heroes / party` node, no duplicate PC nodes.

The one caveat: because attachment is unconditional on "every quest node," it faithfully amplifies
quest overgeneration into an extra deterministic edge rather than filtering it. That's a
consequence of the pass ordering (attachment runs after `encounter_job_pass`, with no salience
gate), not a bug in the attachment logic itself.

## 8. Predicate and dropped-edge findings

- **Dropped edges: zero.** `dropped_edges_missing_endpoints: []`. Every edge endpoint survived to
  the final candidate graph.
- **Predicate issues: 4**, all `relationship_type: present_at` flagged
  `relationship_family_mismatch` against `predicate_family: visibility`. These are pre-existing
  location/presence edges from `edge_pass` (gnomes present at brewery, magical crystals present at
  brewery, cat owl present at combat) — not encounter/job-specific, and not new noise introduced by
  this profile. Worth a follow-up, but out of scope for the encounter/job spike itself.
- **Cross-class collision pressure is the dominant signal**, and it is *visible* rather than
  silent — see next section.

## 9. Evidence/provenance findings

Evidence resolution is strong: 101/101 evidence refs resolve against the source-span index
(100%), all are paragraph-level (`paragraph_evidence_ref_count = 101`), and zero fell back to
full-text (`full_text_fallback_ref_count = 0`). Every node/edge carries `anchor_quotes` a human
reviewer can check against the recap paragraph directly.

One diagnostics inconsistency found: `candidate_validation_report.json` itself reports
`evidence_ref_count: 0` / `resolvable_evidence_ref_count: 0`, because its counting logic only
inspects a top-level `evidence_refs` array on the candidate graph object, which this schema
doesn't populate (evidence lives per-node/per-edge). The manifest's `health` block counts
correctly (it walks nodes/edges/beats), so this is a **reporting bug in one artifact, not an
actual evidence gap** — but it means a reviewer who only opens
`candidate_validation_report.json` would wrongly conclude the run has no evidence at all. Flagging
as a diagnostics fix, not an extraction fix.

### Segmentation bug found during review (new finding, not in the original risk list)

While tracing why a real story beat — the final paragraph of C1S1 ("a beautifully tiled hallway...
another resident of the shatter mages tower... flaming magma infused spider monstrosity") — never
appeared anywhere in any pass, I found the cause is **not** a model or prompt issue. It's a
boundary bug in `evals/graph_memory_layer/graph_preview_runner.py::_split_recap_paragraph_spans`.

The paragraph-splitting regex is:

```python
re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", recap_text, flags=re.DOTALL)
```

This requires each paragraph match to end either at a blank line (`\n\s*\n`) or at the absolute
end of the string (`\Z`) with **no trailing newline**. C1S1's source file — like essentially every
normally-saved Markdown file — ends with exactly one trailing `\n` after the last sentence, not
zero. Because of that single trailing newline, neither alternative in the lookahead is satisfied
at the position right after the last non-whitespace character, so the regex engine never emits a
match for the final paragraph. Verified directly:

```text
recap file: 3130 chars total, ends "...spider monstrosity.\n"
regex matches: 8 paragraphs, last one ends at char 2799 ("A fine first combat...team together!")
chars 2799–3130 (the entire final paragraph) are never split into a span and therefore
never sent to any extraction pass.
```

**Impact:** this silently truncates the *last paragraph of every recap ingested through this
runner*, independent of the encounter/job profile — it would have affected the plain
`current_default` profile identically. It just happened to be invisible before because nobody was
looking at *and* the corpus is full of recaps where the last paragraph is stylistic ("bonding
moment" filler, etc.) — in C1S1 it happens to be the one paragraph that seeds the *next* session's
antagonist and location. This is a correctness bug worth fixing before further dogfooding on any
recap, independent of the encounter/job question.

## 10. Cost/telemetry summary

- Model: `gpt-5.4-mini` (resolved via `MODEL_POLICY.json` → `actions.graph_memory_category_extraction` → `fast_smart_mini`).
- 8 passes (`actor`, `location`, `collective`, `object`, `thread`, `beat`, `encounter_job`, `edge`).
- Estimated cost: **$0.059385** for one ~3.1k-character recap.
- Wall time: ~56s for the full CLI invocation including source-span bundling and validation.
- All diagnostics needed to reconstruct "what happened" were present in the artifact set; the only
  gap was the validation-report evidence-count bug noted above.

## 11. Comparison to PR #242 Glowkindle fixture shape

The synthetic fixture asserted this exact shape and this run matches it almost node-for-node,
despite being independently generated by a live model against real (longer, noisier) prose:

| Fixture check | Fixture (synthetic) | This run (real C1S1) |
|---|---|---|
| `has_quest` | ✓ (1 quest) | ✓ (2 quests — 1 correct + 1 overgenerated) |
| `has_combat_encounter` | ✓ | ✓ |
| `has_party_pursues_quest` | ✓ | ✓ (both quests) |
| `has_party_participates_in_encounter` | ✓ | ✓ |
| `has_encounter_location_edge` | ✓ | ✓ |
| `has_rat_participation_edge` | ✓ | ✓ (as `creature_giant_rats_001 → participates_in → combat`) |
| `has_quest_target_edge` | ✓ | ✓ (`mission_targets → creature_giant_rats_001`) |
| `has_quest_focus_edge` | ✓ | ✓ (`mission_focus → brewery`, fixture used cellar; real recap never names a cellar location node) |
| `has_duplicate_pc_nodes` | false (good) | false (good) |
| `has_invalid_predicate_issues` | false | **true** (4 `present_at` family-mismatch warnings — pre-existing, not encounter/job-specific) |
| `has_dropped_edges` | false | false |

The fixture didn't model cross-class node duplication at all (it was hand-authored, one node per
concept). The real run's dominant gap relative to the fixture is exactly that: **the fixture
proved the encounter/job shape works; the real run additionally proves that shape survives inside
a much noisier candidate graph where the same real-world entity gets independently rediscovered by
3–4 different category passes.**

## 12. Success/failure assessment

**Verdict: Yellow — shape promising, refinement needed.**

What's Green (shape validated):

- Quest and combat-encounter nodes are correctly typed, well-described, and evidence-backed.
- Party attachment is deterministic, non-duplicating, and correctly ignores the PC roster when
  it's already anchored.
- Encounter/job edge guidance produced a rich, source-supported edge set around the new node
  types, including a `results_in` link the fixture didn't even test.
- No dropped edges, no invalid node types, no duplicate PCs, no duplicate party node.
- Diagnostics are largely sufficient for a reviewer to reconstruct what happened — cross-class
  collisions are visible and explained, not silent.

What's not yet Green:

- **Quest overgeneration** (1 of 2 quest nodes is travel flavor, not a real job).
- **Cross-class node duplication is severe and category-decomposed extraction makes it structural,
  not incidental.** 7 of 42 raw model nodes (17%) are exact-label collisions across 2–3 different
  category passes describing the same real-world thing (Stone Bridge the town, The River's Edge
  Pub, Wizard's Tower Brewing Company, giant rats, the cat owl, the troupe of gnomes, the enormous
  boulder). The existing narrow auto-merge policy (place+collective exact match only) essentially
  never fires on real data, because real collisions are usually 3-way (actor+collective+object, or
  object+place, or collective+object+place) rather than the clean 2-way case the policy targets.
  Every single collision in this run landed in `cross_class_blocked_nodes`, not
  `cross_class_merged_nodes`.
- **A real paragraph of source material was silently dropped** before extraction even started, due
  to a boundary bug in paragraph segmentation, unrelated to the encounter/job profile.
- **PC-specific action capture remains thin** — only one PC-attributable action (Bonogo buying a
  firkin of ale) survived into a node/beat, and even that has no edge tying the PC to the item.
  This matches the same gap flagged in the earlier vocabulary-ablation manual review.

This is not a redesign signal. The core taxonomy decision (quest + combat_encounter, no separate
job/monster types) holds up on real data. The refinement need is squarely in (a) the
encounter/job pass's salience rule for what counts as a "quest," and (b) the cross-class
identity/consolidation layer, which is the same gap already flagged for the Prime Design agent in
`Docs/Plans/HANDOFF-prime-design-graph-memory-extraction-taxonomy.md`. This dogfood adds concrete,
measured evidence (7 blocked collision groups on one recap) to that open question rather than
raising a new one.

## 13. Recommended next PR

Ordered by how directly each addresses what this dogfood measured, independent of each other and
each individually small in scope:

1. **Fix the paragraph-segmentation boundary bug** in
   `evals/graph_memory_layer/graph_preview_runner.py::_split_recap_paragraph_spans` (trailing-newline
   lookahead). This silently affects every recap ingested through this runner, not just
   encounter/job profile runs, and should land before any further dogfood on additional sessions.
   Smallest, most urgent, and orthogonal to the taxonomy work.
2. **Refine `encounter_job_pass` salience rules** to exclude "follow directions to a place" /
   generic travel intent from `quest` classification — add a fixture/regression test asserting a
   travel-only sentence does *not* produce a quest node.
3. **Extend the cross-class identity/consolidation policy** beyond the narrow place+collective
   2-way rule, using this run's 7 `cross_class_blocked_nodes` groups as a concrete regression
   fixture. This is the same next step already queued for the Prime Design agent — this report is
   additional real-data evidence for that decision, not a competing plan.
4. **Fix the `candidate_validation_report.json` evidence-count bug** (it should walk per-node/edge
   `evidence_refs`, matching the manifest `health` block's counting logic, not just a nonexistent
   top-level array) so a reviewer who only opens the validation report doesn't get a false "no
   evidence" read.

None of these require UI work, runtime default changes, or touching `/plan`. Per the handoff, this
report does not authorize any of them on its own — it's the evidence a reviewer needs to pick one
and scope a PR.

## 14. Explicit safety statement

This is preview-only dogfood. It does not approve memory, promote canon, mutate corpus, or write
durable graph memory. No files under `corpus/` were modified. No `/plan` behavior changed. No
runtime default changed. All artifacts live under `out/graph_memory/runs/` (git-ignored) plus this
report and the small CLI wrapper script added to run it.

## Appendix — artifact paths

```text
out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/graph_ingest_run_manifest.json
out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/candidate_graph.json
out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/pass_outputs.json
out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/pass_telemetry.json
out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/consolidation_diagnostics.json
out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/candidate_validation_report.json
out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/source_span_index.json
out/graph_memory/runs/longmont-c1/session-1/20260701T185617Z/provenance_index.json
```

Runner script added to reproduce or repeat on another recap:
`evals/graph_memory_layer/run_encounter_job_dogfood.py`

## Addendum — automated gold-graph comparison

The sections above are a manual/qualitative read. To answer "did edge quality actually move the
needle" with a number instead of an eyeball, this run was scored against the hand-authored C1S1
gold fixture (`evals/graph_memory_layer/examples/session_1_candidate_graph_gold/candidate_graph_gold.json`,
24 gold edges / 26 gold nodes) using the real identity-resolution comparator
(`evals.graph_memory_layer.live_vs_gold_compare.compare_parts`, the same best-match-assignment +
predicate-family-folding engine used for the S23 gold work), run directly against the raw candidate
graph JSON for three artifacts: the two pre-existing vocabulary-ablation runs and this dogfood's
output.

| Run | node_recall | edge_recall | node_precision_proxy | edge_precision_proxy |
|---|---:|---:|---:|---:|
| `old_baseline` (vocab ablation, no packet) | 76.9% (20/26) | 29.2% (7/24) | 42.6% | 25.0% |
| `old_edge_and_node_packet` (vocab ablation) | 69.2% (18/26) | 29.2% (7/24) | 38.3% | 28.0% |
| **`category_encounter_job_preview` (this run)** | 73.1% (19/26) | **37.5% (9/24)** | 38.8% | 26.5% |

**Edge recall did move: 29.2% → 37.5%, +2 gold edges recovered on the same 24-edge gold set.**
Node recall is flat-to-slightly-down (this run sits between the two prior runs, not clearly better
or worse — 49 candidate nodes vs 26 gold nodes means precision is doing a lot of the work here, and
none of the three runs auto-merged a single cross-class collision: `merged_nodes: []` for all
three).

Important nuance the aggregate number hides — the two edges this run newly recovered are **not**
the encounter/job edges the profile was built to add:

- `edge:pub-located-in-stonebridge` (River's Edge Pub `located_in` Stone Bridge)
- `edge:jobboard-located-in-stonebridge` (job board `located_in` Stone Bridge)

Both are generic `location_pass`/`edge_pass` containment edges, unrelated to `encounter_job_pass`
or `party_participation_attachment`. The quest/combat-specific edges this dogfood highlighted as
qualitative wins in §6 (`quest → mission_targets → creature`, `party → pursues → quest`,
`combat → results_in → quest`, etc.) were checked directly and **do not score as gold matches**:

```text
edge:party-accepts-job   (gold: heroes/party --undertakes--> "the rat-clearing job")
  best live candidate: our party --pursues--> quest_glowkindle_rat_cleanup_001
  endpoint_score: 0.0  — blocked upstream by the node-level miss below, not a predicate check alone

edge:party-travels-to-brewery (gold: heroes/party --travels_to--> brewing co)
  no live edge scores above threshold; nothing in this run represents "travel to the brewery"
  as an edge (it's represented as the quest_follow_brewery_directions_001 node instead — see below)
```

Root cause, traced one level deeper: `node:rat-clearing-job` (gold, `node_type: thread`) never
matches `quest_glowkindle_rat_cleanup_001` (this run, `node_type: quest`) even though `quest` and
`thread` fold to the *same* identity class (`node_type_class("quest") == node_type_class("thread")
== "thread"`, confirmed directly). The miss is pure label similarity — "Glowkindle's rat cleanup
request" vs "the rat-clearing job" scores `node_match_score` **0.23**, well under the 0.6 match
threshold — compounded by an evidence-scheme mismatch: gold cites curated `source_anchor_id`s,
this run's live extractor cites paragraph-level `source_span_ref_id`s, and the comparator's
same-source rescue boost (`anchors_overlap`) needs literal anchor-id overlap that isn't present
when scoring the raw artifact directly (the full pipeline's resolved-span data wasn't threaded
through this ad-hoc comparison). The same pattern holds for `combat_rat_fight_brewery_001` vs
gold's `node:rat-cellar-combat` ("the rat cellar fight") — class matches (`combat_encounter` and
`event` both fold to `phenomenon`), but label score is **0.22**.

Two important caveats on top of the number itself:

1. **The C1S1 gold fixture predates this taxonomy.** It was hand-authored before `quest` and
   `combat_encounter` existed as node types (it uses `thread` and `event`), so it was never built
   to reward the specific capability this profile adds — it's a real but not entirely fair
   yardstick for this spike. A fresh gold slice with `quest`/`combat_encounter` node types would
   score this profile's actual target capability more honestly than the retrofitted comparison
   above.
2. **The segmentation bug (§9) is a hard recall ceiling, not a tuning problem.** 5 of the 7 missing
   gold nodes this run failed to recover — `flaming magma infused spider monstrosity`, `the
   shatter mage's tower mystery`, `the shatter mage's tower`, plus knock-on edges to them — live in
   the exact paragraph the paragraph-splitter silently drops. No amount of prompt refinement
   recovers content that was never sent to any pass. This is independent confirmation, from the
   gold side rather than the source-text side, that PR-recommendation #1 (fix the segmentation
   bug) gates any further recall measurement on this recap.

**Bottom line for the discussion:** aggregate edge recall moved in the right direction (+2 edges,
+8.3 points) on a fair same-methodology comparison against the two prior runs, but not yet *because
of* the encounter/job mechanism specifically — the two recovered edges are generic location edges,
plausibly run-to-run LLM sampling variance rather than a profile effect. The encounter/job edges
this dogfood judged qualitatively strong in §6 are real, correctly typed, and evidence-backed, but
don't yet register against an automated gold score built for a different (pre-encounter/job)
taxonomy — closing that gap needs either a refreshed gold fixture with `quest`/`combat_encounter`
nodes, or a label-similarity/predicate-family tuning pass so this profile's phrasing converges on
gold's phrasing for the same real-world objects.

## Addendum 2 — skeptical review of the C1S1 gold fixture itself

The addendum above treats gold as ground truth and asks why the live run misses it. This section
turns the question around: **is the gold fixture itself still a trustworthy yardstick**, and are
there things this run picked up that gold simply never wrote down (so no extractor could ever be
credited for them, independent of quality)?

### Correction to this report's own §12 claim

§12 stated "7 of 42 raw model nodes (17%) are exact-label collisions." Re-checked this directly by
clustering all 49 live nodes on normalized label text: it's **7 clusters comprising 17 nodes**, not
7 nodes — i.e. **~40% of the 42 model-produced nodes** (17/42) sit inside a same-label collision
cluster, not 17%. One of the 17 (`item_stone_bridge`, "a bridge over the river near the town of
Stone Bridge") is arguably a *legitimate* distinct referent sharing an ambiguous label — it's the
physical bridge, matching gold's own explicit `node:stone-bridge-span` — mirroring the exact
town-vs-bridge ambiguity gold flags with a `do-not-merge` warning. Excluding that one node, true
same-referent duplication is still **16/42 (~38%)**:

| Cluster (normalized label) | live node types produced |
|---|---|
| "giant rats" | `character` + `group` + `item` (3-way) |
| "Stone Bridge" (the town) | `location` + `faction` (2-way; the 3rd, `item`, is the bridge, not the town) |
| "The River's Edge Pub" | `location` + `organization` + `item` (3-way) |
| "Wizard's Tower Brewing Company" | `location` + `item` (2-way) |
| "the troupe of gnomes" | `character` + `group` (2-way) |
| "mysterious cat owl" | `character` + `item` (2-way) |
| "enormous boulder" | `location` + `item` (2-way) |

This is materially worse duplication pressure than §12 conveyed, and it's a real thing to fix in the
next cross-class-identity PR, not a rounding error. Also caught in the same pass: `creature_giant_rats_001`
carries `node_type: "character"` despite the `creature_`-prefixed ID — a distinct, smaller
ID/type-consistency bug worth a one-line note in the same follow-up PR.

### Is the gold fixture still a good example?

Directionally yes for what it was built for (a hand-checked node/edge shape for the *pre-quest/
combat_encounter* taxonomy, and a good demonstration of the town-vs-bridge do-not-merge pattern and
the unnamed-river `ignored_item` pattern). But re-reading it against the raw source recap surfaces
real, material gaps that inflate how bad "26% edge recall" and "29% edge recall" have looked across
*every* run scored against it (baseline, vocabulary ablation, and this encounter/job run alike):

1. **Gold's own node descriptions assert relationships gold never encodes as edges.**
   `node:karsemine`'s description reads "searches the tower interior and **spots the magma
   spider**" — but the 24-edge gold list has no `karsemine → spots → magma-spider` edge at all.
   `node:firkin-of-ale`'s description reads "Firkin of ale **Bonogo buys** for two gold" — no
   `bonogo → buys → firkin-of-ale` edge exists, and no edge ties the firkin to the pub where it was
   bought either. This is the exact same "PC-specific action capture is thin" gap the
   vocabulary-ablation report flagged as a *live-extraction* weakness — except here it's baked into
   the gold itself. No extractor, however good, can be credited for an edge the gold author
   described in prose but never promoted to the edge list. Some fraction of the "stuck ~29%" edge
   ceiling across all prior dogfood runs is gold under-specification, not extractor failure.
2. **Editorial thoroughness is inconsistent.** Gold captures the firkin of ale (a minor two-gold
   purchase) as its own `item` node, but skips: the excavation-wall breach (the literal causal
   reason rats are a problem — arguably more plot-relevant than the ale), the magical crystals
   lighting the tap room, and the "many, many, many health potions" the source text explicitly
   emphasizes as a marker of how hard the fight was. There's no stated principle for what crosses
   the "worth a node" bar, and the choices don't track narrative importance consistently.
3. **The unnamed-river discipline isn't applied elsewhere.** Gold explicitly suppresses a canonical
   river name via a well-reasoned `ignored_item` ("do not promote a canonical river name from this
   span"). Good practice — but the boulder/statue-foot beat, where the source text *itself* plays up
   an unresolved ambiguity ("what must have been the foot of a once enormous statue. Or a mad
   sculptor's dedication... who really knows with art anyway"), gets flattened into one flat
   `location` node with no `ignored_item`, `deferred_item`, or narrative-thread treatment at all.
   That's a real mystery hook the source text lampshades and gold discards rather than preserves.
4. **Taxonomy gap (already known, restated for completeness):** zero `quest`/`combat_encounter`
   nodes exist in gold; the job is a `thread` and the fight is an `event`. Any run using the new
   taxonomy is structurally capped on this fixture regardless of quality.

### Things this run picked up that gold has no slot for (so can never be credited here)

Cross-checked every "extra" live node/edge against the raw source text. Filtering out the
already-documented cross-class duplicates (giant rats, the pub, the brewery, the cat owl, the
gnomes, the boulder — see table above) and the known quest-overgeneration node, what's left is real
source content gold simply didn't write down:

- **`combat → results_in → quest`** — ties the fight's outcome back to the job that spawned it.
  Gold has no combat/quest nodes to hang this on at all, so this can never score as a match no
  matter how correct it is.
- **The excavation-wall breach** (`item_excavation_wall_breach`) — the actual causal link between
  "cellar expansion" and "rats attacked the crew." Real, source-grounded, zero gold counterpart.
- **Wayfinding detail** — "the big rock" and "the clear trail along the river" (`loc_big_rock`,
  `item_clear_trail`) — real navigation landmarks from Grishna's directions, zero gold counterpart.
- **Magical crystals and health potions** — both directly quoted from source, zero gold counterpart
  (see thoroughness point above).
- **Deterministic party → quest/combat edges** (`pursues`, `participates_in`) — correct and
  non-duplicating (§7), but unscoreable by construction since gold has no quest/combat nodes for
  them to attach to.

None of this changes the Yellow verdict or the recommended-PR ordering in §13 — the quest
overgeneration and cross-class duplication findings stand, and are if anything *worse* on
duplication than originally stated. What it does change: **the ~29–38% edge-recall ceiling seen
across every run against this fixture should not be read as "the extractor is only a third as good
as it should be."** A meaningful, unmeasured fraction of that gap is the gold fixture under-encoding
its own narrated relationships and inconsistently curating minor content — a data-quality problem on
the yardstick, not purely a capability gap in the thing being measured. Recommend folding a **gold
fixture refresh** (add the missing narrated edges in point 1 above, add `quest`/`combat_encounter`
node types, decide a stated inclusion bar for minor items) into the next Prime Design pass, rather
than trusting recall deltas against this fixture as the primary success signal for further
encounter/job tuning.

## Addendum 3 — segmentation fix, vocabulary-packet wiring, and gold/baseline/vocabulary 3-way comparison

Two follow-on actions after Addendum 2's gold-fixture remediation (now `v1`, applied separately —
see `Backlog.md` Follow-up 3): (1) fixed the paragraph-segmentation trailing-newline bug identified
in §9/Addendum 1, and (2) wired the static, corpus/registry-derived context vocabulary packet (the
same packet used by the vocabulary-ablation dogfood) into the real runtime encounter/job path, which
previously had no way to enable it at all. Both changes are documented in full in `Backlog.md`
(Follow-up 4 and Follow-up 5).

**Segmentation fix.** `_split_recap_paragraph_spans`'s lookahead was changed from
`(?=\n\s*\n|\Z)` to `(?=\n\s*\n|\s*\Z)`, so a source file ending in a single trailing newline (every
normally-saved recap) no longer silently drops its final paragraph. C1S1's paragraph span count went
8→9; the final paragraph's content (the magma-infused spider monstrosity, the shatter mage's tower)
is now present in every run's candidate graph regardless of vocabulary setting.

**Vocabulary wiring.** `GraphPreviewRunnerOptions` gained `context_vocabulary_packet`,
`enable_node_vocabulary_packet`, and `enable_edge_vocabulary_packet` fields, threaded through
`category_options_for_graph_extraction_profile` into the extractor's existing (already-supported but
previously unreachable from this path) `CategoryGraphExtractionOptions` vocabulary fields. The
manifest's `diagnostics` block now records `context_vocabulary_packet_id` and both enable flags for
every run, so any future review UI can show at a glance whether a given run used vocabulary
assistance. `run_encounter_job_dogfood.py` gained `--enable-vocabulary-packet`, which reuses the
exact same C1S1 packet (`BED_CONFIGS["c1s1-stonebridge"]`) already vetted by the vocabulary-ablation
dogfood, rather than inventing a second one.

**Three-way comparison (gold `v1` vs. baseline vs. baseline+vocabulary, both post-segmentation-fix,
`category_encounter_job_preview` profile, real model extraction):**

| Run | node_count | edge_count | merged_nodes | blocked_nodes | node_recall | edge_recall | node_precision_proxy | edge_precision_proxy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline (no vocab) | 53 | 33 | 0 | 7 | 66.7% | 23.3% | 34.0% | 21.2% |
| baseline + vocabulary | 46 | 33 | 1 | 4 | 59.3% | 26.7% | 34.8% | 24.2% |

Runs: `out/graph_memory/runs/longmont-c1/session-1/20260701T204317Z/` (baseline) and
`out/graph_memory/runs/longmont-c1/session-1/20260701T215207Z/` (baseline+vocabulary); both
git-ignored, preview-only, `preview_union_store_ready`, selectable in the Graph Gold Review run
picker.

**Reading the delta, node-by-node and edge-by-edge (not just the aggregate):**

- Vocabulary **helped structural consolidation** — cross-class blocked collisions dropped 7→4 and
  produced the run's first auto-merge (0→1), with 7 fewer raw nodes overall (53→46). This is the
  same "vocabulary helps recognition/consolidation" pattern the earlier vocabulary-ablation dogfood
  found on this same recap.
- Vocabulary **recovered 2 new gold nodes** (`Glowkindle's excavation crew`, `the troupe of gnomes`)
  and **2 new gold edges**, both spatial-containment (`The River's Edge Pub is in Stone Bridge`, `the
  job board is in Stone Bridge`) — consistent with the ablation dogfood's "vocabulary is directionally
  useful for spatial containment" finding.
- Vocabulary **regressed 4 previously-matched gold nodes** (`Giant rats`, `The Wizard's Tower Brewing
  Co`, `the Stone Bridge`, `the fermentation cellar`) and **1 previously-matched edge** (`the Stone
  Bridge spans the river at Stone Bridge`) — not because the underlying content disappeared, but
  because vocabulary-influenced relabeling/consolidation shifted these nodes' surface phrasing enough
  that the comparator's label-similarity match to gold's specific wording broke. This is the same
  "actively harmful to institutional identity" pattern flagged in the vocabulary-ablation work,
  showing up here as a comparator-visible regression rather than a real content loss.
- Net result is a wash on the aggregate score (node recall down 7.4 points, edge recall up 3.4
  points, both precision proxies up slightly) — **directionally consistent with, not contradicting,**
  every prior vocabulary finding in this repo: vocabulary trades some label-matching stability for
  better structural consolidation and spatial-edge recovery. One run is not enough to promote or
  reject vocabulary-by-default for this profile; it is enough to say the effect is real, repeatable
  in direction (matches the C1S1 ablation dogfood's node/edge pattern), and orthogonal to the
  segmentation fix (both runs recovered the previously-dropped final paragraph equally).

**Explicitly not done in this pass** (by the user's own sequencing decision): no attempt to build a
unified "Graph Exploring" tool combining Graph Preview, Graph Gold Review, Vocabulary Review, and
Party Registry. That design question — including whether Party Registry (a write path) belongs in
the same surface as the three read-only diagnostic tools, and whether the unified tool should extend
Graph Gold Review's existing run-picker/comparison base rather than being built from scratch — is
deliberately deferred to a future Prime Design pass. See `Backlog.md` Follow-up 5 for the full
scoping conversation and the user's answers on sequencing, Party Registry scope, and merge base.
