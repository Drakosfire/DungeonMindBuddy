# C1S4 Support Knowledge Seeds

This directory contains hand-authored support knowledge for the C1S4 preplanning vertical slice.

These artifacts are **manual perfect-ingestion surrogates**. They are not an ingestion implementation. They represent the kind of structured support knowledge a future source-module/worldbuilding/adaptation ingestion pipeline should eventually produce.

The support knowledge exists so the vertical slice can practice retrieval and planning over idealized structured knowledge without blocking on full ingestion.

## Retrieval contract

Read these before wiring support knowledge into retrieval:

- `SUPPORT_KNOWLEDGE_RETRIEVAL_CONTRACT.md`
- `support_retrieval_field_policy.json`

The contract is intentionally stricter than the support-card schemas. Support cards may contain evaluation metadata such as `usable_for_questions`, but retrieval code must not use that metadata for indexing, filtering, ranking, selection, or query expansion.

The future support retriever should run at least two diagnostic modes:

- `content_only`: index `title` + `summary` only.
- `content_plus_lexical_hints`: index `title` + `summary` + `retrieval_terms`.

Any benefit from lexical hints should be reported separately. This prevents a benchmark from looking successful merely because it matched hand-authored question IDs or target metadata.

## Authority model

These files are planner-support material, not observed C1S4 play truth.

The artifacts deliberately separate multiple layers:

1. **Source module facts** from `Of Conks & Cons` v2.1.
   - These facts describe the third-party Hempholm adventure module.
   - They are planning support, not Longmont campaign canon by themselves.

2. **Adaptation notes** for the Longmont C1S4 Hempholm use case.
   - These map source-module elements into likely retained, modified, replaced, omitted, or campaign-specific elements.
   - They describe adaptation intent and table-prep context, not observed play truth.

3. **Elderwyld worldbuilding facts**.
   - Elderwyld is the continent/world layer.
   - Mirathorn is a city inside Elderwyld, not the worldbuilding root.
   - These facts support world-aware planning, especially C1S4 Beat 1 Q3.

4. **Elderwyld travel and ecology facts**.
   - These summarize road grammar, wilderness motifs, pre-era conical hills, geomantic drakes, and migrating forest ecology.
   - Route-specific and campaign-stateful sources are explicitly labeled so they are not backported into C1S4 as hard canon.

5. **Retrieval cards**.
   - These are small support records for planner experiments.
   - They are designed to be used in a future `prior_plus_support` mode alongside the C1S1-C1S3 KB.
   - They are not keyed answer cards. Retrieval must treat them as ordinary normalized corpus records after policy filtering.

## Retrieval modes

- `prior_only`: C1S1-C1S3 session memory only. These support artifacts are excluded.
- `prior_plus_support_content_only`: C1S1-C1S3 session memory plus support artifacts, indexing only support-card `title` and `summary`.
- `prior_plus_support_content_plus_lexical_hints`: C1S1-C1S3 session memory plus support artifacts, indexing support-card `title`, `summary`, and `retrieval_terms`.
- `world_support`: worldbuilding/travel support allowed, but still not C1S4 oracle material.
- `oracle_grading`: C1S4 recap/oracle material only for grading, never planner-visible.

## Files

### Retrieval contract

- `SUPPORT_KNOWLEDGE_RETRIEVAL_CONTRACT.md`: human-readable retrieval visibility and anti-fake-good contract.
- `support_retrieval_field_policy.json`: machine-readable field visibility policy for future loader/retriever/tests.

### Hempholm / source-module support

- `source_module_facts.of_conks_and_cons.json`: structured source-module facts.
- `adaptation_notes.hempholm_c1s4.json`: source-to-adaptation mapping notes.
- `retrieval_cards.hempholm_support.jsonl`: retrieval-friendly Hempholm support cards.

### Elderwyld / world-travel support

- `elderwyld_worldbuilding_facts.seed.json`: hand-authored world/city facts from existing Elderwyld/Mirathorn corpus.
- `elderwyld_travel_ecology.seed.json`: hand-authored road, wilderness, conical hill, geomantic drake, and migrating forest support facts.
- `retrieval_cards.elderwyld_world_travel_support.jsonl`: retrieval-friendly Elderwyld world/travel support cards.

## Guardrails

No answer should claim these artifacts prove what happened in C1S4. Observed play remains sourced from the C1S4 recap/oracle lane only.

No answer should treat Mirathorn as the continent. Elderwyld is the continent/world layer; Mirathorn is a city node inside it.

No answer should treat Campaign 2 stateful travel notes as Campaign 1 canon unless a specific adaptation/promote step exists.

No answer should claim the exact Stone Bridge-to-Mirathorn route is known from these support artifacts. The current support knowledge can describe Mirathorn's final approach and Elderwyld travel grammar, but the specific route gazetteer remains a known gap.

No retriever should use `usable_for_questions`, question IDs, oracle labels, expected retrieval context, or benchmark-target fields to select records.
