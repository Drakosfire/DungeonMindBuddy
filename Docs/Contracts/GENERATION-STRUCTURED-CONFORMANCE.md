# GenerationEngine structured-conformance consumer boundary

**Status:** ACTIVE CONSUMER GUIDANCE  
**Date:** 2026-09-16  
**Owner of execution contract:** `Drakosfire/GenerationEngine`

## Decision

DungeonMindBuddy owns the schema and the domain meaning of generated data. GenerationEngine owns structural conformance of model output to that caller-supplied schema.

Buddy should therefore move toward this boundary:

```text
Buddy
  owns prompt/task meaning
  owns JSON Schema / product model definition
        ↓
GenerationEngine.generate_structured
  owns provider strategy
  owns parsing
  owns local JSON Schema validation
  owns bounded corrective inference retries
        ↓
schema-conforming generic object
        ↓
Buddy
  constructs product/domain type
  performs domain/evidence/workflow validation
```

The practical rule is:

> **If the validation asks whether the model returned the requested shape, it belongs in GenerationEngine. If it asks whether that shape is correct for DungeonBuddy, the campaign, evidence, or workflow, it remains in Buddy.**

## What Buddy should eventually stop duplicating

Once GenerationEngine's structured-conformance implementation is available and accepted, migration candidates include repeated inference plumbing such as:

```text
JSON extraction/parsing
schema-shape validation
validation-error formatting for the model
bounded model repair after schema mismatch
per-consumer structural retry loops
```

This does not authorize deleting those paths before the GE replacement exists and is proven.

## What stays in Buddy

Buddy continues to own validation such as:

```text
evidence actually supports an extracted assertion
campaign/world chronology is coherent
entity/reference resolution is meaningful
workflow-specific admission rules
product policy/business rules
Agent decisions and orchestration
```

Pydantic usage alone does not determine ownership. A Pydantic validation that merely enforces the same supplied structural schema is a candidate for GE ownership; a validator that encodes product semantics stays here.

## Retry distinction

GenerationEngine transport retries and structured-conformance retries are distinct:

```text
transport retry
→ timeout / rate limit / transient provider failure

conformance retry
→ provider returned content, but it failed structural schema validation
```

Buddy should not rebuild either retry class around GE once the engine contract owns it. Buddy may still retry an entire product workflow for product-level reasons.

## OpenRouter / DeepSeek lab consequence

The current OpenRouter/DeepSeek lab remains useful discovery evidence.

The lab has used provider-specific structured-output behavior with local validation. Until GenerationEngine can reproduce the required semantics through its provider-independent conformance layer, a visibly bounded lab-only direct-provider path remains acceptable.

Do not turn that temporary lab path into normal production routing.

Once GE can express the experiment without semantic loss, prefer the GE path so the lab receives one normalized deadline/retry/failure/observation boundary.

## Migration rule

For each future Buddy structured-generation migration:

1. identify the caller-supplied schema;
2. separate structural validation from domain validation;
3. move only structural parse/conformance/repair responsibility behind GenerationEngine;
4. preserve domain/evidence/workflow checks in Buddy;
5. delete the old structural retry path only after replacement proof;
6. verify GE observations account truthfully for all inference attempts.

## Historical note

The E5A boundary baseline is a characterization record and should not be rewritten to pretend this ownership split already existed. This document records the adopted successor direction.
