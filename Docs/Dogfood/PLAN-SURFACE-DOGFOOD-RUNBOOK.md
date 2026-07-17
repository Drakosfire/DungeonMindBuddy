# /plan Dogfood Runbook — S1 Latest-Recap Sensemaking

## Purpose

Dogfood **only the accepted S1 slice**: conversational latest-recap change reading.

```text
User (U1): What changed after the latest ingested recap?
Agent (A1/A2): Investigate with bounded context; disclose memory lag usefully.
```

`/plan?dogfood=1` is an operator measurement scaffold. This runbook is **not** board
save/recovery, Tripod continuity, graph-object cards, or statblock authoring.

**Authority:** `Docs/Design/UX-STORIES-hermes-campaign-authoring-foundation.md` (U1, A1, A2),
`Docs/Reports/HERMES-S1-LATEST-RECAP-DOGFOOD-2026-07-15.md` (gate ACCEPTED).

## Out of scope for this pass

- Editing / saving Session Prep.md
- Reload / localStorage recovery proofs
- Tripod Null-Calf same-thread continuity (Rung 5 accepted — three live trials DONE)
- Plan Hermes-only asks (Rung 7 DOING — demolition present; cumulative acceptance open; ChatModule retains Live)
- Graph object dogfood list
- CreativeOperationSession / draft / promotion (Phase 2+)

## Preconditions

- Dev servers running (live-control API + UI).
- World Graph activated for Eldyrwild / longmont-c2.
- Branch tip includes the S1 empty-graph repair (`latest_recap_change` on the retrieval session).

## Start URL

```text
/plan?dogfood=1&campaign=longmont-c2&session=24&tool=recap
```

- `?session=24` focuses memory/graph on the latest admitted recap.
- Live packet may still be session-22; that mismatch is OK for this slice.
- Open the **Dogfood checklist** panel and work top to bottom.

## Journey (one pass)

### 1. Setup

1. Confirm the dogfood World Graph snapshot shows focus `session-24` (or your latest admitted recap).
2. Open **Ask DungeonBuddy** on a **fresh** thread.
3. Leave Hermes as the agent (default on new Plan threads).

### 2. Ask the S1 question

Use the populated pill or type exactly:

```text
What changed after the latest ingested recap?
```

Free-form text is the task. The pill is optional starting context, not a hidden form.

### 3. Judge the answer (pass / fail)

**Pass when:**

- **Hermes chat** narrates Session 24 campaign movement (co-GM prose), not a claim-ID ledger;
- **Latest-recap comparison support** (separate panel) names the latest admitted recap,
  comparison boundary, and memory lag, and can show the admitted recap excerpt;
- grounding is not a generic empty-graph abstention (`no_admissible_claims`);
- Hermes does **not** say it cannot narrate until promote.

**Fail when:**

- Hermes chat is only lag metadata + raw recap dump (support content stuffed into chat);
- Hermes only says it found nothing / cannot answer because the focused graph is empty;
- support never names the latest recap or comparison boundary;
- lag is disclosed but the admitted recap body is never available in support;
- grounding is a generic abstention with no named lag story.

Expected grounding today: `partial` / `partial_coverage` with
`admitted_recap_source_read` and lag disclosed. Hermes chat heading:
**Hermes answer** (or **No Hermes answer** if the agent was silent). Lag and
admitted-recap excerpt live in **Latest-recap comparison support**, not the
Hermes bubble.

### 4. Optional inspection

Open evidence / trace if present. Confirm the lag story matches the prose. Do not require a full claim list.

### 5. Capture feedback

1. Check off checklist items as you go.
2. Notes: what felt like sensemaking vs report/abstention.
3. **Copy dogfood report** → paste into chat.
4. **Reset dogfood checklist** clears checklist + notes only.

## Suggested sequence

```text
1. Start API + UI
2. Open /plan?dogfood=1&campaign=longmont-c2&session=24
3. Confirm focus session-24 on the dogfood snapshot
4. Ask DungeonBuddy → fresh Hermes thread
5. Ask: What changed after the latest ingested recap?
6. Score against Pass/Fail above
7. Optional: inspect grounding / evidence
8. Copy dogfood report
```

## What this unlocks next

After you have felt this journey once:

1. **Phase 2** — smallest `CreativeOperationSession` kernel (no domain generator yet).
2. **S2 later** — “Collect everything we know about this threat… help me create a statblock.”
3. Keep the S1 lag disclosure path; do not reopen generic empty-graph abstention.
