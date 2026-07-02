import type { ManualReviewBedDetail, ManualReviewBedSummary } from "../../api/types";
import type { GraphReviewManualVariantLaneView, GraphReviewManualVariantSelection } from "./graphReviewVariantReferenceUtils";

interface GraphReviewVariantLanePanelProps {
  campaignId: string;
  sessionId: string;
  beds: ManualReviewBedSummary[];
  bedsStatus: "idle" | "loading" | "ready" | "error";
  bedsError?: string | null;
  selectedBed: ManualReviewBedDetail | null;
  selectedLaneView: GraphReviewManualVariantLaneView | null;
  selectedVariant: GraphReviewManualVariantSelection | null;
  onSelectBedId: (bedId: string | null) => void;
  onSelectVariantName: (variantName: string | null) => void;
}

function rankBed(bed: ManualReviewBedSummary, campaignId: string, sessionId: string): number {
  if (bed.campaign_id === campaignId && bed.session_id === sessionId) return 0;
  if (bed.campaign_id === campaignId) return 1;
  if (!bed.campaign_id && !bed.session_id) return 2;
  return 3;
}

function formatRecord(record: Record<string, number>): string {
  const entries = Object.entries(record ?? {});
  return entries.length ? entries.map(([key, value]) => `${key}: ${value}`).join(" · ") : "—";
}

export function GraphReviewVariantLanePanel({
  campaignId,
  sessionId,
  beds,
  bedsStatus,
  bedsError = null,
  selectedBed,
  selectedLaneView,
  selectedVariant,
  onSelectBedId,
  onSelectVariantName,
}: GraphReviewVariantLanePanelProps) {
  const sortedBeds = [...beds].sort((a, b) => rankBed(a, campaignId, sessionId) - rankBed(b, campaignId, sessionId) || a.bed_id.localeCompare(b.bed_id));
  const hasExactMatch = beds.some((bed) => bed.campaign_id === campaignId && bed.session_id === sessionId);
  const selectedSummary = beds.find((bed) => bed.bed_id === selectedVariant?.bedId) ?? null;
  const mismatch = selectedSummary && rankBed(selectedSummary, campaignId, sessionId) === 3;
  const variants = selectedBed?.variant_names ?? selectedSummary?.variant_names ?? [];

  return (
    <section className="graph-review-variant-lane-panel" aria-label="Manual variant reference lane">
      <header>
        <p className="plan-surface-kicker">Reference lane</p>
        <h4>Manual variant reference lane</h4>
        <p>Manual review variants are read-only reference artifacts for inventory overlap navigation.</p>
      </header>
      {bedsStatus === "loading" ? <p>Loading manual review beds…</p> : null}
      {bedsStatus === "error" ? <p className="graph-review-error">{bedsError ?? "Failed to load manual review beds."}</p> : null}
      {bedsStatus === "ready" && beds.length === 0 ? <p>No manual review beds are available for this session.</p> : null}
      {beds.length > 0 && !hasExactMatch ? <p className="graph-review-variant-warning">Manual review beds exist, but none advertise this campaign/session. You may still select one manually.</p> : null}
      {mismatch ? <p className="graph-review-variant-warning">Selected bed advertises {selectedSummary?.campaign_id ?? "unknown"} / {selectedSummary?.session_id ?? "unknown"}, not {campaignId} / {sessionId}.</p> : null}
      <div className="graph-review-variant-selector-grid">
        <label>Bed<select value={selectedVariant?.bedId ?? ""} onChange={(event) => onSelectBedId(event.target.value || null)}><option value="">Select bed…</option>{sortedBeds.map((bed) => <option key={bed.bed_id} value={bed.bed_id}>{bed.bed_id} · {bed.campaign_id ?? "unknown"}/{bed.session_id ?? "unknown"}</option>)}</select></label>
        <label>Variant<select value={selectedVariant?.variantName ?? ""} onChange={(event) => onSelectVariantName(event.target.value || null)} disabled={!variants.length}><option value="">Select variant…</option>{variants.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>
      </div>
      {selectedLaneView ? <article className="graph-review-variant-lane-card">
        <h5>{selectedLaneView.lane.label}</h5>
        <dl className="graph-review-lane-meta">
          <div><dt>Bed id</dt><dd>{selectedLaneView.bed.bed_id}</dd></div><div><dt>Variant</dt><dd>{selectedLaneView.variant.variant_name}</dd></div>
          <div><dt>Campaign</dt><dd>{selectedLaneView.lane.campaignId}</dd></div><div><dt>Session</dt><dd>{selectedLaneView.lane.sessionId}</dd></div>
          <div><dt>Nodes</dt><dd>{selectedLaneView.variant.node_count}</dd></div><div><dt>Edges</dt><dd>{selectedLaneView.variant.edge_count}</dd></div>
          <div><dt>Cost estimate</dt><dd>{selectedLaneView.variant.cost_usd ?? "—"}</dd></div><div><dt>Model</dt><dd>{selectedLaneView.bed.model_id ?? "—"}</dd></div>
          <div><dt>Generated</dt><dd>{selectedLaneView.bed.generated_at ?? "—"}</dd></div><div><dt>Node kinds</dt><dd>{formatRecord(selectedLaneView.variant.node_kinds)}</dd></div>
          <div><dt>Edge predicates</dt><dd>{formatRecord(selectedLaneView.variant.edge_predicates)}</dd></div><div><dt>Gold summary</dt><dd>{Object.keys(selectedLaneView.variant.gold_comparison ?? {}).length ? "Available" : "—"}</dd></div>
        </dl>
      </article> : null}
    </section>
  );
}
