# REPORT — guided Stage 4 UX/WOW operator pass v1

**Status:** RECORDED — human pass complete; Stage 4 WOW not satisfied  
**Handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`](../Plans/HANDOFF-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md)  
**Operator:** product owner / GM  
**Product:** merged `main` checkout `/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy`  
**Witnessed:** 2026-09-17  
**Doors:** Ingest / Graph Review at `http://127.0.0.1:5173/` · API `127.0.0.1:8000`  
**World:** durable authority `127.0.0.1:54330` database `dungeonmind_cutover_live` (copied from replay `dmb_current_corpus_replay_v2` during this session so main could read campaign memory)

This is an observation report. It does not dispatch an implementation slice.

```text
STAGE 4 / RECAP WOW                              HOLD — human pass recorded, not satisfying
OPERATOR DOGFOOD ON MERGED #732                  RECORDED
SEMANTIC COVERAGE                                NOT MEASURED (gauntlet not run)
AGENT ANSWERABILITY                              NOT MEASURED
```

---

## What this session answered

> Now that campaign memory actually loads through the product, what is the next thing that stops DungeonBuddy from feeling like a tool I genuinely want to use?

**Answer:** the first World object you look at. Pills pull the eye; glance and peek do not repay that attention. Wrong kind, empty hover, “World Object” chrome, nested disclosures, and relationship lines like `Misty Step · possesses` make the memory feel like a graph dump instead of campaign information. Cross-campaign cultist/Dustwalker facts later *did* impress and create pull. The interface is what spoiled the first minutes.

A separate session-aborting bug rewrote Focus session **Session 27** into **longmont-c2:27** and then showed `Canonical normalized recap is unavailable for longmont-c2:27 in longmont-c2.` That is not the WOW question, but it did interrupt reading.

---

## What worked

Protect these.

- **Campaign + Focus session → published recap** is the right ordinary path. After World was addressable, Session 27 was actually present and readable.
- **Pills draw the eye**, and the operator *wanted* to look at them. Chip attention works.
- **Glance on the hole:** “Location” was useful. “Swarms located in the hole this session.” was “actually pretty useful.”
- **Peek does not navigate away.** Close the node viewer; recap is fine. That grammar held on C2 and C1.
- **Session 26 felt like the same product**, just a different recap.
- **C1 Guard as a faction** was “kinda cool.” Commander Thalia commanding was correct (then duplicated).
- **C1 Cultists / Dustwalker Leads** was mostly true, and Dustwalker being a **C2** node made the campaigns feel connected. Several cultist nodes were “pretty interesting.” Operator: **this isn’t really a useful presentation for a Faction, but it makes me want more and I am impressed.**
- **Author Node** on ordinary browse told the truth: `Authoring requires an explicit source/run context.` It did not fake write authority.

---

## Friction, in experienced order

Operator language is quoted. Classes assigned after the fact.

### 1. Arrival: World chip, no recap

**O1** `World · Needs attention · DungeonMind authority is unavailable. (authority_unavailable)`  
Campaign Longmont C2 / Session 27 were selected. Primary work was red copy + Retry. No recap.  
**Class:** AUTH + UX (infrastructure as the first screen) + operational miss (main `.env` points at `dungeonmind_cutover_live`, which did not exist on 54330 until the replay World was copied there).  
**Impact:** blocked the pass until the operator directed the copy.

### 2. Recap appears; PCs have no pills; then the recap vanishes

**O2** First notice once Session 27 loaded: **Player character nodes don't have pills.**  
**Class:** SEM

**O3** After a short time **the page canvas refreshes, or maybe the surface**, then `Canonical normalized recap is unavailable for longmont-c2:27 in longmont-c2.` Operator tied this to **the mystery refresh bug in the bug tracker**. Recap *had* been present.  
**Class:** BUG + NAV

**O4** Retry. Focus session dropdown contains both **Session 27** and **longmont-c2:27**. Product was on `longmont-c2:27`. Switching to **Session 27** worked. Operator: **whatever and whyever we switched to longmont-c2:27 is a bug.** Extra identity later disappeared; list order **used to be highest to lowest** and had **reversed**.  
**Class:** BUG + NAV

### 3. First pill: unimpressed and confused

**O5** Pills draw the eye; operator wants to look at them.  
**Class:** GOOD

