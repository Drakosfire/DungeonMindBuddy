# Hempholm Support Knowledge Seeds

This directory contains hand-authored support knowledge for the C1S4 preplanning vertical slice.

These artifacts are **manual perfect-ingestion surrogates**. They are not an ingestion implementation and they are not campaign canon. They represent the kind of structured support knowledge a future source-module/adaptation ingestion pipeline should eventually produce from the uploaded/adapted Hempholm source material.

## Authority model

The artifacts deliberately separate three layers:

1. **Source module facts** from `Of Conks & Cons` v2.1.
   - These facts describe the third-party adventure module.
   - They are planning support, not Longmont campaign canon.

2. **Adaptation notes** for the Longmont C1S4 Hempholm use case.
   - These map source-module elements into likely retained, modified, replaced, omitted, or campaign-specific elements.
   - They describe adaptation intent and table-prep context, not observed play truth.

3. **Retrieval cards**.
   - These are small, retrieval-friendly support records for planner experiments.
   - They are designed to be used in a future `prior_plus_support` mode alongside the C1S1-C1S3 KB.

## Retrieval modes

- `prior_only`: C1S1-C1S3 session memory only. These support artifacts are excluded.
- `prior_plus_support`: C1S1-C1S3 session memory plus these Hempholm support artifacts.
- `oracle_grading`: C1S4 recap/oracle material only for grading, never planner-visible.

## Files

- `source_module_facts.of_conks_and_cons.json`: structured source-module facts.
- `adaptation_notes.hempholm_c1s4.json`: source-to-adaptation mapping notes.
- `retrieval_cards.hempholm_support.jsonl`: retrieval-friendly support cards.

## Guardrail

No answer should claim these artifacts prove what happened in C1S4. Observed play remains sourced from the C1S4 recap/oracle lane only.
