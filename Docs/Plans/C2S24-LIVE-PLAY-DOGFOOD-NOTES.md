# C2S24 live-play dogfood notes

**Purpose:** Capture how Cursor + DungeonBuddy behave during Session 24 live play and prep cleanup, especially where recap ingestion still requires manual stitching instead of a mechanized flow.

**Scope:** Queries asked, tools run, files opened, friction observed, and follow-up product ideas. This is **not canon** and not a prep source by itself.

**Last updated:** 2026-06-20 (recap-ingest flow friction)

---

## How to Log

Add a row when an action changes planning state, reveals friction, or suggests a DungeonBuddy feature.

| When | Surface | Query / action | Inputs / files | Result | Friction / opportunity | Follow-up |
|------|---------|----------------|----------------|--------|------------------------|-----------|
| 2026-06-20 | Cursor chat + recap ingest pipeline | Continue S23 recap ingestion from raw notes through breadcrumbing | `_ingest_staging/session_23_raw_notes.orig.txt`, `_ingest_staging/session_23_raw_notes.md`, `_normalized/Session 23 - Mireward Gate Battle.md`, `_breadcrumbed/Session 23 - Mireward Gate Battle.frontmatter_seed.md` | Raw notes had a home and a preprocessed markdown staging file; normalized recap existed; breadcrumbing required a manually authored frontmatter seed before the prompted ingester could run | Ingestion is not yet a single flow: the operator/agent must know staging, canonical recap, normalization, hand seed authoring, prompted breadcrumb command, and session-memory materialization as separate steps | Mechanize recap ingest as an explicit flow with status, next action, seed generation, command preview, and durable artifact checks |
| 2026-06-20 | Plan surface ingest UI | Align Plan ingest wizard with deterministic v1 boundary | `IngestionModule`, `IngestionStatusPanel`, `recap_ingest_pipeline` status envelope | UI now treats `breadcrumb_required` as an expected stop after canonical + normalized recap, not a failure or hung job; materialization remains disabled until disk status reports `breadcrumb_found` | The boundary is understandable only when the UI says which artifacts exist and which are still missing; a manual "I added breadcrumb" bypass would blur authority | Keep `breadcrumb_required` as a first-class actionable Plan state; future seed/breadcrumb tooling should attach behind this state, not bypass it |
| 2026-06-20 | Prompted breadcrumb ingester | Run existing breadcrumb generation after hand-authoring the S23 seed | `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`; `_breadcrumbed/Session 23 - Mireward Gate Battle.{frontmatter_seed,breadcrumbed}.md` | Prompted ingest succeeded on first attempt: 147 inline tags; 80 normalized units; 77 records with routes; cost `$0.10968825` | The harness also ran stale default query gold and reported `all_ok: false`, even though the ingest-specific block succeeded; this makes the operator interpret unrelated benchmark noise | Add a true ingest-only command or flag that stops after breadcrumb + normalization + record summary |
| 2026-06-20 | Session-memory materialization | Build committed S23 session-memory JSONL/meta and check drift | `_breadcrumbed/Session 23 - Mireward Gate Battle.breadcrumbed.md`; `_session_memory/Session 23 - Mireward Gate Battle.records_meta.{json,jsonl}` | Materialization wrote 82 records and the deterministic check passed (`routes=77`); pipeline status became `ready_for_planning_activation` | Pipeline status still warned `slug_mismatch_used_disk_breadcrumb` because its generic canonical recap path expected `Session 23 - Recap.md` while the real stack uses `Session 23 - Mireward Gate Battle` | Normalize slug/title ownership so status, canonical recap, normalized recap, breadcrumb, and session memory resolve the same basename |
| 2026-06-20 | Live-play command board | Refresh live play from newly ingested S23 context | `live/session_23/current_state.json`, `live/session_23/live_packet.json`, `mireward-prep/live-play.html`, `content/tiptap/north-gate-session-runbook.md` | Live state now points at S23 session memory and active north-gate combat; runbook now covers first-wave cleanup, respite NPCs, and second-wave breach pressure | Updating live play required manual edits across state JSON, static page chrome, runbook prose, and corpus naming notes | Mechanize "activate latest recap for live play" as a command that updates packet/state/runbook references and reports stale labels |
| 2026-06-20 | Live combat tracker | Track damage/healing and scan grouped combat rows during active play | Combat roster / HP columns in live-control or command board combat surface | Operator noticed two table-use frictions: grouped rows lose column-name context, and HP changes require more typing/thinking than they should | At-table combat UI needs repeated/sticky group headers and click-to-modify HP affordances | Add group-local column headers; make HP cells open a modifier popover supporting `+/-` arithmetic and manual override |
| 2026-06-20 | Live combat tracker | Use status notes during active turns | Combat roster status/notes affordance | Status notes are useful and table-visible, but they need duration tracking: add a note, choose how many turns/rounds it lasts, and define whether it ticks at top or bottom of the affected character's turn or round | Conditions/effects are currently memory burden instead of tracker-owned state | Add status note duration fields with tick boundary (`top_of_turn`, `bottom_of_turn`, `top_of_round`, `bottom_of_round`) and auto-expiry / warning as the boundary arrives |
| 2026-06-20 | Live combat tracker + statblock markdown | Add spawned minions from abilities | Tripod Null-Calf throws meatwings, meat abominations, and unnamed burrowing things; Ephanna summons Ogonob | Some abilities imply creating new combatants, but the tracker does not expose a structured "spawn this minion" action from the markdown/statblock or PC ability itself | GM has to manually create or improvise spawned creatures, stats, ownership, and initiative during active play | Let statblock/ability markdown define spawnable minion templates; render ability actions that add a minion to the tracker with stats, generated initiative, controlling side/owner, naming sequence, and source/provenance |
| 2026-06-20 | Live combat tracker | Read turn order by initiative bands | Turn order / initiative queue | Operator groups initiative mentally as `21+`, `16-20`, `11-15`, `6-10`, `1-5`; the tracker should visually break the queue into those groups | Flat turn order makes it harder to scan who is in the same initiative phase and where the next band starts | Add configurable initiative grouping bands with strong visual separators and repeated headers per group |
| 2026-06-20 | Live combat tracker | Commit numeric edits with Enter | HP / numeric cell editing | When updating HP or another number, pressing Enter should commit the value, move focus out of the field, and make it visually clear the cell is no longer in edit mode | If focus remains in the input, the GM has to spend attention verifying whether the value is committed or still editable | Make Enter commit-and-blur numeric edits; add a clear saved/non-edit visual state after commit |
| 2026-06-20 | Live combat tracker + rules corpus | Hover rules terms from ingested 5e rules graph | Status/condition/rules labels such as `sleeping` and `poisoned` | Rules terms should be hoverable in combat, but the hover content should be populated dynamically from the ingested D&D 5e rules corpus instead of preloaded/hardcoded tooltip text | The GM needs rules context at the table without bloating the combat payload or manually opening rules references; e.g. hovering `poisoned` should show disadvantage on attack rolls and ability checks | Connect condition/rules labels to the ingested rules graph; resolve terms on hover/focus and render a compact sourced rules card with cache/loading/error states |