**O6** First pill **hybrid monsters**, labeled **ITEM**. Hover has **no information**. Click: World object, C2, collapsed Details/Advanced, Continue in Build. **It's not an item.** Details and Advanced **don't tell me anything useful.** **Unimpressed and confused.**  
**Class:** SEM (wrong kind, empty object) + UX (empty glance, useless peek)

**O7** **If I click Continue in Build it'll mess things up and navigate to Build.**  
**Class:** NAV (not clicked this session; stated as known trap)

**O8** **The colors of the pills don't seem to mean anything either.**  
**Class:** UX / IDEA

### 4. A better glance, then a bloated peek

**O9–O11** Hover **the hole**: Location useful; **Why it matters here** disliked (“I can decide that myself”); **Swarms located in the hole this session.** useful except **this session** is obvious.  
**Class:** GOOD + UX

**O12–O14** Opened the hole to learn more. **The amount of text we capture is HUGE.** **So much space is taken up by the component nesting.** **Why does it say "World Object?"** That doesn't tell anything. Only detail: **Swarms located in**. Want **Swarms located in the hole** as synthesis/summary, not a huge prose block.  
**Class:** UX

### 5. Follow a relationship; memory is patchy

**O15** **Swarms located in** → **ogonob attacks**. Sorta interesting.  
**Class:** GOOD

**O16** Other recap instances of **the swarm** are not pills.  
**Class:** SEM

**O17** **Swarms is listed as an item, and it's clearly a threat.**  
**Class:** SEM (same wrong-kind class as hybrid monsters)

**O18** Close node viewer: fine.  
**Class:** GOOD

**O19–O22** Object body is **too much information to help me consider things.** **Ogonob should have many more entries.** Misty Step is useful; **Misty Step · possesses** is not clear. Ogonob possessing Misty Step *is* useful. **the wall crack and tunnel below it · located in** does not communicate. End of prose: **· session_recap** is odd.  
**Class:** UX (relationship English / evidence leak) + SEM (thin Ogonob)

### 6. Session and campaign movement

**O23–O25** Session list order reversed vs earlier highest-to-lowest. Extra `longmont-c2:27` gone. Session 26 same product.  
**Class:** UX/BUG (order) + GOOD (same product)

**O26** Switching to Campaign 1 **tries to go to session 26, which doesn't exist.**  
**Class:** NAV + BUG

**O27** C1S15 **Guard** is a faction, kinda cool. **Commander Thalia Ashenvale commands** and **Thalia Commands** — clear duplicate. Wants the rest of the connected details; knows they exist.  
**Class:** GOOD + SEM (duplicate + thin)

**O28** **Cultists** / **Dustwalker Leads** mostly true, C2 node, connected, interesting, not a useful Faction presentation, **want more**, **impressed**.  
**Class:** GOOD + UX + SEM

### 7. Refresh and chrome

**O29** Reload feels like a **full graph reload**, or maybe markdown rendering. **Isn't long but I don't like it.**  
**Class:** PERF

**O30** Refresh **closed the tool bar with the node I was reviewing.** Campaign/session survived; the object did not.  
**Class:** NAV

**O31** **Opening Tools just shows the Diagnostic tool which isn't useful.**  
**Class:** UX

### 8. Free exploration

**O32** Author Node: `Authoring requires an explicit source/run context.` Hoped to dogfood authoring; product stopped truthfully.  
**Class:** AUTH + GOOD (truth) + UX (dead end)

**O33** **Tools and Author Node are underpopulated.** Search and merge-node logic exists somewhere and is not here.  
**Class:** UX

**O34** Idea: **highlight text, tell the agent it is a node, and have it author the rest.**  
**Class:** IDEA — not this slice; 7A1 remains queued behind UI-language work unless the steward explicitly reorders.

---

## UX vs memory quality

**The interface made good information hard to use**

- “World Object”, Details/Advanced nesting, huge captured prose.
- “Why it matters here”; redundant “this session”.
- Relationship framing `X · possesses` / `X · located in` / `· session_recap` instead of a sentence with the selected subject.
- Pill colors with no meaning.
- Continue in Build as a navigation trap.
- Tools = Diagnostics only.
- Refresh drops the open object; reload hitch.

**The interface worked but the graph did not know enough / knew the wrong thing**

- Player characters not pilled.
- Other “the swarm” mentions not pilled.
- Hybrid monsters and Swarms labeled **item**; operator: not an item / clearly a threat.
- Empty hover and empty useful details on hybrid monsters.
- Ogonob too thin (“should have many more entries”).
- Thalia command duplicated.
- Guard/cultist connected details the operator knows exist.

