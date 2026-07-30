# Runbook — Authored World Object Magic-Moment Dogfood

**Status:** ACTIVE RUNBOOK  
**Date:** 2026-07-28  
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)

## 1. Purpose

This runbook turns roadmap dogfood breaks into blocking product evidence.

Tests answer whether a contract behaves deterministically. Dogfood answers whether the GM can experience the intended capability with real campaign material and whether the seams feel connected.

## 2. Rules

- Use real campaign data unless the gate explicitly requires a failure injection.
- Do not manually edit hidden state to make a gate pass.
- Do not substitute a script output for the user-facing experience when the gate names Hermes, Workbench, Plan, Build, Ingest, or Combat.
- Record exact world, campaign, graph revision, object/resource locators, and relevant operation IDs.
- Preserve screenshots or exported receipts when useful, but the written result is authoritative.
- A pass with serious friction is recorded as `PASS_WITH_FRICTION`, not silently promoted to clean success.
- An unavailable external provider is `BLOCKED_DEPENDENCY`, not a product pass or fail.

## 3. Result file

Create one report under:

```text
Docs/Reports/MAGIC-MOMENT-<GATE>-<YYYY-MM-DD>.md
```

Use this shape:

```markdown
# Magic Moment Dogfood — <gate>

**Date:**
**Operator:**
**Repository SHA:**
**World / campaign:**
**Graph revision:**
**Result:** PASS | PASS_WITH_FRICTION | FAIL_PRODUCT | FAIL_ARCHITECTURE | BLOCKED_DEPENDENCY

## Intent

What real GM task was attempted?

## Starting state

What was already known or selected? What was deliberately not preselected?

## Steps actually taken

Numbered user-visible actions.

## Durable identities

- retrieval session:
- selected node IDs:
- admitted source anchors:
- draft ID/version:
- candidate ID:
- statblock ID/revision/digest:
- Threat ID/binding ID:
- placement ID:
- combat encounter/runtime entity IDs:

## What felt magical

What worked as one connected experience?

## Friction and misses

Where did the operator copy data, reselect identity, leave the product, or distrust the result?

## Failure / retry / reload observations

What happened after dependency failure, duplicate retry, stale state, browser reload, or server restart?

## Verdict

Why the gate passed or failed.

## Required next slice

The smallest capability that should be dispatched next. Do not list broad wishlist work.
```

## 4. `R0-A` protocol — Existing statblock dependency path

**Start-here after projection recovery:** [`INSTRUCTIONS-reboot-dogfood-R0A-R0B.md`](INSTRUCTIONS-reboot-dogfood-R0A-R0B.md)  
**Operator script (step-by-step):** [`SCRIPT-R0-A-statblock-live-dependency-proof.md`](SCRIPT-R0-A-statblock-live-dependency-proof.md)

1. Start with a real nontrivial Threat concept.
2. Create a ThreatDraft in the current Workbench.
3. Generate through the real provider.
4. Edit at least one dedicated numeric combat field (primary AC, HP scalar, or ability score) — not rename / `rules_text`-only. Typed mechanic fields (attack bonus, damage, save DC, speed) are out of R0-A scope until a later editor expansion.
5. Validate the exact working definition.
6. Accept one exact revision (edited generate candidate is enough).
7. Close/reload and reopen the exact accepted revision.
8. Capture all provider, contract, and parse failures honestly.

**Deferred:** AI revise (`Revise with AI`) — SBW06c UX is operator-hostile; record `DEFERRED_REVISE_UX`. Not required for PASS. Re-include after revise UX cleanup (Backlog). `MAGIC-D2` still expects revise once that UX is usable.

Pass only when the accepted exact identity and digest survive reload.

## 5. `R0-B` protocol — Deep unioned-graph question

**Operator detail (how to ask / known non-failures):** [`INSTRUCTIONS-reboot-dogfood-R0A-R0B.md`](INSTRUCTIONS-reboot-dogfood-R0A-R0B.md) §4

Choose a question that:

- concerns something partly forgotten;
- requires campaign relationships or events beyond one obvious recent document;
- would be useful for designing a Threat;
- is not answered by manually naming a source path.

Example shape:

> What do we actually know about the buried or singing creatures connected to Mireward, the Shepherds, and the recovered meat-goo magic? What is established, what is inferred, and what kind of creature description follows from that?

Run the question through the user-facing Hermes path.

Pass requires:

- meaningful investigation across the admitted unioned graph and source context;
- inspectable support;
- explicit uncertainty;
- an editable description suitable for a ThreatDraft;
- recorded graph revision, selected nodes, source anchors, and gaps.

## 6. `MAGIC-D1` protocol — Hermes to ThreatDraft

1. Start from a successful broad Hermes answer.
2. Choose the product action that develops the answer as a Threat.
3. Review/edit the generated description.
4. Create the ThreatDraft.
5. Open the Workbench from the returned draft identity.
6. Reload and reopen.

Pass only when context and identity survive without manual copy/paste or reselection.

## 7. `MAGIC-D2` protocol — ThreatDraft to accepted revision

1. Generate from the `MAGIC-D1` draft.
2. Review full mechanics.
3. Make one meaningful edit.
4. Validate.
5. Revise once.
6. Compare proposals sufficiently to choose one.
7. Accept.
8. Reload exact accepted mechanics.

Pass only when saved mechanics are exact, immutable, reloadable, and still clearly not graph-published.

## 8. `MAGIC-D3` protocol — Publish Threat and binding

1. Start from an accepted exact statblock revision.
2. Preview create-new and connect-existing possibilities.
3. Choose one intentionally.
4. Review proposed graph object, relationships, authority, visibility, evidence, and exact binding.
5. Confirm.
6. Reload the committed graph revision.
7. Open the Threat projection.
8. Inject one graph failure or stale case if the normal path does not encounter one.

Pass only when retry/recovery does not duplicate mechanics or silently create a second Threat.

## 9. `MAGIC-D4` protocol — Cross-surface placement

Use the same published Threat from:

- Ingest / node editing;
- Build;
- Plan.

Create at least one durable placement with quantity, role, trigger, and notes. Reload each surface. Confirm the exact revision remains pinned.

Pass only when the object is reused rather than copied and each surface invokes the correct owning capability.

## 10. `MAGIC-D5` protocol — Live combat import

1. Start from an exact Threat placement when available; otherwise use an exact Threat binding/revision.
2. Add the requested quantity to the current live combat encounter.
3. Verify distinct runtime instance IDs.
4. Set or roll initiative.
5. Apply damage and a condition.
6. Advance turns.
7. Reload the combat encounter.
8. Drill into the exact statblock revision from a row.
9. Retry the original import to observe duplicate/idempotency behavior.

Pass only when runtime changes remain mutable and durable without changing graph truth or statblock mechanics.

## 11. Gate closeout

After each gate:

- link the report from the tracker or next implementation handoff;
- convert observed friction into the smallest next slice;
- update stale assumptions in pre-designed handoffs;
- do not proceed merely because the next SBW number already exists.