---

## Friction and Product Ideas

| Observation | Why it matters | Candidate DungeonBuddy improvement | Priority |
|-------------|----------------|------------------------------------|----------|
| Recap ingestion currently requires hand-discovering the next step and the right command. | The operator is in live-play mode, where remembering internal pipeline shape is cognitive overhead. | Add a recap-ingest command surface that shows current stage, missing artifact, exact next command, and expected output paths. | ready |
| Breadcrumbing depends on a hand-authored `frontmatter_seed.md`. | The prompted tagger exists, but it is blocked unless the route allowlist has already been assembled. | Generate a reviewable seed draft from the normalized recap plus corpus route lookup, then require human approval before breadcrumbing. | ready |
| The pipeline can report `breadcrumb_required`, but does not yet bridge into seed generation or prompted breadcrumbing. | A good status check still leaves the operator to connect tools manually. | Treat `breadcrumb_required` as an actionable state with one or more mechanized remediations. | ready |
| The prompted breadcrumb harness mixes artifact generation with benchmark scoring by default. | A successful ingest can still end with `all_ok: false` because unrelated gold scenarios were evaluated. | Split the surfaces: `ingest breadcrumb` should report artifact validity, route counts, and cost; benchmark scoring should be opt-in. | ready |
| Activating ingested context for live play is manual. | The GM wants the command board to inherit new session memory, not require hand-patching JSON and markdown during live prep. | Add a live-play activation step: choose session memory artifact, update packet/current-state pointers, refresh board labels, and add a generated runbook delta for review. | ready |
| Grouped combat rows do not repeat the column names. | During live play, the GM has to look up to the top header and map columns back down, which adds friction every time the roster is long or visually grouped. | Render column headers on each grouping, or use sticky subheaders that travel with the group. | ready |
| HP tracking needs arithmetic entry, not only raw editing. | Damage/healing happens constantly; the GM wants to click HP, enter `-12` or `+7`, and let the tracker calculate, while still allowing direct manual correction. | Add an HP modifier popover on HP cells: current/max display, numeric delta field, quick damage/heal actions, apply/undo, and manual set override. | ready |
| Status notes are useful but need duration and tick timing. | Effects like charm, bless, sleep, and spell riders need to expire at precise combat boundaries; otherwise the GM has to remember which top/bottom of turn or round matters. | Add status notes with duration units, owning entity, tick boundary, expiry boundary, and automatic decrement/expired-state display in the turn tracker. | ready |
| Abilities can create sub-minions or summons, but the tracker cannot spawn them from the source ability. | Tripods and other horrors create meatwings, abomination bits, or burrowers; PCs can also create unique allies like Ephanna's summoned **Ogonob**. These should enter initiative with consistent stats, team, and owner instead of being hand-entered mid-combat. | Add structured `spawn` metadata to statblock/ability markdown or companion sidecars, then render "Add minion/summon" actions in the combat tracker with stat template, generated initiative, count, name suffix, team, owner/controller, and source ability. | ready |
| Turn order needs configurable initiative-band grouping. | The GM scans combat by initiative bands, not only strict sorted rows; common bands for this table are `21+`, `16-20`, `11-15`, `6-10`, and `1-5`. | Add a combat tracker setting/config for initiative bands, with clear group headers, visual breaks, and optional repeated column labels inside each band. | ready |
| Numeric edit mode needs an obvious commit/exit gesture. | During combat, lingering focus in HP or numeric fields makes it ambiguous whether the tracker accepted the value or is still waiting for input. | Pressing Enter should commit, blur, and transition the cell back to read mode with an obvious non-edit visual state; Escape should cancel and blur. | ready |
| Combat rules terms should hydrate from the ingested rules graph. | Terms like `sleeping`, `poisoned`, conditions, spell effects, and action names should provide rules help without hardcoding every tooltip into the combat UI. `Poisoned` specifically should surface disadvantage on attack rolls and ability checks. | Add a rules-graph lookup API and hover/focus card component: term normalization, dynamic fetch, compact sourced summary, source citation, local cache, and graceful "not found" state. | ready |

