# Graph Memory Shared Source Vocabulary Contract

Created: 2026-06-21 (UTC)  
Status: active design contract for Agent Interaction, `/plan`, and future DungeonMindBuddy surfaces  
Workstream: Graph Memory / Ontology / Taxonomy  
Consumer context: Agent Interaction Bar/Pane and planning/live surfaces consuming recap ingestion outputs  

## Purpose

This document defines the minimal shared source vocabulary contract between recap ingestion outputs and downstream consumers such as Agent Interaction, `/plan`, future `/surfaces`, and the future ontology/taxonomy graph.

Agent Interaction should not consume ingestion internals such as `_normalized/`, `_breadcrumbed/`, `.records_meta.jsonl`, or `corpus_impact` as its semantic model.

Those are production artifacts of the ingestion pipeline.

Consumers should instead consume a small source-facing contract:

```text
SourceArtifact -> SourceAnchor -> SourceUnit
```

The ingestion adapter should translate current recap/session-memory outputs into that contract.

The contract should be stable enough for Agent Interaction today and replaceable or enrichable later by graph-backed retrieval.

This is not a unified mutable knowledge store. Corpus markdown on disk remains the source of truth. The adapter only describes what was produced, where it lives, how it can be referenced, and what lifecycle/evidence/canon role it has.

## Position

Graph Memory and downstream surfaces should share a semantic envelope, not raw ingestion step names.

The shared envelope is:

- source artifact
- source anchor
- source unit
- opaque locator
- canon state
- lifecycle state
- evidence role
- authority state
- visibility state
- provenance
- diagnostics

Agent Interaction may display ingestion results, reference/proof projections, and eventually question-answering surfaces. It should not learn raw ingestion layout or treat ingestion stages as semantic truth categories.

## Minimal TypeScript-Shaped Schema

```ts
type SourceArtifactKind =
  | "normalized_recap"
  | "breadcrumbed_recap"
  | "frontmatter_seed"
  | "session_memory_recordset"
  | "session_memory_meta"
  | "corpus_impact_proof"
  | "reference_index"
  | "generated_artifact"
  | "unknown";

type SourceLayer =
  | "raw_source"
  | "normalized_source"
  | "breadcrumb_layer"
  | "memory_layer"
  | "diagnostic_layer"
  | "derived_report"
  | "reference_layer";

type CanonState =
  | "played_canon"
  | "planning_scaffold"
  | "generated_candidate"
  | "candidate_extraction"
  | "diagnostic_only"
  | "reference_only"
  | "unknown";

type LifecycleState =
  | "created"
  | "ingested"
  | "indexed"
  | "candidate"
  | "validated"
  | "promoted"
  | "rejected"
  | "stale"
  | "diagnostic";

type EvidenceRole =
  | "source_evidence"
  | "navigation_hint"
  | "derived_summary"
  | "diagnostic_only"
  | "reference_tool"
  | "not_evidence";

type AuthorityState =
  | "played_truth"
  | "gm_prep"
  | "system_derived"
  | "llm_generated"
  | "user_generated"
  | "diagnostic"
  | "unknown";

type VisibilityState =
  | "gm_private"
  | "player_visible"
  | "internal_diagnostic"
  | "spoiler_sensitive"
  | "unknown";

type OpaqueLocator = {
  locatorId: string;
  scheme:
    | "corpus_path"
    | "artifact_path"
    | "jsonl_record"
    | "line_range"
    | "frontmatter_key"
    | "impact_proof"
    | "reference_id"
    | "graph_node"
    | "unknown";
  value: string;
  lineStart?: number;
  lineEnd?: number;
  anchor?: string;
};

type SourceArtifact = {
  artifactId: string;
  kind: SourceArtifactKind;
  layer: SourceLayer;

  label: string;
  campaignId?: string;
  sessionId?: string;
  sessionNumber?: number;

  canonState: CanonState;
  lifecycleState: LifecycleState;
  evidenceRole: EvidenceRole;
  authorityState: AuthorityState;
  visibilityState: VisibilityState;

  primaryLocator: OpaqueLocator;
  relatedLocators?: OpaqueLocator[];

  displaySummary?: string;
  metadata?: Record<string, string | number | boolean | null>;

  producedBy?: string;
  producedAt?: string;
};

type SourceAnchor = {
  anchorId: string;
  artifactId: string;

  label: string;
  anchorKind:
    | "document"
    | "section"
    | "line_range"
    | "sentence_unit"
    | "frontmatter_field"
    | "proof_record"
    | "reference";

  locator: OpaqueLocator;

  canonState: CanonState;
  lifecycleState: LifecycleState;
  evidenceRole: EvidenceRole;
  authorityState: AuthorityState;
  visibilityState: VisibilityState;

  metadata?: Record<string, string | number | boolean | null>;
};

type SourceUnit = {
  unitId: string;
  artifactId: string;
  anchorId: string;

  unitKind:
    | "recap_document"
    | "recap_section"
    | "sentence_unit"
    | "frontmatter_seed"
    | "impact_proof"
    | "reference_projection"
    | "diagnostic_record";

  label: string;

  displaySummary?: string;
  fields?: Record<string, string | number | boolean | null>;

  sourceAnchor: SourceAnchor;

  canonState: CanonState;
  lifecycleState: LifecycleState;
  evidenceRole: EvidenceRole;
  authorityState: AuthorityState;
  visibilityState: VisibilityState;

  provenance: Array<{
    provenanceId: string;
    artifactId: string;
    anchorId?: string;
    locator: OpaqueLocator;
    role: EvidenceRole;
  }>;

  diagnostics?: {
    validationIssues?: Array<{ severity: string; code: string; message?: string }>;
    sourceFamily?: string;
    producedBy?: string;
  };
};

type IngestionSourceBundle = {
  bundleId: string;
  campaignId?: string;
  sessionId?: string;
  sessionNumber?: number;

  producedBy: "recap_ingestion_adapter_v0";
  producedAt: string;

  artifacts: SourceArtifact[];
  anchors: SourceAnchor[];
  units: SourceUnit[];

  diagnostics?: {
    warnings?: string[];
    missingArtifacts?: string[];
    ambiguousArtifacts?: string[];
  };
};
```

