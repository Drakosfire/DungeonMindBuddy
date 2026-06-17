# Graph Memory Baseline Case Index

## Purpose

This index describes the frozen baseline case set for the Ontology / Taxonomy ladder. The cases name graph-native failure families that future taxonomy, ontology IR, deterministic materialization, graph reports, and shadow retrieval work must preserve, measure, or improve.

## Status

Status: baseline case definitions only.

This PR freezes the case manifest and report structure. It does not claim measured graph performance, regenerate historical retrieval output, or reinterpret current retrieval behavior.

## What This Freezes

- The initial graph-memory baseline case IDs.
- The failure families future ladder rungs must account for.
- The preservation requirements for source grounding, citation safety, and non-regression.
- The expectation that future comparisons attach source-grounded evidence and traceable expansion paths.

## What This Does Not Freeze

- Measured graph or retrieval performance.
- A taxonomy registry, ontology IR, graph schema, or materializer.
- Any production retrieval behavior.
- Canonical corpus semantics or source truth.
- Entity merges, aliases, or authority-state decisions not already backed by source artifacts.

## Case Table

| Case ID | Family | Why It Matters | Future Graph Expectation |
| ------- | ------ | -------------- | ------------------------ |
| `C1S1_ROSTER_IDENTITY_ROUTING` | `roster_identity` | Roster-style recall may need party, NPC, route, and hub identity links rather than one lexical match. | Measure whether roster and hub identity links improve recall while keeping evidence source-unit grounded. |
| `C1S2_CLEAN_CONTROL` | `clean_control` | Graph work needs a control case to prove it does not add noise where direct retrieval is already clean. | Show non-regression and reject or down-rank unnecessary expansion. |
| `C1S3_LOCATION_HIERARCHY_STONEBRIDGE_RIVERS_EDGE` | `location_hierarchy` | Parent and sublocation queries can miss each other or over-attract sibling context. | Connect parent and sublocation evidence without flooding unrelated sibling facts. |
| `C1S13_ALIAS_IDENTITY_DRAVEN_NECROMANCER` | `alias_identity_bridge` | Name, role, and alias-like references can miss each other or merge unsafely. | Measure alias/name recall while preserving provenance and merge caution. |
| `C2S22_FINAL_BEAT_SESSION_RECALL` | `session_scoped_final_beat` | Final-beat questions need session scope and ordering, not only topical similarity. | Evaluate session-bound ordering without pulling in neighboring-session events. |
| `SESSION20_BREADCRUMB_NATURAL_QUERY` | `breadcrumb_natural_query` | Natural questions may not share terms with normalized breadcrumbs or route labels. | Measure breadcrumb-to-route expansion while citations remain source-grounded. |
| `UNRESOLVED_HOOK_RESURFACING` | `unresolved_hook_resurfacing` | Hooks may need to resurface through relationships rather than shared query terms. | Surface hook candidates with visible relationship paths and authority/lifecycle state. |
| `HIGH_DEGREE_HUB_OVER_ATTRACTION` | `hub_over_attraction` | Broad hubs can flood context if every graph edge is treated as useful. | Report hub fan-out and measure precision before admitting hub-driven expansion. |
| `AUTHORITY_BOUNDARY_GM_PREP_VS_PLAYED_TRUTH` | `authority_boundary` | Prep notes, rumors, candidate facts, and played events must not collapse into one truth bucket. | Keep authority and evidence roles visible and prevent unsupported promotion. |
| `CITATION_GROUNDING_NO_SUMMARY_AS_SOURCE` | `citation_grounding` | Derived graph summaries must never become source evidence. | Cite source artifacts for evidence and keep graph summaries diagnostic only. |

## Baseline Case Families

The baseline manifest currently covers these required families:

- `roster_identity`
- `clean_control`
- `location_hierarchy`
- `alias_identity_bridge`
- `session_scoped_final_beat`
- `breadcrumb_natural_query`
- `unresolved_hook_resurfacing`
- `hub_over_attraction`
- `authority_boundary`
- `citation_grounding`

## Promotion Use

Future PRs should attach real current-system outputs, deterministic graph reports, or shadow retrieval comparisons to these cases. Promotion beyond shadow mode should require evidence that graph work preserves clean/control behavior, source grounding, citation boundaries, and production retrieval safety while measuring or improving at least one graph-native failure family.

## Next Step

The next ladder PR should add the taxonomy registry v0. Do not start ontology IR until the taxonomy registry exists.