---

## Open Dogfood Follow-ups

| Item | Owner | Status |
|------|-------|--------|
| Turn S23 manual seed authoring into a reproducible tool or pipeline stage | Engineering backlog | Suggested |
| Add a one-command recap ingest status/continue loop for raw -> canonical -> normalized -> seed -> breadcrumbed -> session memory | Engineering backlog | Suggested |
| Combat tracker: repeat/stick column headers per group | Engineering backlog | Suggested |
| Combat tracker: HP modifier popover with +/- math and manual edit | Engineering backlog | Suggested |
| Combat tracker: status-note durations with top/bottom turn or round expiry | Engineering backlog | Suggested |
| Combat tracker: statblock ability spawns sub-minion templates into initiative | Engineering backlog | Suggested |
| Combat tracker: configurable initiative-band grouping (`21+`, `16-20`, `11-15`, `6-10`, `1-5`) | Engineering backlog | Suggested |
| Combat tracker: Enter commits numeric edits and visibly exits edit mode | Engineering backlog | Suggested |
| Combat tracker: rules-term hover cards backed by ingested 5e rules graph | Engineering backlog | Suggested |

---

## Post-Session Design Clarifications

| Topic | Clarified decision |
|-------|--------------------|
| Status ownership | Status durations attach to the affected entity's status list. |
| Status expiry v1 | Start with end-of-turn expiry. Later, rules hydration can infer richer timing from the rules corpus. |
| Spawned minion initiative | Spawned creatures default to the same initiative as the summoner/source, but placed immediately after that source in turn order. |
| Player summons | **Ogonob** specifically should be represented as a summon, with Ephanna as owner/controller. |
| Rules hover scope | Rules lookup should eventually support any rules term, not only conditions. This creates an integration requirement between the command board/combat tracker and the rules ingestion project. |
| HP edit history | Start with final HP only. Long term, keep a time series of HP changes and causes. |
| Initiative bands | Default grouping should always be `21+`, `16-20`, `11-15`, `6-10`, `1-5`. |
| Pain ranking | Biggest pain: rules lookup. Second biggest: minion/summon spawning. |
