# EXPLORATION — Tick ledger and temporal adjudication

**Captured:** 2026-08-22  
**Status:** EXPLORATION — not reviewed contract; does not change PR #627 / BF1–BF5 authority  
**Main at capture:** `0975ebcfb714b1a664dfb57362d7cd13351aa077` (PR #627 merge)  
**Origin:** refinement of the 2026-08-22 exploration, “The tick: time as the organizing primitive of Play”  
**Related authority:** `DESIGN-play-current-moment-cockpit.md`, `ARCHITECTURE-playable-material-and-runtime.md`, `CONTRACT-temporal-envelope-v1.md`, `CONTRACT-temporal-shadow-overlay-v1.md`, `ROADMAP-playable-hoist-dungeonmind-kernel.md`

---

## 1. Design judgment

The original insight survives, but the useful form is narrower than “everything is a clock” or “the Beat is the tick.”

The system has at least three different temporal layers that must remain distinct:

1. **Transaction / revision order** — the order in which one durable authority changes.
2. **Narrative position** — where the GM currently is in the playable material.
3. **Fiction time** — when an occurrence happened or a state was true inside the campaign world.

The word **tick** is useful only if it names the first layer precisely: a domain-local successful durable transition from one authoritative revision to the next.

That produces the following working rule:

> **A tick is a local transaction/revision fact, not a universal unit of story time. Narrative position and fictional time may be projected or annotated against ticks, but they do not inherit tick semantics automatically.**

There is therefore **no global DungeonMind tick** and no integer ordering between unrelated domain clocks.

---

## 2. Refined temporal model

### 2.1 Transaction / revision time — the operational tick

A durable authority may expose a monotonically ordered revision or transaction identity.

Examples already present:

- workspace document revision;
- Play Run `run_revision`;
- graph/world revision and contribution identities;
- Combat-owned round/turn state once durable Combat is considered.

For Play Runtime, `run_revision` is already the strongest candidate for a tick number. A successful non-noop progress mutation advances it exactly once; replay/no-op does not. Rebase also advances `run_revision`, which matters: a Run tick is an **aggregate transaction revision**, not merely a table-action counter.

A useful notation is:

```text
Run R, revision 41 → Run R, revision 42
```

That transition is one Runtime tick even if several progress fields change atomically.

### 2.2 Narrative position — Beat is a frame, not the tick

PR #627 makes Beat the durable primary **current-moment frame**. That is not the same thing as transaction granularity.

The contract explicitly allows all of these while remaining in one Beat:

- select or clear a Scene;
- select/change/clear a Decision Option;
- resolve or unresolve the current Beat;
- write a note;
- keep a resolved Beat current while fallout finishes.

Therefore:

> **Beat is the reviewed narrative unit of attention. `run_revision` is the Runtime transaction unit. One Beat may contain many Runtime ticks, and a Runtime tick need not advance the Beat.**

This distinction is desirable. It prevents implementation pressure to make “story advancement” happen automatically whenever durable state changes.

### 2.3 Fiction time — TL00 remains semantic time

`TemporalEnvelopeV1` already distinguishes:

- source time;
- occurrence time;
- valid time.

It also explicitly places **transaction / revision time outside the envelope**.

That boundary should survive.

A Run tick and `recorded_at` timestamp tell us **when DungeonMindBuddy recorded a Runtime transition**. They do not, by themselves, tell us:

- when the described event occurred in the fiction;
- how long a fictional state was valid;
- whether the table event and the in-fiction event were simultaneous.

In particular, this tempting mapping is wrong:

```text
value selected at Run tick 42
→ therefore fiction valid_time begins at tick 42
```

The interval during which a Runtime field remained unchanged is a **transaction-state interval**, not TL00 fictional `valid_time`.

Likewise, `recorded_at` is transaction metadata. It may later participate in provenance, but it is not automatically TL00 `source_time`, and never automatically `occurrence_time`.

### 2.4 Cross-domain temporal reference — the possible shared primitive

A future shared primitive may need to say:

```text
this fact/action/reference was observed at
Play Run R revision 42
```

or:

```text
this Combat transition occurred while Play Run R was at revision 57
```

That is a **reference between domain-local transaction clocks**. It is not a shared counter.

A conceptual shape might eventually resemble:

```text
TransactionPointRef
  authority_kind
  authority_id
  revision
```

This exploration does **not** freeze that wire shape or its owner.

---

## 3. The clocks / mutation authorities that exist today

Calling every mutable thing a “clock” is too broad. The useful distinction is whether historical ordering is part of the authority.

| Authority | Ordered mutation identity | Current judgment |
|---|---|---|
| Workspace document | document revision | Real transaction clock. Past bytes are not currently archived, so revision identity outlives retrievability. |
| Play Run | `run_revision` | Real transaction clock. CAS + persisted revision make ordering authoritative within one Run. |
| Active-Run pointer | last explicit pointer write | Mutable selection authority, but not currently a revisioned history. Do not promote it into a temporal primitive merely because writes are ordered. |
| Combat | round / turn plus Combat mutation state | Domain-local temporal structure. Round/turn semantics remain Combat-owned; no shared counter with Play. |
| World / canon | graph/contribution/revision governance | Has revision/provenance mechanics, but should not be collapsed into a single “canon tick” without a concrete consumer need. |

The design heuristic remains useful:

> For every durable piece of state, ask which authority/revision it changes with. If it appears to require its own independent clock, demand evidence that it cannot be derived from an existing authority.

That supports PR #627’s decision that relevance has **no independent clock**: it derives from sealed edges + durable selections and therefore cannot drift.

---

## 4. The Runtime history / “tick ledger” idea

The product idea remains attractive:

> Keep the minimal ordered story of what changed in a Run.

But the original “one JSONL append inside the same lock is nearly free and cannot diverge” claim is not correct enough for this repository’s integrity posture.

### 4.1 `run_revision` is a good transaction identity

A ledger/history entry should bind to the revision transition, not invent another counter:

```json
{
  "from_run_revision": 41,
  "to_run_revision": 42,
  "recorded_at": "2026-08-21T22:09:02Z"
}
```

No-op and replay requests must not create a new entry because they do not create a new authoritative revision.

Creation needs an explicit baseline (for example revision 1 / Run-created), and **every operation that advances `run_revision` must be represented** if the history ever claims fold-completeness. Today that includes progress replacement and rebase, not only table actions.

### 4.2 One tick may contain several semantic changes

Current Runtime mutation is full-progress CAS replacement, not a command-specific event API. One successful request may truthfully do more than one thing — for example changing Beat and clearing Scene in the same transaction.

Therefore §14 of the cockpit contract is a useful vocabulary source but is **not already a ledger schema**.

A better conceptual entry is one transaction with typed changes:

```json
{
  "schema_version": "dmb_play_run_tick_v1",
  "run_id": "<uuid>",
  "from_run_revision": 41,
  "to_run_revision": 42,
  "recorded_at": "2026-08-21T22:09:02Z",
  "changes": [
    {
      "kind": "current_beat",
      "from": "beat:breach",
      "to": "beat:aftermath"
    },
    {
      "kind": "current_scene",
      "from": "scene:tunnel",
      "to": null
    }
  ]
}
```

The exact schema is not frozen here. The important rule is:

> **One durable transaction tick may contain multiple semantic changes. Do not split one CAS transition into fake sequential story events.**

### 4.3 A lock does not make two files atomic

The current Run write uses atomic temp-file replacement for one JSON document. A separate JSONL append is a separate durable write.

Holding the same registry lock guarantees **ordering**, but it does not guarantee atomicity across:

```text
Run JSON write
+
ledger JSONL append
```

A process/filesystem failure can occur after either one. That would produce exactly the divergence the ledger is supposed to prevent.

So a trustworthy history needs one of these integrity postures:

#### Option A — history inside the Run record

```text
one atomic Run JSON replacement
= current progress + bounded/unbounded history
```

Pros:
- simplest atomicity story;
- uses the existing CAS/write boundary;
- human-rate Run histories are likely small enough initially.

Cons:
- Run JSON grows and is rewritten each mutation;
- history cannot independently recover a completely lost Run file;
- a future large-history/read model may want separation.

#### Option B — separate write-ahead/event sidecar with recovery protocol

The ledger is written under a small transaction/recovery contract so an interrupted two-file transition is detectable and resumable.

Pros:
- independent durable history;
- can become a true recovery source;
- append-oriented storage remains possible.

Cons:
- no longer “nearly free”;
- introduces a multi-file integrity/recovery seam similar in seriousness to P2C’s rebase intent;
- must prove response-loss/replay/crash behavior.

#### Option C — ledger becomes authority

Full event sourcing: current Run progress becomes a materialized view of the event stream.

This is not justified today. It makes folding/version evolution part of the hot integrity boundary and reverses the current simple fail-closed Run-record authority.

### 4.4 Current recommendation

If dogfood proves a user-facing need for “what changed” / recap before independent recovery is required, **Option A is the smallest credible first implementation**.

If independent recovery/audit is the actual requirement, design Option B explicitly rather than pretending a locked two-file append is atomic.

Do not adopt Option C without evidence that temporal queries/replay are first-class product requirements.

---

## 5. What a history would and would not mean

A Run history can be valuable without becoming a world-event stream.

It may support:

- “what changed since I last looked?”;
- session recap assistance;
- debugging a surprising current state;
- “when did this selection/note/current position last change?”;
- provenance for a later explicit canon/adoption action;
- possibly recovery, **only** if its storage integrity contract actually supports recovery.

It does not automatically mean:

- the selected authored consequence happened in the fiction;
- a note is canon;
- a Beat resolution advanced fictional time;
- a Combat round shares the same counter;
- World truth should mutate;
- every local UI action deserves a durable history row.

This reinforces PR #627 §5.4: authored consequences remain informational until an owning authority receives an explicit action.

---

## 6. Relationship to TL00 / TL01

The original exploration correctly noticed a family resemblance, but the clean seam is different from a direct field mapping.

### What should be reused

TL00 already gives the project two valuable disciplines:

1. **Interpretation without ownership.** The temporal module interprets temporal meaning while leaving extraction, publication, current-state reduction, ordering, and UI with their owners.
2. **Do not infer semantic time from provenance.** Source/recording context is not automatically occurrence or valid time.

Those principles should govern any future Runtime-to-World temporal bridge.

### What should not be conflated

`run_revision` and `recorded_at` are transaction/revision facts. TL00 explicitly says transaction/revision time lives outside `TemporalEnvelopeV1`.

Therefore a future design should prefer:

```text
transaction reference / provenance
    + optional TemporalEnvelopeV1 interpretation
```

not:

```text
Run tick == occurrence_time == valid_time
```

TL01 is also instructive: a table event could eventually receive an evidence-bound fictional-time annotation without rewriting the Runtime event itself. That is closer to the existing “shadow interpretation” posture than putting speculative `occurred` fields into every tick at write time.

Initial recommendation: **do not add fictional occurrence/valid time to the first Run-history entry schema.** Add it only through explicit operator input or a separately governed annotation/adoption seam when a real workflow requires it.

---

## 7. Should DungeonMind be the tick adjudicator?

The original phrase is directionally interesting but too strong as written.

The hoist roadmap says DungeonMind should own cross-consumer authority/context semantics, while Beat/Scene/Run progress and product workflow stay in DungeonMindBuddy.

That argues for this refinement:

> **Domains own their clocks and tick mechanics. A shared/kernel temporal layer may eventually own how references to those local transaction clocks are represented and interpreted across domains. It should not decide what constitutes a Beat, a Combat turn, or a Play mutation.**

The promotion test still applies. A Play-only `run_revision` history is not enough reason to add a DungeonMind kernel primitive.

Promotion becomes credible when a second independent consumer needs the same invariant, for example:

- durable Combat needs to reference the Play transaction at which it launched/returned;
- authoring/canon adoption needs stable provenance back to one Run transition;
- World temporal interpretation needs to cite a table observation without copying Play ontology.

At that point the candidate kernel concern is something like **transaction-point reference + temporal interpretation**, not “one master clock.”

No cross-domain integer comparison should ever be implied:

```text
Play tick 42 < Combat tick 42
```

is meaningless without an explicit relation recorded between those authorities.

---

## 8. Interaction with the merged current-moment cockpit design

PR #627 is now merged. This exploration does **not** reopen its reviewed decisions.

### BF1 — Beat-first grammar + manifest foundation

**No change.**

BF1 is structural Playable/manifest work. A Runtime tick history does not belong in it.

### BF2 — Runtime current-position v2 + relevance derivation

BF2 is where the Runtime mutation vocabulary becomes more important, but the ledger should **not be silently bundled into BF2**.

BF2 should preserve these properties because they make later history possible:

- one authoritative `run_revision` transition per successful durable Run transaction;
- no revision advance for no-op/replay;
- validation before persistence;
- derived relevance remains clockless;
- multi-field current-position transitions remain one atomic transaction.

Whether BF2 also implements history should be a separate capability decision with an explicit atomicity contract. Current recommendation: **no implicit scope expansion; let BF2 ship the reviewed Runtime semantics first.**

### BF3 — current-moment cockpit projection

A Run history could eventually power a compact **recent changes / what happened** projection, which fits the approved cockpit direction well.

But BF3 should not require history in order to exist. The primary cockpit can be built from authoritative current Run state + sealed Playable material. History should enter only if dogfood proves it materially improves table operation.

### BF4 — Plan Beat-first authoring

No direct dependency. Authoring revisions are another transaction clock, but the absence of historical revision bytes is a separate capability problem. Do not solve workspace revision archival merely to make the tick idea symmetrical.

### BF5 — legacy/migration posture

Do not fabricate history for old Runs. If Runtime history is introduced later, it may begin at the version/capability boundary with an explicit baseline rather than pretending pre-history exists.

### Combat lane

Combat remains a separate clock. The first shared need, if any, is likely a **cross-domain reference**, not a shared tick sequence.

`linkedCombatRuntime` may eventually record enough identity to say which Combat authority belongs to the Run. If dogfood later needs “Combat began at Run revision 57,” that is evidence for a transaction-reference seam.

---

## 9. Promotion ladder

The safest sequence is evidence-driven:

### Stage 0 — current truth

```text
Run record is authority
run_revision is CAS / transaction revision
no Run history contract
TL00 owns fictional temporal interpretation on World assertions
```

### Stage 1 — Play-local history, only if dogfood needs it

```text
one Run transaction → one revision transition
history records typed changes for that transition
Run record remains current-state authority
no fictional-time inference
```

Choose same-file or an explicit recovery protocol based on the actual requirement.

### Stage 2 — second-domain pressure

If Combat, authoring, or governed World adoption needs to refer to local transaction points, design a generic shared reference seam.

### Stage 3 — kernel promotion

Only after the promotion test is satisfied, consider DungeonMind owning the generic interpretation/reference contract. Domain counters and product semantics stay with their owners.

---

## 10. Hard design rules carried forward

1. **No global tick.** Ticks are local to a durable authority.
2. **Beat is not the transaction clock.** It is the narrative current-moment frame.
3. **No automatic fiction-time inference from Runtime order or wall-clock recording time.**
4. **TL00 fictional `valid_time` is not “the revisions during which a Runtime field held this value.”**
5. **Derived state does not get an independent clock without evidence.**
6. **One CAS transaction may contain multiple semantic changes.** Preserve that atomic grouping in any history.
7. **A lock is not a multi-file transaction.** A ledger and Run record need an explicit atomicity/recovery contract if stored separately.
8. **Run record remains authority unless a reviewed design deliberately migrates authority.**
9. **No retroactive fabricated history.** Legacy Runs may have an explicit baseline or no history.
10. **Kernel promotion requires cross-consumer pressure.** Do not hoist Play vocabulary or mechanics merely because the abstraction sounds general.

---

## 11. Questions worth dogfooding rather than answering now

1. Does the GM actually want a visible “recent changes” trail during Play, or is history mainly useful for recap/debugging afterward?
2. Is note history valuable, or does retaining every note edit create noise compared with recording only semantic table transitions?
3. Do we need independent recovery from history, or only trustworthy audit/recap inside the Run authority?
4. When Combat becomes durable, does the GM need explicit Play↔Combat temporal anchoring beyond a linked runtime handle?
5. Does any real canon/adoption workflow need to cite an exact Run revision as evidence?
6. Does workspace history become necessary because Runtime history exposes a painful asymmetry, or is current-revision-only authoring still adequate?
7. What is the first second consumer that makes a generic `TransactionPointRef` safer than product-local references?

---

## 12. Current recommendation

Do **not** alter BF1 or reopen PR #627.

Proceed with the reviewed Beat-first sequence. Keep this exploration visible while BF2/BF3 dogfood the actual Runtime/cockpit experience.

The next concrete decision point should be evidence-based:

> **After BF2 establishes v2 Runtime mutation semantics, decide whether “ordered history of Run changes” is independently useful enough to deserve one atomic slice before or alongside later cockpit dogfood.**

If yes, start Play-local and keep the Run record authoritative. Treat cross-domain temporal adjudication as a later promotion candidate, not a prerequisite.

The deeper architectural insight is retained in this refined form:

> **DungeonMindBuddy is not building one clock. It is building truthful local authorities whose changes can be ordered, referenced, and eventually interpreted together without pretending their notions of time are the same.**
