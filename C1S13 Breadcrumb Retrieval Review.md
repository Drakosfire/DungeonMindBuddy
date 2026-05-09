C1S13 Breadcrumb Retrieval — Skeptical Failure Analysis
0. Anchor: what this benchmark is supposed to prove
From evals/sentence_routing_retrieval_falsification/C1S2_BENCHMARK_CONTRACTS.md §"Goals":

Goal: Prove lexical + route-grounded retrieval from the breadcrumb artifact supports accurate answers in recall, prep, and planning-shaped questions.

C1S13 is a holdout of that same contract on a session whose breadcrumb body has only just been ingested. The retriever itself is generic — it consumes a session-memory JSONL produced from a dmb_recap_breadcrumbs_v1 artifact and ranks records by:

lexical token overlap on record.lexical_plain, plus
routes attached to each record (record.routes[]) emitted by inline tags and the synthetic frontmatter "meta" record.
Anything corpus-specific (slugs, aliases, location/NPC routes) is not baked into retriever code — it is supposed to come from the breadcrumb artifact (which itself is supposed to come from the LLM-driven ingestion step that hits the readiness gate in breadcrumb_query_run). See .cursor/rules/llm-context-discovery.mdc and Docs/Learnings/LEARNINGS-Corpus-Layout-For-LLM-Grounding.md.

That framing is what makes the C1S13 numbers below diagnosable rather than mysterious.

1. Headline numbers
all_ok=False, scenarios=27, passed=0
cohort LLM cost ≈ $0.1027 (mean $0.00380, gpt-5.3-chat-latest)
universal violation: missing_expected_route_hit  → 27 / 27 scenarios
Per-scenario verdict table (extracted from evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s13_report.json): see the run table in §3 below — strict semantic_verdict is pass_updated on 17/27 scenarios while every scenario fails route coverage.

That asymmetry — "answer text is OK, route gates aren't" — is the whole story. It is not a retriever logic bug. It is an ingestion pipeline output gap that the benchmark correctly punishes.

2. The single decisive finding
C1S13's breadcrumb artifact contains zero inline tags. Every other session has inline tags; only C1S13 was bootstrapped from a "zero-tag" body to satisfy the prompt-rewriting readiness gate.

evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.breadcrumbed.md (lines 85–90):


Session
Lines 85-90
  inline_tags:
    PC: 0
    NPC: 0
    Location: 0
    Party: 0
    NewHubCandidate: 0
For comparison (same counts_by_subject_type.inline_tags block):

Session	PC	NPC	Location	Party	NewHubCandidate
C1S1 (Session 1 - Recap 3-27-24.breadcrumbed.md)
9
6
11
6
1
C1S2 (Session 2 - Finishing the Job.breadcrumbed.md)
0
4
5
2
2
C1S3 (Session 3 - The Stone Bridge Flood.breadcrumbed.md)
29
0
13
0
20
C1S13 (Session 13 - The Meaty and the Dead.breadcrumbed.md)
0
0
0
0
0
This propagates straight into the JSONL the retriever sees:

records_meta.jsonl: 69 lines total, 68 with "routes": []
only meta-session-0013-locations carries routes (3 Locations from frontmatter)
evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s13_report.records_meta.jsonl line 1 (representative empty-route record) and the only non-empty record:

unit_id=u-L0005-01  lexical_plain="Torbin"               routes=[]
unit_id=u-L0017-02  lexical_plain="Mossglade comes…"     routes=[]
unit_id=u-L0021-04  lexical_plain="…Wolf's head…"        routes=[]
unit_id=meta-session-0013-locations  routes=[Location:stormspire_academy/, council_chambers/, basement_morgue/]
So no record about Mossglade, Cinderbranch, Tealeaf, Necromancer, Draven, Bonogo, etc. ever surfaces an NPC/PC route. That is exactly what the universal missing_expected_route_hit is reporting, and exactly what unique_routes_in_top9 shows for every scenario in §3 — the only routes ever returned across all 27 scenarios are the same three Location routes from the meta record.

