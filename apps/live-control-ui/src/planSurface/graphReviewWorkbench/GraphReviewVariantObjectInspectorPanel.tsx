import type { GraphReviewVariantInventoryRow } from "./graphReviewVariantReferenceUtils";

interface Props { selectedRow: GraphReviewVariantInventoryRow | null; }

function preview(value: unknown): string {
  if (value == null) return "—";
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > 220 ? `${text.slice(0, 220)}…` : text;
}
function list(values: string[]): string { return values.length ? values.join(" · ") : "—"; }
function liveCandidates(row: GraphReviewVariantInventoryRow): string { return row.liveObjects.length ? row.liveObjects.map((live) => `${live.object_kind}:${live.object_id}`).join(" · ") : "—"; }

export function GraphReviewVariantObjectInspectorPanel({ selectedRow }: Props) {
  return <section className="graph-review-variant-object-inspector-panel" aria-label="Variant object inspector">
    <header><h4>Variant object inspector</h4><p className="graph-review-variant-note">Manual review variant objects are reference artifacts. This inspector is read-only and does not promote canon.</p></header>
    {!selectedRow ? <p>Select a variant/live inventory row to inspect reference-lane object details.</p> : null}
    {selectedRow?.variantNode ? <dl className="graph-review-variant-object-grid">
      <div><dt>Node id</dt><dd>{selectedRow.variantNode.node_id}</dd></div><div><dt>Label</dt><dd>{selectedRow.variantNode.label}</dd></div>
      <div><dt>Node type</dt><dd>{selectedRow.variantNode.node_type}</dd></div><div><dt>Pass name</dt><dd>{selectedRow.variantNode.pass_name ?? "—"}</dd></div>
      <div><dt>Description</dt><dd>{selectedRow.variantNode.description ?? "—"}</dd></div><div><dt>Confidence</dt><dd>{selectedRow.variantNode.confidence ?? "—"}</dd></div>
      <div><dt>Importance</dt><dd>{selectedRow.variantNode.importance ?? "—"}</dd></div><div><dt>Corpus ref</dt><dd>{preview(selectedRow.variantNode.corpus_ref)}</dd></div>
      <div><dt>Evidence span ids</dt><dd>{list(selectedRow.evidenceSpanIds)}</dd></div><div><dt>Anchor quotes</dt><dd>{list(selectedRow.anchorQuotes)}</dd></div>
      <div><dt>Live candidates</dt><dd>{liveCandidates(selectedRow)}</dd></div>
    </dl> : null}
    {selectedRow?.variantEdge ? <dl className="graph-review-variant-object-grid">
      <div><dt>Edge id</dt><dd>{selectedRow.variantEdge.edge_id}</dd></div><div><dt>From node / label</dt><dd>{selectedRow.variantEdge.from_node_id} / {selectedRow.variantEdge.from_label ?? "—"}</dd></div>
      <div><dt>To node / label</dt><dd>{selectedRow.variantEdge.to_node_id} / {selectedRow.variantEdge.to_label ?? "—"}</dd></div><div><dt>Relationship type</dt><dd>{selectedRow.variantEdge.relationship_type}</dd></div>
      <div><dt>Predicate family</dt><dd>{selectedRow.variantEdge.predicate_family ?? "—"}</dd></div><div><dt>Confidence</dt><dd>{selectedRow.variantEdge.confidence ?? "—"}</dd></div>
      <div><dt>Evidence span ids</dt><dd>{list(selectedRow.evidenceSpanIds)}</dd></div><div><dt>Anchor quotes</dt><dd>{list(selectedRow.anchorQuotes)}</dd></div><div><dt>Live candidates</dt><dd>{liveCandidates(selectedRow)}</dd></div>
    </dl> : null}
    {selectedRow && !selectedRow.variantNode && !selectedRow.variantEdge ? <dl className="graph-review-variant-object-grid">
      <div><dt>Live object id</dt><dd>{selectedRow.liveObjects[0]?.object_id ?? "—"}</dd></div><div><dt>Object kind</dt><dd>{selectedRow.liveObjects[0]?.object_kind ?? selectedRow.objectKind}</dd></div>
      <div><dt>Label</dt><dd>{selectedRow.label}</dd></div><div><dt>Payload preview</dt><dd>{preview(selectedRow.liveObjects[0]?.payload)}</dd></div>
      <div><dt>Matched variant candidates</dt><dd>—</dd></div>
    </dl> : null}
  </section>;
}
