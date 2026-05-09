# Handoff: Corpus-Backed Entity Profiles for Top Wiki Entities (~138–142)

**Date:** 2026-04-09  
**Priority:** Medium (quality / eval interpretability — not blocking code merges)  
**Estimated effort:** Large; wall-clock depends on cohort size. **Discovery and first-pass synthesis are intended to run in Cursor auto mode** (see below) in disciplined batches; human review can tighten citations and adjudicate edge cases.

---

## Goal (canonical deliverable)

The **authoritative output** of this audit is **one JSON object per entity** that **validates against** `schemas/v0.1/corpus_entity_profile.schema.json` (`profile_kind: corpus_entity_audit`). See `schemas/v0.1/examples/corpus_entity_profile.example.json` for a **minimal** instance and `schemas/v0.1/examples/corpus_entity_profile.bonogo_exemplar.json` for a **full-depth** reference (same bar as §1 below).

That schema captures:

- `**integrated_summary`** — docs-only synthesis paragraph.
- `**citations[]`** — file-level evidence with `**layer_tags`** (`dossier`, `observed_play`, `gm_prep`, `ledger`, `item_or_mechanics`, `design_report`) for filtering and QA.
- `**narrative_layers`** — optional split prose (dossier vs play vs prep vs ledger) aligned with the Bonogo exemplar in §1.
- `**relationships`**, `**terminal_beats`** — structured edges and outcomes when relevant.
- `**store_reliability**` — typed `**caveat_kind**` (`none`, `alias_pollution`, `referent_mixing`, `thin_evidence`, `projection_divergence`) plus design-report paths.
- `**evidence_sufficiency**`, `**cohort**` (manifest / store / `list_wiki_targets` reproducibility).

**Human-readable markdown** (e.g. `entity_definitions_batch_*.md`) is a **projection** of the same content for review and diffs; the **JSON profile** is what we index, query, and regression-test.

Markdown batches may use the **compact template** in §6; rich entities should still **round-trip** into a full `CorpusEntityProfile` record.

---

## 0) Execution model — Cursor harness (auto mode), not a passive checklist

This work is **run by the Cursor agent in auto mode** as the primary executor: an **agentic** pass that **collects context about each entity** by **using the tools available** when they help — e.g. **repository search** (`rg` / grep), **reading corpus and design docs**, **semantic/codebase search**, `**uv run`** CLI against the **FactStore** (`list_wiki_targets`, `compile-wiki --list`, optional Python one-liners from §3), and **store inspection** — until it can emit a **validated** profile (or an explicit insufficient-evidence stub with `evidence_sufficiency: thin` / `absent`).

- **Not assumed:** A human manually grepping every entity without tool assistance, or a single bulk LLM dump without file-level citations.
- **Assumed:** The agent **follows this handoff**, **locks the cohort** (Phase 0), **discovers sources per entity** (Phase 1), and **writes CorpusEntityProfile JSON** (Phase 2) using the **depth bar** (Bonogo exemplar JSON in §1) and the **compact §6 template** where appropriate.
- **Human in the loop (optional but valuable):** Spot-check high-stakes names, resolve ambiguous referents, and approve the manifest parameters (store path, campaign, threshold).

---

## 1) What you are doing

Repeat the **Bonogo-style exercise** for **every entity in the “top wiki” cohort** (approximately **138** entities when using default wiki selection — exact count depends on store snapshot and `min_connectivity`; recent slice: **142** rows).

**Bonogo exercise (template):**

1. **Primary sources:** Read **campaign corpus markdown** (General Notes, Session Recaps, Session Prep) where the entity’s **proper name** appears; extract **who/what/when** with **file paths and quoted lines or section titles** as citations (map into `citations[]` with correct `**layer_tags`**).
2. **Secondary / caveat sources:** Read **internal design reports** that document **store-level failure modes** (e.g. alias merge, name pollution) when they apply to that entity or its neighbors (`store_reliability`, `design_report_paths`).
3. **Explicit non-authority:** Treat **projected attributes** and **compiled wiki text** as *hints*, not ground truth, unless cross-checked against corpus — the graph can **conflate** or **mislabel** distinct referents (see §5).