## Minimal Python-Shaped Schema

```python
from dataclasses import dataclass, field
from typing import Literal

SourceArtifactKind = Literal[
    "normalized_recap",
    "breadcrumbed_recap",
    "frontmatter_seed",
    "session_memory_recordset",
    "session_memory_meta",
    "corpus_impact_proof",
    "reference_index",
    "generated_artifact",
    "unknown",
]

SourceLayer = Literal[
    "raw_source",
    "normalized_source",
    "breadcrumb_layer",
    "memory_layer",
    "diagnostic_layer",
    "derived_report",
    "reference_layer",
]

CanonState = Literal[
    "played_canon",
    "planning_scaffold",
    "generated_candidate",
    "candidate_extraction",
    "diagnostic_only",
    "reference_only",
    "unknown",
]

LifecycleState = Literal[
    "created",
    "ingested",
    "indexed",
    "candidate",
    "validated",
    "promoted",
    "rejected",
    "stale",
    "diagnostic",
]

EvidenceRole = Literal[
    "source_evidence",
    "navigation_hint",
    "derived_summary",
    "diagnostic_only",
    "reference_tool",
    "not_evidence",
]

AuthorityState = Literal[
    "played_truth",
    "gm_prep",
    "system_derived",
    "llm_generated",
    "user_generated",
    "diagnostic",
    "unknown",
]

VisibilityState = Literal[
    "gm_private",
    "player_visible",
    "internal_diagnostic",
    "spoiler_sensitive",
    "unknown",
]

@dataclass(frozen=True)
class OpaqueLocator:
    locator_id: str
    scheme: str
    value: str
    line_start: int | None = None
    line_end: int | None = None
    anchor: str | None = None

@dataclass(frozen=True)
class SourceArtifact:
    artifact_id: str
    kind: SourceArtifactKind
    layer: SourceLayer
    label: str
    canon_state: CanonState
    lifecycle_state: LifecycleState
    evidence_role: EvidenceRole
    authority_state: AuthorityState
    visibility_state: VisibilityState
    primary_locator: OpaqueLocator
    campaign_id: str | None = None
    session_id: str | None = None
    session_number: int | None = None
    related_locators: tuple[OpaqueLocator, ...] = ()
    display_summary: str | None = None
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)
    produced_by: str | None = None
    produced_at: str | None = None

@dataclass(frozen=True)
class SourceAnchor:
    anchor_id: str
    artifact_id: str
    label: str
    anchor_kind: str
    locator: OpaqueLocator
    canon_state: CanonState
    lifecycle_state: LifecycleState
    evidence_role: EvidenceRole
    authority_state: AuthorityState
    visibility_state: VisibilityState
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

@dataclass(frozen=True)
class SourceUnit:
    unit_id: str
    artifact_id: str
    anchor_id: str
    unit_kind: str
    label: str
    source_anchor: SourceAnchor
    canon_state: CanonState
    lifecycle_state: LifecycleState
    evidence_role: EvidenceRole
    authority_state: AuthorityState
    visibility_state: VisibilityState
    display_summary: str | None = None
    fields: dict[str, str | int | float | bool | None] = field(default_factory=dict)
    provenance: tuple[dict, ...] = ()
    diagnostics: dict[str, object] = field(default_factory=dict)
```

