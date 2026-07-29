# Magic Moment Dogfood — R0-A

**Date:** 2026-07-29  
**Operator:** GM operator  
**Repository SHA:** exact local SHA not captured; current repository authority was `9174dd5e99b3acf20f4d81858bff4a563f65ae97`  
**World / campaign:** `eldyrwild` / `longmont-c2`  
**Graph revision:** not captured  
**Result:** FAIL_PRODUCT

## Intent

Run the real GM-facing Statblock Workbench sequence for **Mireward Latchling**:

```text
create ThreatDraft
→ generate through current DungeonMindServer
→ inspect complete mechanics
→ make one meaningful mechanical edit
→ validate
→ revise
→ accept exact mechanics
→ reload and reopen
```

## Starting state

The operator used the normal product path with the real DungeonMindServer available. This was not a mock-provider, fixture, hidden-store, corpus-promotion, or scripted substitute.

The exact local repository SHA, graph revision, draft ID/version, request ID, and provider request identifiers were not captured in the reported observation.

## Steps actually taken

1. Opened the Statblock Workbench.
2. Authored or selected the **Mireward Latchling** ThreatDraft.
3. Requested real candidate generation.
4. Received the product error:

```text
Couldn’t generate a candidate for Mireward Latchling: Generated definition failed validation
```

5. Stopped the dogfood early after substantial preceding friction rather than retrying blindly or bypassing the product path.

The run did not reach candidate rendering, complete-definition editing, preview validation, revise, acceptance, or exact-revision reload.

## Durable identities

- retrieval session: not applicable to R0-A
- selected node IDs: not captured
- admitted source anchors: not captured
- draft ID/version: created or loaded by the product, exact identity not captured
- generation request ID: not captured
- candidate ID: not created
- revise proposal ID: not created
- statblock ID/revision/digest: not created
- Threat ID/binding ID: not applicable
- placement ID: not applicable
- combat encounter/runtime entity IDs: not applicable

## What felt magical

No magic moment was reached. The real provider path was reachable, but the first generated mechanics never became an inspectable candidate.

## Friction and misses

### Candidate generation failed before a candidate existed

DungeonMindServer accepted the request far enough to invoke its definition provider. The server then rejected the provider output in one of two current `definition_invalid` branches:

1. the provider payload did not parse as `StatblockDefinitionV1`; or
2. the parsed definition failed generation-candidate structural/reference validation.

Both branches currently collapse to the same public response:

```text
422 validation_failed: Generated definition failed validation
```

The operator therefore could not tell:

- which branch failed;
- which fields or references were invalid;
- whether the failure was caused by a provider schema miss, a domain-reference error, or another deterministic validator issue;
- whether retrying the same request would replay the same terminal failure;
- what change, if any, would make the request succeed.

### The current contract discards actionable validation evidence

As built on 2026-07-29:

- DungeonMindServer's generation service has access to the Pydantic `ValidationError` or the full `ValidationReceiptV1.issues[]` before returning `definition_invalid`.
- `raise_for_generation_failure` maps every `definition_invalid` to one generic HTTP message and emits no details.
- the durable candidate-generation failure snapshot stores only `kind` and `message`, so same-request replay cannot recover diagnostics that were never persisted.
- DungeonMindBuddy's transport error type can carry a structured `details` object, but the candidate-generation orchestration converts the error to `failure_category` and `failure_message` only.
- the Workbench therefore has no structured issue list to render.

This is a product observability and recovery failure at the exact boundary the dogfood gate was intended to exercise.

## Failure / retry / reload observations

The operator stopped after the first visible validation failure. No blind retry was used as evidence.

The current DungeonMindServer generation operation is durable by `(caller_scope, request_id)`. A failed operation is terminally snapshotted and a same-key replay returns the stored failure without a second provider call. Because the snapshot currently omits diagnostics, even a correct same-key replay would reproduce only the generic message.

No candidate identity existed to reload.

## Verdict

`FAIL_PRODUCT`.

This is not `BLOCKED_DEPENDENCY`: the dependency was reachable and executed generation work. It is not yet `FAIL_ARCHITECTURE`: the existing provider, validator, error-envelope, durable operation, and Buddy transport seams can support an inspectable failure without changing the authored-object lifecycle.

The gate failed because the product could neither produce a candidate nor explain the deterministic validation failure well enough for the GM or an implementer to act.

## Required next slice

Dispatch one **DungeonMindServer contract slice** before any prompt tuning, permissive parser change, automatic repair loop, Workbench library work, `SBW06d`, or broader publication work:

```text
DMS generation-validation diagnostics
```

### Mission

When candidate generation or revision rejects provider output as `definition_invalid`, DungeonMindServer returns and durably replays a bounded typed diagnostic packet that distinguishes schema parsing from domain validation and identifies the actionable validation issues without retaining or exposing the raw provider payload.

### Required invariant

```text
The same failed request identity returns the same safe diagnostic classification and issue packet on first response and replay.
```

### Named consumer successor

After the Server contract lands, DungeonMindBuddy must preserve the diagnostic packet in `GenerateThreatDraftCandidateResponseV1` and render it in the Workbench while retaining exact draft/request retry authority.

### Explicit non-goals for the first slice

- no raw provider payload or exception object in errors or durable stores;
- no broad schema relaxation;
- no silent coercion of invalid mechanics;
- no automatic second provider call;
- no prompt redesign based on an unknown failure;
- no Buddy UI changes in the Server PR;
- no claim that R0-A passes until Mireward Latchling is re-run through the product.