**Deliverable:** One `**corpus_entity_profile`** object per entity (JSONL line, JSON array batch, or one file per entity), **validated** against the schema, plus optional markdown mirror. Include a **store caveat** in `store_reliability` when the KB is known to be unreliable for that name.

### Reference exemplar (depth bar — Bonogo)

The depth bar for **major / high-connectivity** entities is a **single validated `corpus_entity_profile` object** with the same information density as a full dossier pass: rich `narrative_layers` (dossier, observed play, GM prep, adjacent ledger/world), many `citations[]` with `layer_tags` and session/campaign pointers, `relationships`, `terminal_beats` for plot-critical outcomes, and a substantive `store_reliability` block when the KB disagrees with corpus.

**Canonical file (must validate):** `[schemas/v0.1/examples/corpus_entity_profile.bonogo_exemplar.json](../../schemas/v0.1/examples/corpus_entity_profile.bonogo_exemplar.json)`. Edit that file when the exemplar changes; the block below is a copy for inline reading.

```json
{
  "schema_version": "0.1.0",
  "created_at": "2026-04-09T12:00:00Z",
  "updated_at": "2026-04-09T12:00:00Z",
  "record_status": "active",
  "extraction_pass_id": null,
  "profile_kind": "corpus_entity_audit",
  "entity_id": "ent_bonogo",
  "display_name": "Bonogo",
  "entity_class": "actor",
  "cohort": {
    "manifest_id": "entity_audit_2026-04-09",
    "wiki_connectivity_score": 1.5428,
    "list_wiki_targets_params": {
      "campaign_id": "longmont-c1",
      "min_connectivity": 0.3
    },
    "store_path": "evals/mirathorn_vertical_slice/output/phase_d_store",
    "store_git_commit": "3f108761355344b2ca3bf5793c866d3508ef4059"
  },
  "evidence_sufficiency": "sufficient",
  "insufficient_evidence_note": null,
  "integrated_summary": "Bonogo is documented as a Longmont PC whose written character sheet (evil-leaning retribution ideal, deep trust issues, malnourished bugbear-ish background, escape from elven captivity) lives in Longmont Campaign General Notes. In session recaps, the same name is the playable character who crafts, steals, performs in arenas, fights with daggers and whip, and—in C1 Session 12—is the agent of the Wolf’s terminal defeat, including the oily sheen / regret beat in the Campaign 1 Session 12 recap. Prep docs add social tone for specific scenes (e.g. Stacey) in session_20_stacey_stuart_marla_reference. Engineering documentation (REPORT §S5) warns that automated entity merging may have polluted Wolf ↔ Bonogo linking in the store, so corpus markdown remains the clearest intentional definition of Bonogo as a person while structured extraction should be validated separately.",
  "narrative_layers": {
    "dossier": "Under “Bonogo Characteristics” in General Notes: Personality—hides scraps of food and trinkets in pockets. Ideals—retribution: the rich must be shown what life and death are like in the gutters (Evil). Bonds—no one else should endure the hardships I’ve been through. Flaws—will never fully trust anyone other than myself. Appearance—tall and gangly from a malnourished upbringing. Backstory—recently escaped elves who held him captive in a “shitty zoo.”",
    "observed_play": "Session recaps (observed_session_recap where frontmatter exists) show a bugbear-typed, rogue-flavored PC: sneak, daggers, theft, arena/combat. C2 Session 10 (longmont-c2): goblin alchemy booth (green goo with a mind of its own); candy tent (lollipop → hair/fur monster; steals a child’s lollipop; feels watched); bone jewelry (ring whispers compliments); coliseum fight with Ogonob and Baergrom—strikes first vs glass-of-ale elemental, whip, crowd cheers; hooded figure watches again. C1 Session 7 Passing Mirathorn Gates: solid black ribbon vs faction colors; carnival game for toy airship (fails then wins). C2 Session 8: prone fight; crossbow/steady aim; kills priest with dagger through the eye, quip “Now I’m in your head”; ties Dustwalker with chain; maps with Bonogo; Mountain Iron Vale Gate. C1 Session 12: surprise round vs the Wolf; secret passage chase; caltrops, oil fire, knives; killing blow—oily sheen fades from Wolf’s eyes, regret at betraying Mirathorn (Mirathorn eval gold beat). C2 Session 12 (different file): Wanted posters; daggers at Dustwalker in bard competition; heavy melee vs Dustwalker and red cloaks; Academy cell check with Karsemine (Dustwalker apparently in cell). Consistent identity: crafting mishaps, theft and swagger, whip/dagger, recurring watched/paranoia, major violence including Wolf kill.",
    "gm_prep": "session_20_stacey_stuart_marla_reference: Bonogo should relate to Stacey as a fellow goblinoid chaos peer (“menace with promise”), not as generic adult authority. Scripted joke beat and Marla riposte as tone samples for one session—directorial, not guaranteed in-world canon.",
    "ledger_or_world": "Same General Notes file pivots under “Main World and Story Themes” to Shepherds/Maelthor, twisted meat, etc.—ambient campaign context adjacent to the Bonogo trait block; not mechanically the same as Bonogo-only paragraphs."
  },
  "relationships": [
    {
      "related_entity_id": "ent_the_wolf",
      "related_display_name": "the Wolf",
      "relation_summary": "Bonogo lands the killing blow after chase through secret passage (caltrops, oil fire, knives); recap states oily sheen fades from the Wolf’s eyes and regret at betraying Mirathorn (C1 Session 12)."
    },
    {
      "related_entity_id": null,
      "related_display_name": "Stacey",
      "relation_summary": "Prep: peer relationship—fellow goblinoid chaos, “menace with promise,” not generic adult authority (session_20 prep)."
    },
    {
      "related_entity_id": null,
      "related_display_name": "Dustwalker",
      "relation_summary": "C2 Session 8: helps tie up with chain after barn fight. C2 Session 12: Wanted posters, bard-competition daggers, melee; cell check with Karsemine."
    }
  ],
  "terminal_beats": [
    {
      "summary": "Killing blow on the Wolf: oily sheen fades from the Wolf’s eyes, replaced with regret at betraying Mirathorn.",
      "session": 12,
      "campaign_id": "longmont-c1"
    }
  ],
  "citations": [
    {
      "corpus_relative_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md",
      "layer_tags": ["dossier"],
      "authority": "canon_reference",
      "quote": "Bonogo Characteristics — Personality, Ideals, Bonds, Flaws, Appearance; GM-facing ledger_or_dossier",
      "session": null,
      "campaign_id": "longmont-c1"
    },
    {
      "corpus_relative_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Longmont Campaign General Notes.md",
      "layer_tags": ["ledger"],
      "authority": "canon_reference",
      "quote": "Main World and Story Themes — Shepherds, Maelthor, twisted meat (ambient; not Bonogo-only block)",
      "session": null,
      "campaign_id": "longmont-c1"
    },
    {
      "corpus_relative_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 10 - Recap.md",
      "layer_tags": ["observed_play"],
      "authority": "play_record",
      "quote": "Goblin alchemy, candy tent, bone ring, coliseum elemental fight, whip, watched/hooded figure",
      "session": 10,
      "campaign_id": "longmont-c2"
    },
    {
      "corpus_relative_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 7 - Passing Mirathorn Gates.md",
      "layer_tags": ["observed_play"],
      "authority": "play_record",
      "quote": "Black ribbon; carnival toy airship game",
      "session": 7,
      "campaign_id": "longmont-c1"
    },
    {
      "corpus_relative_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 8 - Recap.md",
      "layer_tags": ["observed_play"],
      "authority": "play_record",
      "quote": "Dagger through the eye — Now I’m in your head; tie Dustwalker; Mountain Iron Vale Gate",
      "session": 8,
      "campaign_id": "longmont-c2"
    },
    {
      "corpus_relative_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 12 - One Persistent Bugbear or Sneaky Fucking Bugbear.md",
      "layer_tags": ["observed_play"],
      "authority": "play_record",
      "quote": "As Bonogo deals the killing blow the oily sheen fades from the Wolf’s eyes",
      "session": 12,
      "campaign_id": "longmont-c1"
    },
    {
      "corpus_relative_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 12 - Recap.md",
      "layer_tags": ["observed_play"],
      "authority": "play_record",
      "quote": "Wanted posters, bard competition daggers vs Dustwalker, Academy cell with Karsemine",
      "session": 12,
      "campaign_id": "longmont-c2"
    },
    {
      "corpus_relative_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
      "layer_tags": ["gm_prep"],
      "authority": "planning_note",
      "quote": "Bonogo × Stacey as goblinoid chaos peers; joke beat / Marla riposte tone samples",
      "session": null,
      "campaign_id": "longmont-c2"
    },
    {
      "corpus_relative_path": "Docs/Design/REPORT-benchmark-shortcomings-and-successes.md",
      "layer_tags": ["design_report"],
      "authority": null,
      "quote": "§S5 — Wolf alias set incorrectly included Bonogo, Grishna, Torbin; proper-name pollution",
      "session": null,
      "campaign_id": null
    }
  ],
  "store_reliability": {
    "caveat_kind": "alias_pollution",
    "detail": "The knowledge graph must not be assumed to match narrative identity without audit: REPORT §S5 states the Wolf’s alias set incorrectly included distinct character names including Bonogo (along with Grishna, Torbin) due to over-aggressive fuzzy matching; proper-name pollution persists after mitigations. Wiki compiler input for ent_bonogo is projected facts, not full Session 12 markdown—definition-by-docs and definition-by-store can diverge (e.g. mixed bugbear vs location style labels).",
    "design_report_paths": ["Docs/Design/REPORT-benchmark-shortcomings-and-successes.md"]
  },
  "review_state": "draft",
  "author": "handoff:exemplar"
}
```