## Required Lifecycle / Canon / Source-Role Fields

These fields are required now:

```text
canonState / canon_state
lifecycleState / lifecycle_state
evidenceRole / evidence_role
authorityState / authority_state
visibilityState / visibility_state
```

Reasons:

- `canonState` prevents played canon, planning scaffold, generated candidate, diagnostic metadata, and reference-only tools from collapsing into one blob.
- `lifecycleState` says where the item is in the workflow: created, ingested, indexed, candidate, validated, promoted, rejected, stale, or diagnostic.
- `evidenceRole` says whether this can support a claim or is only navigation, summary, diagnostics, or a reference tool.
- `authorityState` says whether the item comes from played truth, GM prep, generated content, system derivation, or diagnostics.
- `visibilityState` prevents GM-private, spoiler-sensitive, player-visible, and internal-diagnostic content from being treated the same.

## Mapping Current Recap / Session-Memory Outputs

| Current ingestion output | Contract object(s) | Recommended kind/layer | Evidence/canon role | Consumer use |
|---|---|---|---|---|
| Normalized recap markdown | `SourceArtifact`, document-level `SourceAnchor`, optional section `SourceUnit`s | `normalized_recap` / `normalized_source` | Played canon, source evidence when anchored | “What recap was ingested?” and source-backed recap projection |
| Breadcrumbed recap markdown | `SourceArtifact`, breadcrumb anchors, reference/navigation `SourceUnit`s | `breadcrumbed_recap` / `breadcrumb_layer` | Played canon, navigation hint; source evidence only with anchored source refs | Reference chips, navigation, proof-backed jumps |
| Frontmatter seed markdown | `SourceArtifact`, frontmatter-field anchors, seed `SourceUnit`s | `frontmatter_seed` / `diagnostic_layer` or `reference_layer` | Planning scaffold or candidate extraction; not evidence by default | Show extracted seed metadata without treating it as canon |
| Session-memory JSONL/meta | `SourceArtifact` for recordset/meta, `SourceAnchor` per record/unit, `SourceUnit` per sentence unit | `session_memory_recordset` / `memory_layer` | Diagnostic/candidate unless explicitly source-anchored | Agent Interaction memory units and future graph materializer input |
| `corpus_impact` proof metadata | `SourceArtifact`, proof anchors, diagnostic proof `SourceUnit`s | `corpus_impact_proof` / `diagnostic_layer` | Diagnostic proof, not narrative evidence | Show what changed, what was written, and proof of ingestion effects |

## Adapter Output By Ingestion Artifact

### Normalized recap markdown

Produce:

- one `SourceArtifact`
- one document-level `SourceAnchor`
- optional section-level `SourceUnit`s if section boundaries are available
- an opaque locator to the normalized recap artifact
- no full markdown body in the bundle
- optional short display summary or title

Conservative defaults:

```text
canonState: played_canon
lifecycleState: ingested
evidenceRole: source_evidence
authorityState: system_derived
visibilityState: gm_private
```

### Breadcrumbed recap markdown

Produce:

- one `SourceArtifact`
- anchors for breadcrumb targets when available
- source units for reference/navigation projections
- an opaque locator to the breadcrumbed artifact
- reference metadata only; raw breadcrumb implementation path remains hidden

