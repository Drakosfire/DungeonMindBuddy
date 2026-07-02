import type { GraphReviewVariantInventoryIndex } from "./graphReviewVariantReferenceUtils";

interface Props { index: GraphReviewVariantInventoryIndex; selectedRowId: string | null; onSelectRow: (rowId: string | null) => void; }

export function GraphReviewVariantInventoryPanel({ index, selectedRowId, onSelectRow }: Props) {
  return <section className="graph-review-variant-inventory-panel" aria-label="Variant/live inventory comparison">
    <header><h4>Variant/live inventory comparison</h4><p className="graph-review-variant-note">Variant/live inventory comparison is label-based navigation only. Gold/live deltas remain the correctness model.</p></header>
    {index.warnings.map((warning) => <p key={warning} className="graph-review-variant-warning">{warning}</p>)}
    <div className="graph-review-variant-inventory-count-grid">
      {(["variant_only", "live_only", "kind_label_overlap", "label_overlap", "comparator_uncertain"] as const).map((status) => <span key={status}>{status === "comparator_uncertain" ? "uncertain" : status} {index.countsByStatus[status]}</span>)}
    </div>
    {selectedRowId ? <button type="button" onClick={() => onSelectRow(null)}>Clear inventory selection</button> : null}
    {index.rows.length === 0 ? <p>Select a manual review variant to compare its inventory against the selected live run.</p> : null}
    <div className="graph-review-variant-inventory-list">
      {index.rows.map((row) => <button type="button" key={row.rowId} className={`graph-review-variant-inventory-row${row.rowId === selectedRowId ? " is-selected" : ""}`} onClick={() => onSelectRow(row.rowId)}>
        <span className="graph-review-variant-inventory-status">{row.status}</span><span>{row.objectKind}</span><strong>{row.label}</strong><span>{row.variantNode?.node_id ?? row.variantEdge?.edge_id ?? "—"}</span><span>{row.liveObjects.map((live) => live.object_id).join(", ") || "—"}</span><span>{row.summary}</span>
      </button>)}
    </div>
  </section>;
}
