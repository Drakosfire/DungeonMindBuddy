# Graph Memory / Plan Surface Consumer Alignment

## Purpose

This report re-anchors the Ontology / Taxonomy ladder after Session-Memory Sentence-Unit Materializer v0 and records `/plan` as the first named future consumer for graph-memory derived structures.

This is a docs/report-only alignment checkpoint. It does not change `/plan`, live-control UI behavior, retrieval, graph extraction, materializers, prompts, or corpus files.

## Current Ladder State

The ladder has completed:

1. Baseline case freeze
2. Taxonomy Registry v0
3. Ontology IR Schema v0
4. Ontology IR Validation Rules v0
5. Synthetic Deterministic Materializer v0
6. Materializer Report CLI v0
7. Real-Structure Materialization Gate v0
8. Session-Memory Sentence-Unit Materializer v0

The ladder can now materialize explicit session-memory JSONL sentence/source-unit records into a diagnostic candidate GraphBundle. The default validator still uses a tiny synthetic fixture for the baseline materializer path. No broad campaign/corpus materialization has begun, no production retrieval behavior has changed, no graph output influences `/plan` or live retrieval yet, no LLM extraction has begun, no alias/entity/relationship inference has begun, and no corpus mutation has happened.

## Current `/plan` Consumer Shape

`/plan` remains a consumer, not the owner of graph memory or taxonomy. It owns projection UI, reference-chip display, tool workflows, user interaction, editing affordances, and fallback to current live indexes.

The UI should not become graph-aware. The UI should ask for source-backed, lifecycle-aware units through a stable adapter.

The current live-index path remains the fallback until graph-assisted retrieval is measured in shadow mode and explicitly promoted.

## Adapter Boundary

The expected adapter vocabulary is:

`source artifact -> source anchor -> source unit`

The ontology ladder owns controlled vocabulary, graph-memory record shapes, provenance, evidence role semantics, lifecycle state semantics, validation, reporting, and future shadow retrieval explanations.

The adapter boundary owns mapping graph/taxonomy concepts into projection kinds, returning safe source locators, preserving lifecycle/provenance metadata, and degrading when graph data is absent or uncertain.

| Concern | Owned by `/plan` | Owned by ontology ladder | Adapter contract |
|---|---|---|---|
| Projection UI | Yes | No | Receives projection-ready source units |
| Reference chips | Yes | No | Chips carry opaque handles, not graph internals |
| Taxonomy vocabulary | No | Yes | Adapter maps graph terms to projection kinds |
| Alias resolution | No | Yes, later | Adapter may expose candidates separately from matches |
| Lifecycle semantics | Display only | Yes | Adapter returns lifecycle/provenance fields |
| Source evidence | Display/cite | Yes | Adapter returns source anchors and evidence roles |
| Graph traversal | No | Later shadow mode | Adapter returns bounded expansions with explanations |
| Current fallback | Yes | No | Live-index fallback remains valid |

## Reference Type Mapping

| Current `/plan` ref type | Current source | Likely ontology/taxonomy concept | Alignment note |
|---|---|---|---|
| `npc` | live NPC index | `entity_kind:npc` | UI ref type is an adapter key, not ontology ownership |
| `location` | live location index | `entity_kind:location` / `entity_kind:sublocation` / route metadata | Avoid forcing UI string to carry taxonomy detail |
| `statblock` | live statblock index / generated workflow | generated content + future source artifact / lifecycle state | Needs draft/accepted/promoted/indexed lifecycle distinction |
| `roll-table` | live roll-table index | support/source artifact, not necessarily entity | Needs source kind and projection kind mapping |
| session-memory unit | graph materializer output | `entity_kind:source_unit` plus `source_kind:session_memory_record` | First graph-backed source-unit candidate |

## Proposed Graph-Backed Source Unit Shape

```typescript
type GraphBackedSourceUnit = {
  adapterKey: string;
  refId: string;
  label: string;
  displaySummary?: string;
  fields?: Record<string, string | number | boolean | null>;
  sourceAnchor: {
    sourceId: string;
    sourceKind: string;
    sourceLayer: string;
    sourcePath?: string;
    sourceReference?: string;
    lineStart?: number;
    lineEnd?: number;
    anchor?: string;
  };
  evidenceRole: string;
  authorityState: string;
  visibilityState: string;
  lifecycleState: string;
  provenance: Array<{
    provenanceId: string;
    sourceRefs: unknown[];
  }>;
  graphDiagnostics?: {
    nodeId?: string;
    edgeIds?: string[];
    validationIssues?: Array<{ severity: string; code: string }>;
    expansionReason?: string;
  };
};
```

