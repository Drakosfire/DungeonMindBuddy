# Entity definitions — sanity batch (3)

**Purpose:** Validate citation style and template from `HANDOFF-entity-definition-audit-top-N.md` before scaling to the full cohort.

**Machine-readable shape:** Each audited entity should round-trip to `schemas/v0.1/corpus_entity_profile.schema.json` (see `schemas/v0.1/examples/corpus_entity_profile.example.json`). That record holds `integrated_summary`, structured `citations[]` with `layer_tags` (dossier / observed_play / gm_prep / ledger / item_or_mechanics / design_report), `store_reliability` for KB caveats, optional `narrative_layers` prose, `relationships`, and `terminal_beats` — aligned with lean identity in `entity.schema.json` plus projected `Fact` state, not a replacement for them.

**Reproducibility (Phase 0):**


| Parameter                                                   | Value                                                                      |
| ----------------------------------------------------------- | -------------------------------------------------------------------------- |
| Git commit                                                  | `3f108761355344b2ca3bf5793c866d3508ef4059`                                 |
| Store path                                                  | `evals/mirathorn_vertical_slice/output/phase_d_store`                      |
| `campaign_id`                                               | `longmont-c1`                                                              |
| `min_connectivity`                                          | `0.3`                                                                      |
| Wiki targets (`list_wiki_targets` after `FactStore.load()`) | **142** (not 138; threshold + projection yields 142 rows on this snapshot) |


**Manifest:** `Docs/Plans/entity_audit_manifest.tsv` (all rows, sorted by connectivity descending).

**Note for automation:** `FactStore` does not call `load()` in `__init_`_; scripts must invoke `store.load()` before `list_wiki_targets`, or the cohort export will show 0 entities.

---

### ent_bonogo (`ent_bonogo`)

**Definition (corpus-backed):**  
Bonogo is a player-character in the Longmont campaigns—a stealth-capable, shadow-leaning adventurer tied to items such as the Slinkstone (teleport in dim light/darkness, shadow resonance) and implicated in the Blood-Edged Invitation plot (“The Killer is Hunting Bonogo”). In play he fights cultists and horrors alongside “Questionable Company” (e.g. warehouse and barn fights in Campaign 2, killing a priest with a dagger through the eye in Session 8). In Campaign 1 he pursues and lands the **killing blow on the Wolf** in council-chamber combat; the recap states the oily corruption leaves the Wolf’s eyes as he dies. Corpus consistently treats Bonogo as a distinct person from the Wolf.

**Primary citations:**

- `[corpus/eldyrwild-markdown/Longmont Campaign/Homebrew Items/Item_ The Slinkstone.md](corpus/eldyrwild-markdown/Longmont%20Campaign/Homebrew%20Items/Item_%20The%20Slinkstone.md)` — attuned item keyed to Bonogo; shadow/fey theming and combat options.
- `[corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 12 - One Persistent Bugbear or Sneaky Fucking Bugbear.md](corpus/eldyrwild-markdown/Longmont%20Campaign/Campaign%201/Session%20Recaps/Session%2012%20-%20One%20Persistent%20Bugbear%20or%20Sneaky%20Fucking%20Bugbear.md)` — “As Bonogo deals the killing blow the oily sheen fades from the Wolf’s eyes…”
- `[corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 8 - Recap.md](corpus/eldyrwild-markdown/Longmont%20Campaign/Campaign%202/Session%20Recaps/Session%208%20-%20Recap.md)` — Bonogo kills the priest (“dagger through the eye”) and helps secure the Dustwalker after the barn fight.

**KB caveat (if any):**  
`Docs/Design/REPORT-benchmark-shortcomings-and-successes.md` (S5) documents that **the Wolf’s alias set incorrectly includes proper names such as Bonogo** due to aggressive fuzzy matching. The corpus keeps Bonogo and the Wolf separate; **do not** treat store-level aliases as authority for identity.

---

### the Wolf (`ent_the_wolf`)

**Definition (corpus-backed):**  
“The Wolf” is a senior Mirathorn guard officer (second-in-command of the guard in GM prep for Session 9, Campaign 1) who works with the cult: distributing corrupted meat, manipulating leadership, and using invisibility and necrotic tactics in the council-chamber confrontation. **Terminal outcome (Campaign 1):** Bonogo kills him after a chase through secret passages; the oily magical influence fades at death, and later recaps refer to removing his head for Speak with Dead at Stormspire Academy.

**Primary citations:**

- `[corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 9 - Battle with the Meat Monsters.md](corpus/eldyrwild-markdown/Longmont%20Campaign/Campaign%201/Session%20Recaps/Session%209%20-%20Battle%20with%20the%20Meat%20Monsters.md)` — “The Wolf who is the second in command of the guard and a cultist is also alerted to the party.”
- `[corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 12 - One Persistent Bugbear or Sneaky Fucking Bugbear.md](corpus/eldyrwild-markdown/Longmont%20Campaign/Campaign%201/Session%20Recaps/Session%2012%20-%20One%20Persistent%20Bugbear%20or%20Sneaky%20Fucking%20Bugbear.md)` — killing blow and regret at betraying Mirathorn (terminal beat).
- `[corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 13 - The Meaty and the Dead.md](corpus/eldyrwild-markdown/Longmont%20Campaign/Campaign%201/Session%20Recaps/Session%2013%20-%20The%20Meaty%20and%20the%20Dead.md)` — Bonogo removes the Wolf’s head for transport to the academy / Speak with Dead setup.

**KB caveat (if any):**  
Same S5 report: the **store may list unrelated proper names on this entity** (e.g. other PCs). Adjudicate conflicts using session recaps and GM notes, not merged aliases alone.

---

### Mirathorn (`ent_mirathorn`)

**Definition (corpus-backed):**  
Mirathorn is the principal city in this arc: walled, politically layered (Council, Guard, Academy), tied to Lake Mirathorn and festivals such as the Festival of Expansion. The party receives a deed to Wolf’s Manor as an in-city base after cult-related losses. Narrative ledgers frame it as a “rebel city” under institutional strain—storms, martial law, and underground tunnels appear in later Campaign 2 state summaries.

**Primary citations:**

- `[corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md](corpus/eldyrwild-markdown/Longmont%20Campaign/Campaign%202/Session%20Recaps/Session%203%20-%20Recap.md)` — “Now the adventures have a home base inside Mirathorn.”
- `[corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Elderwyld_Narrative_Ledger_2.md](corpus/eldyrwild-markdown/Longmont%20Campaign/Campaign%202/Elderwyld_Narrative_Ledger_2.md)` — “Primary Location: Mirathorn, Eldyrwyld”; “Mirathorn stands as a rebel city…”
- `[corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Campaign 2 Notes.md](corpus/eldyrwild-markdown/Longmont%20Campaign/Campaign%202/Campaign%202%20Notes.md)` — civic/military context (Council, Guard, storms) in GM-facing notes.

**KB caveat (if any):**  
None noted for location-level merge in the same way as character alias pollution; projected facts may still omit narrative color present only in ledgers/recaps—prefer primary prose for tone and detail.

---

## Open questions (sanity scope)

- **Cohort size:** Adopt **N = 142** for this store snapshot or trim to top 138 by connectivity in `entity_audit_manifest.tsv` if a fixed 138-row run is required.

---

**Status:** Sanity batch complete; ready to continue with `batch_01`… in connectivity or alphabetical order per handoff §7.