3. Failure buckets (with concrete evidence)
I am keeping the bucketing oriented at root cause, not at which violation flag tripped. Every scenario also trips missing_expected_route_hit; that flag is a symptom of the buckets below, not its own bucket.

Bucket A — "Zero-tag corpus": no per-line routes (root cause for ALL 27)
Cause: the breadcrumb body has zero inline tags, so retrieval can never put Wolf, Bonogo, Mossglade, Professor Cinderbranch, etc. on a route. The only routes it can emit are the three Locations on the meta record.

Evidence (top-9 unique routes per scenario, copied verbatim from a structured walk over full_result.hits[:9]):

wolf_head_why_academy            → routes = [stormspire_academy/, council_chambers/, basement_morgue/]
covert_ops_meat_check            → routes = []                          (meta record didn't surface in top-9)
stormspire_activity_arrival      → routes = [stormspire_academy/, council_chambers/, basement_morgue/]
morgue_combat_mechanical_prep    → routes = [stormspire_academy/, council_chambers/, basement_morgue/]
stormspire_who_shows_up_…        → routes = [stormspire_academy/, council_chambers/, basement_morgue/]
mossglade_residency_vs_assoc.    → routes = [stormspire_academy/, council_chambers/, basement_morgue/]
necromancer_question_identity_t. → routes = [stormspire_academy/, council_chambers/, basement_morgue/]
bonogo_poison_bite_sequence      → routes = [stormspire_academy/, council_chambers/, basement_morgue/]
The expected substrings are NPC/PC/entity names (Wolf, Mossglade, Bonogo, Sewer Meat Monster, Elite Guard 2, Stafl, Draven, Professor Cinderbranch, Wolf, Lira, Shepherd). With zero inline tags they cannot appear in retrieved routes. This bucket is unfixable without re-ingestion — there is nothing for the retriever to do here.

This is consistent with the project rule: don't overfit the retriever to the corpus. The retriever is correctly returning what is in the index; the index is impoverished.

Bucket B — Synthesis-grade pass even with zero-tag retrieval (17/27)
Even with no routes, the LLM read the lexical-only context and produced an answer that satisfied the gold's must_hit_tokens semantically. These trip route gates only.

Examples (verdicts copied from the report):

wolf_head_why_academy        ok=False  semantic=pass_updated  ctx=1.00  llm_ctx=1.00
guards_oily_eyes_alert       ok=False  semantic=pass_updated  ctx=1.00  llm_ctx=1.00
party_first_split_assignments ok=False  semantic=pass_updated  ctx=1.00  llm_ctx=1.00
mossglade_residency_vs_assoc ok=False  semantic=pass_updated  ctx=1.00  llm_ctx=1.00
torbin_thread_status_end     ok=False  semantic=pass_updated  ctx=1.00  llm_ctx=1.00
study_room_short_rest_song   ok=False  semantic=pass_updated  ctx=1.00  llm_ctx=1.00
Net: lexical-only retrieval was sufficient for the LLM to answer 17/27 questions correctly in content. The retriever is doing useful work; it just cannot back its answer with grounded routes.

Bucket C — Lexical recall gap on combat / mechanical-prep questions (4)
Cause: the query token bag, after restrained-stopword filtering, doesn't lexically overlap the actual combat sentences enough to surface them in the top‑k.

morgue_combat_mechanical_prep    semantic=fail_incomplete  ctx=0.29  llm_ctx=0.00  surface=retrieval_gap
                                 strict_must_hits=['poisoning','bites']        (gold expected 7)
                                 missing route subs=[Draven, Elite Guards, Sewer Meat Monster, Bonogo]
stormspire_activity_arrival      semantic=fail_incomplete  ctx=0.25  llm_ctx=0.25  surface=retrieval_gap
                                 strict_must_hits=['Stormspire Academy']       (gold expected 4: …potions, runes, wards)
next_session_sewer_direction     semantic=fail_incomplete  ctx=0.40  llm_ctx=0.40  surface=retrieval_gap
shepherd_break_of_dawn_hook      semantic=fail_incomplete  ctx=0.50  llm_ctx=0.50  surface=synthesis_gap
These would benefit from inline [NPC:draven]/[Location:basement_morgue] tags (which would also let the retriever's route-family expansion pull adjacent units), but they are also lexically weak — query terms like "reconstruct", "mechanically", "battlefield" do not overlap with the recap's narrative phrasing. This is classic shallow lexical retrieval failure that route-grounded retrieval is supposed to mitigate; in C1S13 it can't, because no routes.

Bucket D — Disambiguation collapse (4)
Adjacent-action and pronoun-collision scenarios where the right answer requires sequence preservation, and lexical retrieval ends up mixing the two collisions.

wolf_killer_disambiguation               surface=synthesis_gap   llm_ctx=0.40
lira_shepherd_plot_disambiguation        surface=synthesis_gap   llm_ctx=0.43
elite_guards_city_guards_disambiguation  surface=synthesis_gap   llm_ctx=0.43
necromancer_question_identity_trap       surface=synthesis_gap   llm_ctx=0.80
These are the cases where having [NPC:wolf], [NPC:bonogo], [NPC:draven] tags on the specific sentence ("He nods towards Bonogo" / "Draven closes and locks the door") would have prevented the retriever from blending in later combat sentences.

Bucket E — Query-mode routing miss on the location-entity-list scenario (1)
Specific to stormspire_who_shows_up_location_entity_list:

violations = [
  "missing_expected_route_hit",
  "query_mode_mismatch",                  ← gold expected location_entity_list, runtime used lexical_route_overlap
  "missing_location_entity_summary",
  "llm_semantic_verdict:fail_incomplete",
  "llm_context_support_below_threshold"
]
Why the mode flipped: _is_location_entity_list_question(query) in src/agent/session_memory_query.py:242 is a regex heuristic with a closed vocabulary:


session_memory_query.py
Lines 242-259
def _is_location_entity_list_question(query: str) -> bool:
    """Heuristic: GM is asking for a roster of people/NPCs tied to a place name."""
    ql = str(query or "").lower()
    if re.search(r"\b(npcs?|characters|people|residents?|townsfolk)\b", ql):
        return True
    if re.search(r"\blist of\b", ql) and re.search(
        r"\b(npcs?|people|characters|residents?)\b", ql
    ):
        return True
    if re.search(r"\ball\b", ql) and re.search(r"\b(npcs?|characters|people)\b", ql):
        return True
    if re.search(r"\bwho\b", ql) and re.search(r"\b(npcs?|characters|people)\b", ql):
        return True
    if re.search(r"\bwho\b", ql) and re.search(
        r"\b(live|lives|living|reside|residing|residents?|staying)\b", ql
    ):
        return True
    return False
The C1S13 question reads:

"Who shows up or is meaningfully present at Stormspire Academy during this session?"

It contains who but pairs it with "shows up" / "meaningfully present" — neither of which is in the heuristic's vocabulary. So the query falls through to lexical_route_overlap and the location-entity aggregator never runs. The benchmark also encodes intent_hint: "location_entity_list" in gold (line 542 of breadcrumb_query_natural_c1s13_v1.json) — which the runtime currently does not consume as a fallback signal.

There's also a second failure on this same scenario that would have surfaced even if the heuristic matched: the location-entity aggregator builds its roster from records co-tagged with the location route. With zero inline tags, the only co-tagged record is the meta record (which has no NPCs). Result: an empty entities[]. So this scenario actually fails twice — once at intent routing, once at aggregation feedstock.

Bucket F — Forbidden-token injection (sub-failure on Bucket E)
Specific to the same Stormspire scenario, gold (line 560):


breadcrumb_query_natural_c1s13_v1.json
Lines 560-565
"forbid_location_entity_route_substrings": [
  "Thalia",
  "Lira",
  "Shepherd",
  "covert ops groups"
]
The LLM answer for this scenario doesn't actually leak Thalia/Lira/Shepherd, but it does invent an "academy itself is described as 'bustling with activity', implying many other students or staff are around" — recap-phrasing-faithful but speculative. The retriever has no defense for this; the gold gates it via forbid_location_entity_route_substrings, which only fires if the location-entity aggregator runs (Bucket E), which it doesn't.

4. Deep dive: stormspire_who_shows_up_location_entity_list
Pulling all the wires for the specific question you asked about.

4a. What got retrieved
full_result.hits — top hit is the meta record, which provides the only routes; everything else is body sentences with routes: []:


breadcrumb_query_natural_c1s13_report.json
Lines 26800-26834
      "hit_count": 18,
      "top_hit": {
        "hit_id": "4db2914a5cd2d8db4bb7",
        "score": 8,
        "source_recap_path": "Longmont Campaign/Campaign 1/Session Recaps/Session 13 - The Meaty and the Dead.md",
        "unit_id": "meta-session-0013-locations",
        "line_start": 0, "line_end": 0,
        "routes": [
          {"subject_class":"Location","normalized_route":"Longmont Campaign/Campaign 1/Locations/stormspire_academy/", ...},
          {"subject_class":"Location","normalized_route":"Longmont Campaign/Campaign 1/Locations/council_chambers/",   ...},
          {"subject_class":"Location","normalized_route":"Longmont Campaign/Campaign 1/Locations/basement_morgue/",     ...}
        ],
        "why_matched": ["lexical_token:stormspire","route_token:stormspire","lexical_token:academy","route_token:academy"]
      }
Body sentences that do mention Mossglade / Cinderbranch / Tealeaf / Necromancer were retrieved by lexical overlap on academy/stormspire only — every one of them carries routes: []. So they reach the LLM as text but they never participate in route gating.

4b. What the LLM produced

breadcrumb_query_natural_c1s13_report.json
Lines 27183-27184
      "llm_answer_preview": "At Stormspire Academy in this session, the primary people present are the party members themselves: Bonogo, Stafl, Caelynn, Baergrom, and Karsemine. They arrive together, bringing the Wolf … There are also academy-affiliated NPCs present. A Necromancer is explicitly someone Stafl and Bonogo go to meet … additionally, at least one unnamed mage appears … the academy itself is described as 'bustling with activity,' implying many other students or staff are around …"
The LLM answered correctly on PCs + Necromancer + Wolf-as-remains, but did not mention Mossglade, Professor Cinderbranch, Professor Tealeaf, or Torbin, which the gold expected. Why? Look at what fragment of the body actually made it into llm_user_message:


breadcrumb_query_natural_c1s13_report.json
Lines 27186-27186
      "llm_user_message": "Question:\nWho shows up or is meaningfully present at Stormspire Academy during this session?\n\n### Retrieved excerpts and routes (only source you may use)\nsession locations location places place setting map stormspire_academy Primary session location for academy events. … The group has decided … Wolf to Stormspire Academy … bustling with activity. Bonogo … removes the Wolf's head … the tainted meat is burned up by one of the mages. … escaped … Stafl and Bonogo will go meet the Necromancer for the ritual while Caelynn, Baergrom and Karsemine will hunt for the meat.\n"
The promoted "lexical hit context" did not include the Mossglade/Cinderbranch/Tealeaf/Torbin sentences (they are at line 23, 25, 27 in the body and only score 1 on lexical overlap with the query tokens "shows", "meaningfully", "present", "stormspire", "academy"). They got expanded into retrieval_hit_context_full but they aren't in the prompt the LLM actually used. So the LLM is grounded in a subset of the page — and that subset doesn't carry the names the gold expects.

This is the cleanest possible falsification: the data the model is allowed to see does not contain the answer's missing entities, and route gating cannot rescue them because nothing is tagged.

4c. What the canvas was telling you (and why your earlier fix was on-target)
The canvas matcher in evals/sentence_routing_retrieval_falsification/c1s13_benchmark_canvas_emit.py:29-38 does an alphanumeric-normalised substring match to bridge "Stormspire Academy" ↔ …/stormspire_academy/. After your fix it correctly resolves the expected substring against Longmont Campaign/Campaign 1/Locations/stormspire_academy/. The "Matched? = Yes" you now see is honest. But the route check inside the run report uses a different code path: context_evidence_metrics.route_substrings_missing_in_top_k (in breadcrumb_query_grader.py), which does its own substring check, and it correctly reports Stormspire Academy as missing — not because the route isn't there, but because the meta record didn't make it into top-k for this scenario (top-k is the first 9 hits ranked by score; meta ranks #1 and is in top-k, so this needs another look — see §6 Open Questions).

5. Skeptical pass: oracle / cheating audit
Three things crossed the line into "is this an oracle?" Each is graded on the project's "anti-oracle" spec in C1S2_BENCHMARK_CONTRACTS.md §"Anti-oracle (leakage) guardrails".

5a. Hand-authored frontmatter entity_index (real but acknowledged)
evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.breadcrumbed.frontmatter_seed.md was hand-curated from the recap during the bootstrap iteration where the LLM kept failing the readiness gate. That seed enumerates Mossglade, Professor Cinderbranch, Professor Tealeaf, Torbin, Necromancer, Draven, Elite Guard, Sewer Meat Monster, Wolf, Thalia, Lira, Shepherd, … as new_hub_candidates — names that nobody outside the corpus would know.

Why this matters: those slugs flow into the lexicon (extract_hub_aliases.extract_hub_aliases_from_frontmatter → assemble_lexicon) and become the equivalences you see in the run report (stormspire_academy → [academy, stormspire, stormspire academy], professor_cinderbranch → [cinderbranch, professor, professor cinderbranch], etc., report lines 27298‑27302, 27276‑27280). On a future session, these equivalences are supposed to be produced by the LLM ingestion step, not authored by hand.

Verdict: soft oracle, in the sense that:

The benchmark gold can still falsify retrieval (it does — 27/27 fail).
But the retriever's lexicon today is partially the product of human knowledge of the recap, not the LLM ingestion path. Any claim of "the retriever resolved Mossglade aliases correctly" should be footnoted with "because we hand-fed it the slug."
This is acknowledged as bootstrap state in the prior conversation's plan and in breadcrumb_prompt.py hardening; it is not a hidden cheat. But it should be removed before treating C1S13 as a "we proved retrieval works" data point. Re-running C1S13 ingestion through the LLM-driven path (and accepting whatever entity_index the LLM emits) is the only way to get a clean number.

5b. The lexicon also has a small generic seed (benchmark_lexicon_seeds_v1.json)

benchmark_lexicon_seeds_v1.json
Lines 1-22
{ "description": "Eval-harness-only semantic equivalence seeds and shadow-diff legacy route stopword snapshot. Loaded by token_resolver_shadow (not shipped in src/token_resolution defaults).",
  "equivalences": {
    "captain": ["lysandra","captain lysandra","ironveil"],
    "forest":  ["migrating forest","the forest"],
    "tower":   ["voices tower","tower drawing","drawing"],
    "voices":  ["voice","tower"]
  } }
This is fine in principle (it's a shadow-diff seed, not the production lexicon), but it does name captain → lysandra/ironveil etc., which is corpus-specific. It does not affect C1S13 retrieval — none of those equivalences are referenced by C1S13 queries. Mark it for future cleanup but it didn't influence this run.

5c. Gold's expected_answer strings include the precise phrasing the LLM also emits
I checked whether the gold strings could be leaking into the prompt. They are not — breadcrumb_query_run's LLM prompt only carries Question + retrieved excerpts, not gold (see the llm_user_message quote in §4b). Confirmed: not an oracle.

5d. The canvas emitter's substring matcher is not an oracle
_expected_matches_route (lines 29‑38 of the emit script) does a normalised-alphanumeric substring match. It runs after the run finished, only for canvas display. It cannot affect run pass/fail (which already wrote report.json). It is a UX shim, not a grader.

6. What this means about the goal ("retriever generic, no overfitting")
Reading the failure surface against the project anchor:

Retriever code is generic. No C1S13-specific path exists in src/agent/session_memory_query.py or src/agent/retriever.py. The 27/27 route-miss is driven by the data the retriever was given.
Retriever inputs are corpus-specific by design, but supposed to be generated by ingestion. C1S13 broke that because we seeded the frontmatter by hand and zeroed the inline tags. The retriever's worst case in C1S13 is exactly what you'd see if any future session arrived with no inline tags — which is the actionable insight: production ingestion must close the inline-tag readiness gap, or the retriever degrades to lexical-only (Bucket B answers correct, but every route gate fails).
The gold is honest. expect_route_substrings ask for things the body and the corpus actually establish. The benchmark is correctly catching that the index is degraded; it would be wrong to soften it.
7. Recommended next moves (no time estimates)
Two issues are addressable in the retriever without corpus overfitting; the rest are upstream-of-retrieval and need ingestion to do its job.

Retriever-only
Strengthen _is_location_entity_list_question (Bucket E). Today it requires explicit "people / NPCs / residents". Extend the heuristic to recognise presence-shaped phrasing (shows up, meaningfully present, who is at, who is in, who appears at) when followed by a location reference. This is generic English, not corpus-specific. Add intent_hint/expect_query_mode from gold as a fallback signal in the run harness so a benchmark can force the mode when phrasing is novel — but only as an opt-in for benchmark scenarios, not for production planner queries, otherwise tests become self-fulfilling.
Fail-loud when location-entity aggregation runs against a zero-tag index (Bucket E sub‑failure). Today it returns entities=[] silently. Have it surface a resolution_note like "no NPC routes co-tagged on this location; ingestion produced 0 inline tags" — that turns the zero-tag failure into an observable contract violation rather than an empty roster.
Ingestion (the actual root cause for Buckets A, C, D)
Re-ingest C1S13 with the prompt-based breadcrumb tagger until the readiness gate passes with non-zero inline tags. The current prompt hardening (no rewriting + sentence-unit self-check) is the right line; the bootstrapped zero-tag artifact should be treated as scaffolding, not the golden output. Rerun the C1S13 benchmark afterward and compare delta on Buckets A/C/D — that delta is the cleanest evidence that the retriever (unchanged) benefits from real tagging.
Stop hand-curating entity_index for new sessions. The seed file should be a bootstrap-only artifact and gated by a flag so anyone running ingestion sees a loud "this session is using a hand-authored seed" notice. Otherwise §5a's soft-oracle creeps in by default.
Benchmark gold (small, surgical)
The expect_route_substrings array on a few scenarios encodes mechanical things that aren't really routes ("Elite Guard 2", "ritual room", "sewer", "tunnel"). These trip route gates regardless of ingestion quality because they don't correspond to hub paths. Either move them into must_hit_tokens only, or define explicit Location slugs the corpus already has. (Don't loosen the rubric — realign the contract per verify-before-debug.mdc.)
8. Cost note
cohort sum = $0.1027
mean per scenario = $0.00380
n = 27 (gpt-5.3-chat-latest)
In-envelope; no regression to flag. Calling this out explicitly per cost-as-signal.mdc so the regression baseline for the next C1S13 cohort is on the record.

Net. The 27/27 failure on this run is one root cause masquerading as five violation flags: C1S13 was indexed without inline tags, so route-grounded retrieval is mathematically impossible, and lexical-only retrieval covers the easy questions (17/27 semantically correct) but cannot disambiguate adjacent collisions or run the location-entity aggregator. The Stormspire-presence question sits at the worst confluence — heuristic miss + zero-tag aggregator feedstock + LLM grounded only on the lexical-overlap subset of the body. The retriever is doing what it should; the contract violation is upstream