Use `evidenceRole: navigation_hint` by default. If a breadcrumb points to a specific source span, that anchor may carry `source_evidence`.

### Frontmatter seed

Produce:

- one `SourceArtifact`
- one anchor per useful frontmatter key
- one source unit per visible seed field or grouped seed object
- `canonState: planning_scaffold` or `candidate_extraction`
- `evidenceRole: not_evidence` or `diagnostic_only`

Frontmatter is useful for “what did ingestion infer or seed?” but is not automatically source evidence.

### Session-memory JSONL/meta

Produce:

- one `SourceArtifact` for the JSONL recordset
- one optional `SourceArtifact` for meta if separate
- one `SourceAnchor` per JSONL record
- one `SourceUnit` per sentence/source unit
- opaque line/unit locators
- small fields such as `unitId`, `lineStart`, `lineEnd`, `textHash`, `routeCount`, and `hasRoutes`
- no full `lexical_plain` by default

Conservative defaults:

```text
canonState: candidate_extraction
lifecycleState: candidate
evidenceRole: diagnostic_only
authorityState: system_derived
visibilityState: internal_diagnostic
```

If the unit directly anchors to normalized recap lines, the adapter may include source-anchor provenance, but the unit itself remains a derived memory unit.

### `corpus_impact`

Produce:

- one `SourceArtifact` for the proof object
- one `SourceUnit` per changed/written/validated artifact if available
- diagnostic/proof metadata only
- small fields such as `createdCount`, `updatedCount`, `skippedCount`, `affectedPathsCount`, `proofId`, and `status`

`corpus_impact` answers “what did ingestion do?” It is not campaign narrative evidence.

## Opaque Locator Fields

The following should remain opaque locators rather than semantic consumer fields:

- raw `_normalized/` path
- raw `_breadcrumbed/` path
- `.records_meta.jsonl` path
- raw `corpus_impact` proof path
- absolute filesystem paths
- internal ingestion step names
- full recap markdown body
- full breadcrumbed markdown body
- full session-memory JSONL line body
- full `lexical_plain` text by default
- raw corpus writer proof internals
- future graph node IDs, except inside diagnostics

Agent Interaction can render labels like “Normalized recap,” “Session memory units,” or “Corpus impact proof,” but it should not reason from `_normalized` as a semantic category.

## Agent Interaction Consumer Boundary

Agent Interaction may consume directly:

- `IngestionSourceBundle`
- `SourceArtifact[]`
- `SourceAnchor[]`
- `SourceUnit[]`
- artifact labels
- display summaries
- small typed fields
- lifecycle/canon/evidence/authority/visibility states
- opaque locators
- provenance summaries
- diagnostics and display-safe warnings

Agent Interaction should not consume directly:

- raw ingestion pipeline file paths as semantic model
- raw normalized/breadcrumbed/session-memory file contents
- corpus writer internals
- full JSONL metadata lines
- graph internals
- ontology taxonomy refs directly
- identity merge or alias candidate logic
- relationship inference output as truth
- source evidence claims without anchors/provenance

Agent Interaction can ask the adapter:

- What artifacts were produced?
- What units can I display?
- What anchors can I project?
- Which items are source-backed?
- Which items are diagnostic only?
- Which items are candidate extraction?
- Where should the user navigate if they click this?

Agent Interaction should not ask:

- Which raw ingestion stage produced this semantic truth?
- Which identity should this alias merge into?
- Which relationship is canon?
- Can this summary be used as evidence?

## Deferred Until Ontology / Taxonomy Graph Is Ready

Defer:

- entity extraction
- relationship inference
- alias resolution
- identity merge
- graph traversal
- graph-backed Q&A
- source-family expansion beyond current ingestion outputs
- route topology
- promotion from candidate extraction to canon
- statblock/corpus promotion lifecycle integration
- confidence scoring
- semantic ranking
- high-degree hub filtering
- cross-session reasoning
- durable graph node IDs as public UI contract
- treating summaries as answer evidence

The current contract should be graph-compatible, not graph-dependent.

## Non-Negotiable Invariants