`displaySummary` is navigation/display prose, not source evidence. Source-backed claims must point through source anchors. Lifecycle state must be displayed, not flattened into a generic known-fact state. Graph diagnostics are optional and should be bounded by limits, relation filters, source-family filters, and explanation metadata.

## Lifecycle Requirements

The `/plan` consumer must be able to distinguish at least:

- played truth
- GM prep
- rumor
- generated candidate
- dismissed candidate
- diagnostic-only extraction
- accepted-to-combat
- promoted-to-corpus
- indexed
- promoted canon

The ladder should not collapse these into one "known fact" state.

Some of these may already map to existing taxonomy terms. Others may require future taxonomy additions or adapter-level substate fields. This PR does not add those terms unless the active rung explicitly permits it.

## Evidence vs Summary

Graph summaries and display summaries are not source evidence. They may help navigation in a drawer or planning workspace, but they are not admissible proof of a source-backed claim.

Every source-backed adapter response should include source anchors, evidence roles, authority state, visibility state, lifecycle state, and provenance. Reports should flag records where summary text exists without source refs or where summary text is treated as `source_evidence`.

## Mismatch Risk Register

### Risk A — Taxonomy drift between UI strings and graph categories

`/plan` uses operational ref types such as `npc`, `location`, `statblock`, and `roll-table`. The graph taxonomy may need richer categories.

Mitigation: ontology owns taxonomy; `/plan` owns adapter keys and display projections. Add an explicit adapter map before graph-backed `/plan` projection.

Detection: report any graph output that cannot map to a known projection kind.

### Risk B — Session-memory source units are too narrow for `/plan`

The first admitted materializer only produces source-document/source-unit graph records from session-memory JSONL. `/plan` will also need dossiers, statblocks, roll tables, generated drafts, and corpus source surfaces.

Mitigation: keep this rung narrow, but list future source families and evidence requirements before adding them.

Detection: consumer-alignment report tracks missing source families and whether each has source refs, lifecycle states, and projection fields.

### Risk C — Graph summaries become tempting UI evidence

The drawer wants concise summaries, but graph summaries are not source evidence.

Mitigation: adapter returns both `displaySummary` and source anchors. Schema and docs must state that summary text is navigational, not admissible evidence.

Detection: validation/reporting flags records where summary exists without source refs or where summary is used as `source_evidence`.

### Risk D — Lifecycle collapse

Planning UX encourages moving between prep, generated content, and canon. This can flatten rumor, prep, generated candidate, diagnostic extraction, and played truth.

Mitigation: lifecycle/provenance fields are first-class in every adapter response.

Detection: report records missing lifecycle, authority, evidence role, or visibility state.

### Risk E — Identity merge pressure leaks into UI

Reference chips create pressure to “just find the thing,” but identity/alias logic belongs to graph memory.

Mitigation: adapter returns matched entity and candidate aliases separately. `/plan` may display candidates but does not merge identities.

Detection: no adapter response may return a merged identity without provenance and lifecycle/confidence metadata.

### Risk F — Graph depth overwhelms the drawer

The live drawer works because it is bounded and fast.

Mitigation: future graph-backed adapter must support limits, relation filters, source-family filters, and explanation metadata.

Detection: shadow reports track expansion count, source-family count, high-degree hubs, and rejected expansions.

## Deferred Alignments

The following remain intentionally unaligned until shadow retrieval:

- `/plan` runtime implementation
- live-index replacement
- graph-backed reference resolution
- graph traversal in the projection drawer
- alias/identity merge behavior
- statblock promotion lifecycle integration
- generated-content writeback
- corpus writer integration
- player/privacy filtering beyond current metadata
- production retrieval behavior

These should not be implemented until the ladder has deterministic reports and shadow retrieval fixtures proving value and safety.

## Acceptance Notes

This report answers the consumer-alignment questions before graph-backed `/plan` consumption begins: `/plan` is a future consumer, the ontology ladder owns graph semantics, the adapter boundary owns projection-safe mapping, lifecycle/provenance remain first-class, display summaries are not evidence, current reference types have an explicit mapping, and mismatch risks have mitigations and detection paths.
