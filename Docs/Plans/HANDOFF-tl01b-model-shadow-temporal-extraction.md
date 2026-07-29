# HANDOFF — TL01B: Evidence-Bound Model Shadow Temporal Extraction

**Created:** 2026-07-29  
**Status:** ACTIVE  
**Required dependency:** PR `#450`, merged as `d6ea4959c9bcc2f113ef50d912629864c1a1c04b`  
**Branch:** `feat/tl01b-model-shadow-temporal-extraction`  
**Base SHA:** `d6ea4959c9bcc2f113ef50d912629864c1a1c04b`

Sealed case → evidence packets → Responses strict batch → grounding → TL01 overlay → preview → gold compare. Implementation: `src/graph_memory/temporal_shadow_extraction*.py`, cohort under `evals/graph_memory_layer/examples/temporal_shadow_cohort/`, contract `Docs/Design/CONTRACT-temporal-shadow-extraction-v1.md`.

Full specification lives in the authoring conversation (TL01B §0–§31). No graph authority writes; do not modify TL01 kernel or `temporal_shadow.py`.
