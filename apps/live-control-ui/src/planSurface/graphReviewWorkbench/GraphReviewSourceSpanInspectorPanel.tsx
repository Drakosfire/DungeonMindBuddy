import type { GraphReviewContextualDelta, GraphReviewLaneObjectRef } from "./graphReviewDeltaTypes";
import { buildEvidenceSelectionForDelta } from "./graphReviewEvidenceSelectionUtils";
import type { GraphReviewSourceSpanDeltaPresentation } from "./graphReviewSourceSpanOverlayUtils";
import { statusLabelForSourceSpan } from "./graphReviewSourceSpanOverlayUtils";

interface GraphReviewSourceSpanInspectorPanelProps {
  selectedSourceSpanId: string | null;
  presentation?: GraphReviewSourceSpanDeltaPresentation | null;
  onSelectEvidenceDelta?: (deltaId: string) => void;
  selectedEvidenceDeltaId?: string | null;
}

function formatRef(ref: GraphReviewLaneObjectRef): string {
  const score = typeof ref.matchScore === "number" ? ` · score ${ref.matchScore.toFixed(2)}` : "";
  return `${ref.laneRole}:${ref.objectKind}:${ref.objectId}${ref.label ? ` · ${ref.label}` : ""}${score}`;
}

function UniqueList({ values, emptyLabel = "—" }: { values: string[]; emptyLabel?: string }) {
  if (!values.length) return <span>{emptyLabel}</span>;
  return (
    <ul className="graph-review-source-span-inspector-list">
      {values.map((value) => (
        <li key={value}>{value}</li>
      ))}
    </ul>
  );
}

function DeltaDetails({
  delta,
  onSelectEvidenceDelta,
  selectedEvidenceDeltaId,
}: {
  delta: GraphReviewContextualDelta;
  onSelectEvidenceDelta?: (deltaId: string) => void;
  selectedEvidenceDeltaId?: string | null;
}) {
  const evidenceSelection = buildEvidenceSelectionForDelta(delta);
  const canInspectEvidence = evidenceSelection.status !== "no_object_ref";
  return (
    <article className="graph-review-source-span-delta-list-item" data-selected-evidence={delta.deltaId === selectedEvidenceDeltaId ? "true" : "false"}>
      <header>
        <strong>{delta.status}</strong>
        <span>{delta.objectKind}</span>
      </header>
      <p>{delta.summary}</p>
      <dl className="graph-review-source-span-inspector-grid">
        <div>
          <dt>Lane refs</dt>
          <dd><UniqueList values={delta.laneObjectRefs.map(formatRef)} /></dd>
        </div>
        <div>
          <dt>Source span refs</dt>
          <dd><UniqueList values={delta.sourceSpanRefIds} /></dd>
        </div>
        <div>
          <dt>Evidence refs</dt>
          <dd><UniqueList values={delta.evidenceRefIds} /></dd>
        </div>
        <div>
          <dt>Comparator reason</dt>
          <dd>{delta.comparatorReason || "—"}</dd>
        </div>
      </dl>
      {onSelectEvidenceDelta ? (
        <button
          className="graph-review-evidence-inspect-button"
          type="button"
          disabled={!canInspectEvidence}
          onClick={() => onSelectEvidenceDelta(delta.deltaId)}
        >
          Inspect gold/live evidence
        </button>
      ) : null}
    </article>
  );
}

export function GraphReviewSourceSpanInspectorPanel({
  selectedSourceSpanId,
  presentation = null,
  onSelectEvidenceDelta,
  selectedEvidenceDeltaId = null,
}: GraphReviewSourceSpanInspectorPanelProps) {
  if (!selectedSourceSpanId) {
    return (
      <aside className="graph-review-source-span-inspector-panel" aria-label="Source-span delta inspector">
        <p className="plan-surface-kicker">Source-span inspector</p>
        <p>Select a source-span row to inspect paragraph-level delta context.</p>
      </aside>
    );
  }

  if (!presentation) {
    return (
      <aside className="graph-review-source-span-inspector-panel" aria-label="Source-span delta inspector">
        <p className="plan-surface-kicker">Source-span inspector</p>
        <p>No source-span delta presentation is available for this span.</p>
      </aside>
    );
  }

  return (
    <aside className="graph-review-source-span-inspector-panel" aria-label="Source-span delta inspector">
      <p className="plan-surface-kicker">Source-span inspector</p>
      <header>
        <div>
          <h3>{presentation.sourceSpanRefId}</h3>
          <p>Read-only paragraph-level delta context for the selected live source span.</p>
        </div>
        <span data-delta-status={presentation.status}>{statusLabelForSourceSpan(presentation.status)}</span>
      </header>
      <dl className="graph-review-source-span-inspector-grid">
        <div><dt>Status</dt><dd>{statusLabelForSourceSpan(presentation.status)}</dd></div>
        <div><dt>Source span id</dt><dd>{presentation.sourceSpanRefId}</dd></div>
        <div><dt>Ordinal</dt><dd>{presentation.sourceSpan?.ordinal ?? "—"}</dd></div>
        <div><dt>Text excerpt</dt><dd>{presentation.sourceSpanText || "—"}</dd></div>
        <div><dt>Live node ids</dt><dd><UniqueList values={presentation.liveNodeIds} /></dd></div>
        <div><dt>Evidence refs</dt><dd><UniqueList values={presentation.evidenceRefIds} /></dd></div>
        <div><dt>Comparator reasons</dt><dd><UniqueList values={presentation.comparatorReasons} /></dd></div>
      </dl>
      <p className="graph-review-source-span-inspector-note">Display summaries are navigation aids, not evidence.</p>
      <div className="graph-review-source-span-delta-list">
        {presentation.deltas.length ? presentation.deltas.map((delta) => (
          <DeltaDetails
            key={delta.deltaId}
            delta={delta}
            onSelectEvidenceDelta={onSelectEvidenceDelta}
            selectedEvidenceDeltaId={selectedEvidenceDeltaId}
          />
        )) : <p>No contextual deltas are attached to this source span.</p>}
      </div>
    </aside>
  );
}