Lighter-touch entities can use the **compact template** in §6 only; still meet **success criteria** in §8 and populate required schema fields (minimum: `integrated_summary`, `citations`, `store_reliability`, `evidence_sufficiency`).

---

## 2) Why this exists

- **Wiki compilation** (`compile_entity_page`) is fed **projected facts only**, not raw evidence (`src/compiler/wiki_compiler.py` — `_format_facts_for_prompt`). Automated pages can **miss narrative** or **blend** entities if extraction merged aliases.
- **Benchmark / eval interpretability:** Gold questions and traces assume **narrative referents**; a **file-cited, schema-valid** profile helps adjudicate **fail_incomplete** vs **bad merge** vs **question fault**.
- **Regression asset:** A frozen **manifest + CorpusEntityProfile bundle** becomes a **spot-check** when re-ingesting or changing projection, and is **queryable** by caveat kind, layer tag, and sufficiency.

---

## 3) Scope: freezing “top ~138”

The wiki compiler selects targets by **composite connectivity** ≥ `**min_connectivity`** (default **0.3**), intersected with **projected entities**, minus **generic display names** (`should_skip_entity_for_wiki`), unless overridden.

**Authoritative list for a given store snapshot:**

1. Load the same `**FactStore`** path you use for Mirathorn / full-corpus work.
2. Call `**store.load()`** after constructing `FactStore` (otherwise lists are empty).
3. Run `**list_wiki_targets`** (see `src/compiler/wiki_compiler.py`) **or** REPL `**compile-wiki --list`** with the **same** `--campaign`, `--min-connectivity`, and generic-name flags as your batch wiki run.