Both are real. The **first minutes** failed on presentation of the first object. Later C1 cultists showed that memory *can* pull. Semantic gauntlet is justified as a follow-on diagnostic, not the next dispatch while the first click still says ITEM and the hover is empty.

---

## The operator's actual workflow (free exploration)

After the guided path, the operator did not keep clicking recap tokens. They tried **Author Node** hoping to dogfood authoring, found a truthful dead end, noticed Tools is Diagnostics-only, remembered search/merge exists elsewhere, and stated the product wish: highlight recap text, tell the agent it is a node, have it author the rest.

That is the intended GM workflow leaking through: read → notice → inspect → then *do something* to the memory. Browse/write separation is correct; the empty authoring/tools side is what they reached for next.

---

## Suggested next steward decision

Choose **B**, not A, C, or D.

```text
B. One bounded UX defect dominates
   → design one UI-language successor: chip → glance → peek
     as campaign information, not graph chrome.
```

**Why not A:** UX is not good enough. First object left the operator unimpressed and confused. They were later impressed *despite* presentation.

**Why not C as the whole outcome:** after the World DSN was pointed at real memory, the ordinary path worked (campaign, session, recap, glance, peek, close, other sessions, C1). The `longmont-c2:27` rewrite is a real structural abort and may be a **serialized predecessor repair** inside or immediately before B, not a return to campaign-memory substrate work.

**Why not D:** Stage 4 WOW is not satisfied. “Makes me want more” on Cultists is the closest WOW signal; it is not the first-object experience.

**Do not dispatch in this report:** 7A1, semantic gauntlet, Agent tuning, graph-ingestion redesign, Play paint, Combat, catalog cleanup.

**Operator idea to park, not dispatch:** highlight text → tell agent it is a node → author the rest.

---

## Observation ledger (compact)

| ID | Operator words / fact | Class |
|---|---|---|
| O1 | World Needs attention / authority_unavailable; Retry; no recap | AUTH UX |
| O2 | Player character nodes don't have pills | SEM |
| O3 | Canvas/surface refresh; recap unavailable for longmont-c2:27 | BUG NAV |
| O4 | Dropdown has Session 27 and longmont-c2:27; switch worked; identity rewrite is a bug | BUG NAV |
| O5 | Pills draw my eye; I want to look at them | GOOD |
| O6 | Hybrid monsters ITEM; empty hover; not an item; Details/Advanced useless | SEM UX |
| O7 | Continue in Build messes things up / navigates to Build | NAV |
| O8 | Pill colors don't seem to mean anything | UX |
| O9 | Hole = Location; swarms line useful | GOOD |
| O10 | Why it matters here — I can decide that myself | UX |
| O11 | “this session” is not useful | UX |
| O12 | Huge captured text; component nesting | UX |
| O13 | Why does it say World Object? | UX |
| O14 | Want “Swarms located in the hole” as summary, not a prose dump | UX |
| O15 | ogonob attacks sorta interesting | GOOD |
| O16 | Other “the swarm” mentions aren't pills | SEM |
| O17 | Swarms listed as item; clearly a threat | SEM |
| O18 | Close node viewer; recap fine | GOOD |
| O19 | Too much information to help me consider things | UX |
| O20 | Ogonob too thin; Misty Step · possesses unclear | SEM UX |
| O21 | wall crack… · located in — not sure what that communicates | UX |
| O22 | · session_recap at end of prose | UX |
| O23 | Session order reversed from highest-to-lowest | UX BUG |
| O24 | Extra session 27 gone | — |
| O25 | Session 26 same product | GOOD |
| O26 | Campaign 1 tries session 26, which doesn't exist | NAV BUG |
| O27 | Guard faction cool; Thalia duplicate; missing connected details | GOOD SEM |
| O28 | Cultists / Dustwalker; C2 connected; not useful Faction presentation; want more; impressed | GOOD UX SEM |
| O29 | Reload feels like full graph reload; don't like it | PERF |
| O30 | Refresh closed the node being reviewed | NAV |
| O31 | Tools = Diagnostic only; not useful | UX |
| O32 | Author Node: requires explicit source/run context | AUTH GOOD UX |
| O33 | Tools and Author Node underpopulated | UX |
| O34 | Highlight text, tell agent it is a node, author the rest | IDEA |