1. Corpus markdown on disk remains the source of truth.
2. Agent Interaction consumes source artifacts, anchors, and units, not ingestion internals.
3. `displaySummary` is never evidence.
4. Every source-backed claim must have a source anchor and provenance.
5. Every unit must carry canon, lifecycle, evidence, authority, and visibility state.
6. Session-memory JSONL is derived memory, not automatically canon.
7. Frontmatter seed output is scaffold/candidate metadata, not automatically canon.
8. `corpus_impact` is diagnostic proof metadata, not narrative evidence.
9. No unified mutable knowledge store is introduced.
10. Taxonomy/ontology owns derived semantics, identity merge, alias resolution, and relationship inference.
11. The adapter may expose opaque locators, but Agent Interaction should not depend on raw paths or ingestion step names for semantics.
12. The contract must degrade cleanly when graph-backed retrieval does not exist.

## Minimal Implementation Steps For The Ingestion Adapter

1. Add shared contract types in a neutral place used by ingestion consumers.

Suggested names:

```text
SourceArtifact
SourceAnchor
SourceUnit
IngestionSourceBundle
OpaqueLocator
```

2. Add a recap-ingestion adapter function:

```ts
function buildIngestionSourceBundle(input: RecapIngestionResult): IngestionSourceBundle
```

or Python equivalent:

```python
def build_ingestion_source_bundle(result: RecapIngestionResult) -> IngestionSourceBundle:
    ...
```

3. Map each produced artifact into a `SourceArtifact`.

At minimum:

- normalized recap
- breadcrumbed recap
- frontmatter seed
- session-memory JSONL
- session-memory meta if present
- corpus impact proof if present

4. Add document-level anchors for each artifact.

5. Add fine-grained anchors only when stable IDs or ranges already exist.

Do not invent fake precision.

6. Add `SourceUnit`s for displayable things:

- recap document
- recap sections if known
- breadcrumb/reference projections if known
- session-memory units
- frontmatter seed fields
- corpus impact proof rows

7. Keep raw text out of the default payload.

Use locators and small display fields.

8. Add validation.

Fail or warn when:

- a source-backed unit lacks source anchor
- a unit lacks lifecycle/canon/evidence/authority/visibility state
- diagnostic metadata is labeled as source evidence
- frontmatter seed is labeled as played canon
- session-memory JSONL is treated as promoted canon
- raw absolute file paths leak into display fields

9. Agent Interaction reads only the bundle.

No direct reads from `_normalized/`, `_breadcrumbed/`, `.records_meta.jsonl`, or `corpus_impact`.

10. Later, graph-backed retrieval can produce the same `SourceUnit` shape.

That is the replacement path.

## Current Output Warnings / Ambiguities

### Normalized recap may be source truth, but it is still system-shaped

Normalized recap markdown can be treated as the current source-backed recap artifact, but the adapter should preserve that it is system-derived from ingestion, not raw table transcript.

Use:

```text
canonState: played_canon
authorityState: system_derived
evidenceRole: source_evidence
```

### Breadcrumbed recap is partly source and partly navigation

Breadcrumbed markdown may contain source text plus navigation tags. Do not make the whole artifact `source_evidence` blindly.

Use navigation roles for breadcrumb-specific projections unless anchored to source spans.

### Frontmatter seed is easy to over-trust

Frontmatter seed metadata often feels authoritative because it is structured. It should default to planning scaffold or candidate extraction, not played canon.

### Session-memory JSONL is not canon by itself

It is derived memory. It may point back to source evidence, but the JSONL record is not itself the canonical campaign source.

### `corpus_impact` is proof of operation, not proof of fiction

It can prove ingestion wrote or touched files. It does not prove a narrative claim is true.

### Stable source anchors may not exist for every artifact yet

If line ranges, headings, or unit IDs are missing, use coarse document anchors and mark precision honestly.

Do not invent line precision.

### Surface labels and ontology terms must stay separated

Agent Interaction can display “recap,” “memory,” “reference,” “proof,” or “statblock” language. The adapter should still preserve source/evidence/lifecycle semantics underneath.

## Practical Recommendation

Implement the adapter as a one-way read model:

```text
RecapIngestionResult -> IngestionSourceBundle
```

Do not make it a store.

Do not make it mutable.

Do not make it graph-specific.

Do not let Agent Interaction bypass it.

This gives Agent Interaction a stable consumer contract now while allowing the ontology/taxonomy graph to later produce richer `SourceUnit`s with the same envelope.
