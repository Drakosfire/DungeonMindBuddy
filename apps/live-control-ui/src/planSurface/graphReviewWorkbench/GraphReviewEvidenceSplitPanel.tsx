import type { GoldReviewEvidenceDiffResponse, GoldReviewEvidenceResolvedRef } from "../../api/types";
import { lineRangeLabel } from "../graphPreview/graphPreviewUtils";
import type { GraphReviewEvidenceSelection } from "./graphReviewEvidenceSelectionUtils";

type EvidenceStatus = "idle" | "loading" | "ready" | "error" | "unavailable";

interface GraphReviewEvidenceSplitPanelProps {
  selection: GraphReviewEvidenceSelection;
  evidence: GoldReviewEvidenceDiffResponse | null;
  status: EvidenceStatus;
  errorMessage?: string | null;
  onClearSelection?: () => void;
}

function payloadPreview(payload: Record<string, unknown>): string {
  const text = JSON.stringify(payload ?? {}, null, 2);
  return text.length > 500 ? `${text.slice(0, 500)}…` : text;
}

function RefList({ selection }: { selection: GraphReviewEvidenceSelection }) {
  const refs = selection.delta?.laneObjectRefs ?? [];
  if (!refs.length) return null;
  return (
    <ul className="graph-review-evidence-entry-list" aria-label="Local delta refs">
      {refs.map((ref) => (
        <li className="graph-review-evidence-entry" key={`${ref.laneRole}-${ref.objectKind}-${ref.objectId}`}>
          <strong>{ref.laneRole}</strong> {ref.objectKind} · <code>{ref.objectId}</code>
          {ref.label ? <span> · {ref.label}</span> : null}
        </li>
      ))}
    </ul>
  );
}

function EvidenceEntry({ evidence }: { evidence: GoldReviewEvidenceResolvedRef }) {
  return (
    <li className="graph-review-evidence-entry">
      <header>
        <strong>{evidence.label ?? evidence.source_anchor_id ?? evidence.source_span_ref_id ?? "Evidence ref"}</strong>
        <span>{lineRangeLabel(evidence.line_start, evidence.line_end)}</span>
      </header>
      <dl>
        <div><dt>Source anchor id</dt><dd>{evidence.source_anchor_id ? <code>{evidence.source_anchor_id}</code> : "—"}</dd></div>
        <div><dt>Source span ref id</dt><dd>{evidence.source_span_ref_id ? <code>{evidence.source_span_ref_id}</code> : "—"}</dd></div>
        <div><dt>Preview snippet</dt><dd>{evidence.preview_snippet || "—"}</dd></div>
        <div><dt>Paragraph text</dt><dd>{evidence.paragraph_text || "—"}</dd></div>
      </dl>
    </li>
  );
}

function EvidenceSideCard({
  title,
  side,
  sideName,
}: {
  title: string;
  side: GoldReviewEvidenceDiffResponse["gold"] | GoldReviewEvidenceDiffResponse["live"];
  sideName: "gold" | "live";
}) {
  if (!side) {
    return (
      <article className="graph-review-evidence-side-card" data-side={sideName}>
        <header><p className="plan-surface-kicker">{title}</p><h4>No live evidence side.</h4></header>
        <p className="graph-review-evidence-empty">No live evidence side.</p>
      </article>
    );
  }

  return (
    <article className="graph-review-evidence-side-card" data-side={sideName}>
      <header>
        <p className="plan-surface-kicker">{title}</p>
        <h4>{side.label || side.object_id}</h4>
      </header>
      <dl>
        <div><dt>Object id</dt><dd><code>{side.object_id}</code></dd></div>
        <div><dt>Object kind</dt><dd>{side.object_kind}</dd></div>
        <div><dt>Label</dt><dd>{side.label || "—"}</dd></div>
        <div><dt>Summary</dt><dd>{side.summary || "—"}</dd></div>
        <div><dt>Payload preview</dt><dd><pre>{payloadPreview(side.payload)}</pre></dd></div>
      </dl>
      {side.evidence.length ? (
        <ul className="graph-review-evidence-entry-list" aria-label={`${title} evidence refs`}>
          {side.evidence.map((entry, index) => (
            <EvidenceEntry evidence={entry} key={`${side.object_id}-${index}`} />
          ))}
        </ul>
      ) : (
        <p className="graph-review-evidence-empty">No evidence refs on this side.</p>
      )}
    </article>
  );
}

export function GraphReviewEvidenceSplitPanel({
  selection,
  evidence,
  status,
  errorMessage = null,
  onClearSelection,
}: GraphReviewEvidenceSplitPanelProps) {
  const hasSelection = Boolean(selection.delta);

  return (
    <section className="graph-review-evidence-split-panel" aria-label="Gold/live evidence split inspector">
      <header className="graph-review-evidence-split-header">
        <div>
          <p className="plan-surface-kicker">Gold/live evidence</p>
          <h3>Evidence split inspector</h3>
        </div>
        {hasSelection && onClearSelection ? <button type="button" onClick={onClearSelection}>Clear selection</button> : null}
      </header>

      {status === "idle" || !hasSelection ? (
        <p className="graph-review-evidence-empty">Select a delta, graph pill, or source-span attached delta to inspect gold/live evidence.</p>
      ) : null}

      {hasSelection && status === "unavailable" && selection.status === "live_only_no_gold" ? (
        <div className="graph-review-evidence-empty">
          <p>This live-only delta has no gold object reference, so there is no gold evidence side to fetch in this PR.</p>
          <p>{selection.delta?.summary}</p>
          <RefList selection={selection} />
        </div>
      ) : null}

      {hasSelection && status === "unavailable" && selection.status === "no_object_ref" ? (
        <div className="graph-review-evidence-empty">
          <p>This delta does not contain an inspectable object reference.</p>
          <p>{selection.reason}</p>
        </div>
      ) : null}

      {hasSelection && status === "unavailable" && selection.status === "unsupported_object_kind" ? (
        <div className="graph-review-evidence-empty">
          <p>{selection.reason}</p>
          <RefList selection={selection} />
        </div>
      ) : null}

      {status === "loading" ? <p className="graph-review-evidence-empty" role="status">Loading gold/live evidence…</p> : null}

      {status === "error" ? (
        <div className="graph-review-error" role="alert">
          <p>{errorMessage || "Failed to load gold/live evidence."}</p>
          <p>Selected query object: {selection.queryObjectKind ?? "—"} · {selection.queryObjectId ?? "—"}</p>
        </div>
      ) : null}

      {status === "ready" && evidence ? (
        <>
          <p className="graph-review-evidence-note">
            {evidence.matched ? "Matched live evidence" : "Closest or missing live evidence"}
            {typeof evidence.match_score === "number" ? ` · score ${evidence.match_score.toFixed(2)}` : ""}
          </p>
          <div className="graph-review-evidence-split-grid">
            <EvidenceSideCard title="Gold expected evidence" side={evidence.gold} sideName="gold" />
            <EvidenceSideCard title="Live produced evidence" side={evidence.live} sideName="live" />
          </div>
        </>
      ) : null}

      <p className="graph-review-evidence-note">Evidence text and summaries are review aids. Source artifacts remain authoritative.</p>
    </section>
  );
}