**CLI note:** `uv run python -m src.cli --store <path> …` only parses global args; `**compile-wiki` is a REPL command**. Example:

```bash
printf 'compile-wiki --list --campaign longmont-c1\nquit\n' | uv run python -m src.cli --store <STORE_PATH>
```

1. **Record the printed count.** If it is not exactly 138, either:
  - adjust scope (document “N entities at threshold X on date Y”), or
  - trim/pad using **sorted-by-score** rows until you match the intended cohort (e.g. **top 138 by connectivity**).

**Optional:** Export rows to JSON/CSV once in Phase 0 so the audit does not depend on REPL scrolling:

```bash
uv run python -c "
from pathlib import Path
from src.store import FactStore
from src.compiler.wiki_compiler import list_wiki_targets
store = FactStore(Path('<STORE_PATH>'))
store.load()
rows = list_wiki_targets(store, campaign_id='longmont-c1', min_connectivity=0.3)
print(len(rows))
for eid, sc, dn in rows:
    print(f'{eid}\t{sc:.4f}\t{dn}')
"
```

Replace `campaign_id` / path with your **canonical** values.

---

## 4) Source hierarchy (use in order)


| Priority | Source                                                                                     | Role                                                            |
| -------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------- |
| A        | `corpus/eldyrwild-markdown/...` — **General Notes**, **Session Recaps**, **Session Prep**  | **Canonical prose** for “who is this?”                          |
| B        | `Docs/Design/REPORT-benchmark-shortcomings-and-successes.md` (and related quality reports) | **Known systematic errors** (e.g. alias pollution, fuzzy merge) |
| C        | Ingested **evidence unit** text in store (via `document_id` / grep in corpus)              | Tie-break when recap filename does not match entity string      |
| D        | `store.entities` aliases, `store.wiki_pages`                                               | **Hints only**; cite conflicts in §5 style                      |


