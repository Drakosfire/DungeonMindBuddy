# Runbook — Authored World Object Magic-Moment Dogfood

**Status:** ACTIVE RUNBOOK — PUBLICATION-FIRST SEQUENCING  
**Updated:** 2026-07-30  
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)

## 1. Purpose

This runbook turns roadmap gates into blocking product evidence.

Tests answer whether a contract behaves deterministically. Dogfood answers whether the GM can experience the intended capability with real campaign material and whether identity, authority, and reload seams remain trustworthy.

The critical statblock gate sequence is now:

```text
R0-A accepted-revision recovery
→ MAGIC-D3 publish/query/hydrate/project
→ MAGIC-D4 place across surfaces
→ MAGIC-D5 enter live combat
```

`R0-B`, `MAGIC-D1`, and `MAGIC-D2` remain valuable grounded-authoring proofs, but they run in a parallel lane and do not block publication after one exact accepted revision exists.

## 2. Rules

- Use real campaign data unless the gate explicitly requires failure injection.
- Do not manually edit hidden state to make a gate pass.
- Do not substitute script output for a named user-facing experience.
- Record exact world, campaign, graph revision, object/resource locators, and operation IDs.
- A pass with serious friction is `PASS_WITH_FRICTION`, not silent success.
- An unavailable external provider is `BLOCKED_DEPENDENCY`.
- A reachable provider returning an invalid product result is `FAIL_PRODUCT` or `FAIL_ARCHITECTURE`, not `BLOCKED_DEPENDENCY`.
- Exact consumers pin exact revision identity; never substitute `latest`.
- Saved mechanics, graph publication, projection, placement, and combat runtime remain separate.
- A later gate may proceed without a parallel authoring convenience gate when the actual technical prerequisite is satisfied.

## 3. Result file

Create:

```text
Docs/Reports/MAGIC-MOMENT-<GATE>-<YYYY-MM-DD>.md
```

Template:

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
What exact identities already existed? What was deliberately not preselected?

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
- publication operation ID:
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
The smallest capability that should be dispatched next.
```

## 4. `R0-A` protocol — Exact accepted-revision prerequisite

**Operator pickup:** [`INSTRUCTIONS-reboot-dogfood-R0A-R0B.md`](INSTRUCTIONS-reboot-dogfood-R0A-R0B.md)  
**Detailed script:** [`SCRIPT-R0-A-statblock-live-dependency-proof.md`](SCRIPT-R0-A-statblock-live-dependency-proof.md)

1. Start with a real nontrivial Threat concept.
2. Create a ThreatDraft in the current Workbench.
3. Generate through the real provider.
4. Edit one shipped dedicated numeric field: primary AC, HP scalar, or ability score.
5. Validate the exact working definition.
6. Accept one exact revision.
7. Close/reload and reopen the exact accepted identity.
8. Capture provider, contract, field/reference validation, and parse failures honestly.

AI revise remains `DEFERRED_REVISE_UX` and is not required for this prerequisite.

Pass only when exact `(statblock_id, revision_id, digest)` survives reopen.

If the provider is reachable but returns `definition_invalid`, the result is `FAIL_PRODUCT`. Preserve the provider diagnostics and do not manufacture a candidate.

## 5. `R0-B` protocol — Deep unioned-graph research and provisional authoring

Choose a question that:

- concerns something partly forgotten;
- requires relationships or events beyond one obvious recent document;
- would be useful for designing a Threat;
- is not answered by manually naming a source path.

Run it through the user-facing Hermes path.

Record:

- pinned graph revision;
- retrieval/session identity when available;
- selected or matched node IDs;
- admitted source anchors;
- diagnostics and incomplete coverage;
- established, inferred, creative proposal, and unknown;
- the resulting provisional Threat description.

A useful grounded answer and provisional description may pass the research/content portion even when a stable authoring artifact or direct ThreatDraft handoff does not yet exist.

This gate informs the parallel authoring lane. It does not block `SBW08` after `R0-A` produces an accepted revision.

## 6. `MAGIC-D1` protocol — Hermes to durable ThreatDraft

1. Start from a successful grounded Hermes answer.
2. Choose the explicit authoring action.
3. Review/edit the campaign-facing description artifact.
4. Create or open the ThreatDraft.
5. Open the Workbench from the returned exact identity.
6. Reload and reopen.

Pass only when graph/source context and draft identity survive without manual copy/paste or reselection.

## 7. `MAGIC-D2` protocol — Connected authoring to accepted mechanics

1. Generate from the grounded draft.
2. Review full mechanics.
3. Make one meaningful supported edit.
4. Validate.
5. Revise once after the GM-facing revise UX exists.
6. Compare proposals sufficiently to choose one.
7. Accept.
8. Reload exact accepted mechanics.

Pass only when the GM can distinguish grounded prose, creative proposal, generated mechanics, operator edits, and the exact immutable accepted revision.

`MAGIC-D2` is a connected-authoring proof. It is not a prerequisite for `SBW08` when `R0-A` has already produced the exact accepted revision used for publication.

## 8. `MAGIC-D3` protocol — Publish, query, hydrate, and project

1. Start from an accepted exact statblock revision.
2. Preview create-new and connect-existing possibilities.
3. Inspect likely matches and explicitly choose or refuse.
4. Review proposed graph object, relationships, authority, visibility, evidence, and exact binding.
5. Confirm through graph governance.
6. Reload the committed graph revision.
7. Ask Hermes at least:
   - one exact/alias-name question;
   - one role, capability, relationship, location, faction, or event question that does not name the Threat exactly.
8. Resolve the Hermes result to the exact `ThreatStatblockBinding`.
9. Open compact and full projections hydrated from the exact accepted revision.
10. Inject or encounter one graph failure/stale case and retry.

Pass only when:

- publication does not duplicate mechanics or silently merge identity;
- the exact binding survives reload;
- Hermes can discover the Threat semantically;
- the exact mechanics hydrate from the owning store;
- projection does not silently select a different binding or revision;
- a newer statblock revision does not move the published binding implicitly.

## 9. `MAGIC-D4` protocol — Cross-surface placement

Use the same published Threat from:

- Hermes results;
- graph inspection;
- Ingest / node editing;
- Build;
- Plan;
- exact Threat projection.

Create at least one durable placement with exact Threat, binding, revision, host locator, quantity, role, trigger, and notes. Reload each affected surface.

Pass only when:

- the object is reused rather than copied;
- exact locators survive reload;
- each surface invokes the correct owning capability;
- a newer revision does not silently repin the placement.

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
- do not proceed merely because the next SBW number exists;
- do not block the publication/placement critical path on a parallel authoring convenience unless it is a demonstrated technical dependency.