---

## 5) Known failure modes to flag per entity

When any of these apply, set `**store_reliability.caveat_kind`** and explain in `**detail`** (and cite design docs in `**design_report_paths`**):

- **Alias pollution / merge:** Design report notes improper-name sets on merged entities (e.g. distinct PCs folded onto a single node). See `**Docs/Design/REPORT-benchmark-shortcomings-and-successes.md`** (alias / Wolf discussion). → `alias_pollution`
- **Referent mixing:** Projected attributes mention **disjoint** proper names or **locations** as if one referent — usually **extraction or co-occurrence** noise; **do not** synthesize a single in-world fact unless prose supports it. → `referent_mixing`
- **Thin evidence:** Few or no corpus hits — set `evidence_sufficiency` to `thin` or `absent`, `integrated_summary` to what little is justified, `citations` to whatever exists.

---

## 6) Output format (per entity)

### JSON (required)

One object per entity validating against `**schemas/v0.1/corpus_entity_profile.schema.json`**. Minimum fields to populate:


| Schema field                      | Role                                                                                            |
| --------------------------------- | ----------------------------------------------------------------------------------------------- |
| `integrated_summary`              | §5 synthesized paragraph (docs-only).                                                           |
| `citations[]`                     | Every cited file; use `layer_tags` and optional `authority`, `quote`, `session`, `campaign_id`. |
| `narrative_layers`                | Optional; mirror §1 exemplar sections when useful.                                              |
| `relationships`, `terminal_beats` | When edges or terminal outcomes matter (e.g. Wolf kill).                                        |
| `store_reliability`               | Always present; `caveat_kind: none` when clean.                                                 |
| `evidence_sufficiency`            | `sufficient`                                                                                    |
| `cohort`                          | Manifest id, connectivity score, store path, git commit, `list_wiki_targets` params.            |


Validate with `src.contracts.schema_validation.validate_instance` in tests or one-off scripts.

### Markdown (optional mirror)

Use a **fixed template** so batches are diffable and skimmable:

```markdown
### {display_name} (`{entity_id}`)

**Definition (corpus-backed):**  
[2–6 sentences: identity, role, fate if known, relationships. Plain language.]

**Primary citations:**
- `[relative/path/to/file.md](relative/path)` — [short quote or section anchor]

**KB caveat (if any):**  
[Or “None noted.”]

---
```

For **major plot entities**, add **one line** tying terminal beats to recap **session** when relevant (e.g. “terminal outcome in C1 Session 12 recap”).

**Aggregation:** JSONL / `profiles[]` JSON array / one file per entity under `Docs/Plans/entity_profiles/` (or agreed path), plus optional `entity_definitions_topN.md` or `entity_definitions/batch_01.md` … with an **index** listing `entity_id` and file anchor.

---

## 7) Workflow (phased)

### Phase 0 — Lock cohort (≤30 min)

- Fix **store path**, **campaign_id**, **min_connectivity**, **date**.
- Run `**list_wiki_targets`** export after `**FactStore.load()`**; save `**entity_audit_manifest.tsv`** (`entity_id`, `connectivity`, `display_name`).
- Confirm **N** (≈138 or actual, e.g. 142); document actual **N**.

### Phase 1 — Discovery tooling (≤1 h per batch, agent-led)

- For each `display_name`, use **grep** over the corpus root (case-sensitive first, then case-insensitive if needed):
`rg -n "Name" corpus/eldyrwild-markdown`
- Record **hit counts** and **best 1–3 files** per entity in the manifest (optional columns: `primary_files`). The **Cursor agent** should run these searches and record results — not hand-wave “the corpus probably mentions X.”

### Phase 2 — Batched synthesis (main effort — agent in auto mode)

- Work in **chunks of 10–20 entities** (by descending connectivity or alphabetically).
- For each entity: **read** top files with tooling; build `**corpus_entity_profile` JSON** (compact §6 or **exemplar depth** §1); **validate**; **flag** KB issues in `store_reliability`.
- **Do not** block on reading every grep hit — cap reading at **~15 minutes** per entity unless high-impact (Wolf-tier plot entities, disputed merges).

### Phase 3 — Spot-check against wiki / projection (optional, ≤2 h)

- For a **5% sample** (7 entities), open `**store.wiki_pages[entity_id]`** and compare **first paragraph** to `integrated_summary`. Mismatches → **file bug** under `Docs/Design/` or **backlog** for projection/merge.

### Phase 4 — Handoff package

- Single **manifest** + **JSON profile bundle** (validated) + optional **markdown mirror** + **“open questions”** list (entities with `evidence_sufficiency: absent` or zero corpus hits).

---

## 8) Success criteria

- **Every entity in the frozen cohort** has a `**corpus_entity_profile` record** OR an explicit stub with `evidence_sufficiency: absent` / `thin` and **whatever** citations exist.
- **At least one citation** per entity **when** the name appears in corpus; otherwise stub explains **absence**.
- `**store_reliability`** present; `**caveat_kind` ≠ `none`** when REPORT-style failure modes apply.
- **Reproducible:** `cohort` lists **store path + git commit + list_wiki_targets parameters**.
- **Schema-valid:** each object passes `corpus_entity_profile.schema.json`.

---

## 9) Out of scope (unless separately tasked)

- Changing **ingestion**, **projection**, or **wiki_compiler** prompts.
- Full **evidence-unit** back-tracing for all facts (expensive); sample only.
- **Bulk** LLM-only definitions with **no** per-claim file open/read/citation pass (this handoff **is** agent + tools + corpus — not blind generation). A separate automated draft **plus** mandatory citation verification could be scoped later.

---

## 10) Key references


| Item                                        | Location                                                                                                                                                                                               |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Corpus entity profile schema + examples** | `schemas/v0.1/corpus_entity_profile.schema.json`; `schemas/v0.1/examples/corpus_entity_profile.example.json` (minimal); `schemas/v0.1/examples/corpus_entity_profile.bonogo_exemplar.json` (depth bar) |
| Schema bundle README                        | `schemas/v0.1/README.md`                                                                                                                                                                               |
| Connectivity score + wiki target selection  | `src/compiler/wiki_compiler.py` — `score_entity_connectivity`, `compile_wiki`, `list_wiki_targets`                                                                                                     |
| Wiki prompt inputs (projected facts only)   | `src/compiler/wiki_compiler.py` — `compile_entity_page`, `_format_facts_for_prompt`                                                                                                                    |
| REPL `compile-wiki` flags                   | `src/cli.py` — `_cmd_compile_wiki`                                                                                                                                                                     |
| Validation helper                           | `src/contracts/schema_validation.py` — `validate_instance`                                                                                                                                             |


---

## 11) Suggested first batch (sanity)

Run the **template + JSON validation** on **3 entities** already deeply documented (**Bonogo**, **The Wolf**, **Mirathorn** or **Dustwalker**) to validate **citation style**, **file paths**, and **schema round-trip**, then scale to the full manifest.

---

**Status:** Ready for execution (Cursor auto mode + tools). Canonical artifact: **CorpusEntityProfile JSON**.  
**Owner:** Cursor agent executes Phases 0–2 against this doc; optional human review for citations and edge cases.