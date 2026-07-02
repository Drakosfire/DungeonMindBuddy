import type { GraphProjectionNodeView } from "../../api/types";
import type { GraphReviewContextualDelta, GraphReviewLaneObjectRef } from "./graphReviewDeltaTypes";
import type { GraphReviewNodeDeltaPresentation } from "./graphReviewPillOverlayUtils";
import { buildEvidenceSelectionForDelta } from "./graphReviewEvidenceSelectionUtils";
import { statusLabelForPill } from "./graphReviewPillOverlayUtils";

interface GraphReviewDeltaInspectorPanelProps {
  selectedNodeId: string | null;
  selectedNode?: GraphProjectionNodeView | null;
  presentation?: GraphReviewNodeDeltaPresentation | null;
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
    <ul className="graph-review-delta-inspector-list">
      {values.map((value) => (
        <li key={value}>{value}</li>
      ))}
    </ul>
  );
}

function DeltaDetails({
  delta,
  primary,
  onSelectEvidenceDelta,
  selectedEvidenceDeltaId,
}: {
  delta: GraphReviewContextualDelta;
  primary: boolean;
  onSelectEvidenceDelta?: (deltaId: string) => void;
  selectedEvidenceDeltaId?: string | null;
}) {
  const matchScores = delta.laneObjectRefs
    .map((ref) => ref.matchScore)
    .filter((score): score is number => typeof score === "number");
  const evidenceSelection = buildEvidenceSelectionForDelta(delta);
  const canInspectEvidence = evidenceSelection.status !== "no_object_ref";
  return (
    <article className="graph-review-delta-inspector-delta" data-primary={primary ? "true" : "false"} data-selected-evidence={delta.deltaId === selectedEvidenceDeltaId ? "true" : "false"}>
      <header>
        <strong>{primary ? "Primary delta" : "Related delta"}</strong>
        <span>{delta.status}</span>
      </header>
      <p>{delta.summary}</p>
      <dl className="graph-review-delta-inspector-grid">
        <div>
          <dt>Lane refs</dt>
          <dd>
            <UniqueList values={delta.laneObjectRefs.map(formatRef)} />
          </dd>
        </div>
        <div>
          <dt>Match scores</dt>
          <dd>{matchScores.length ? matchScores.map((score) => score.toFixed(2)).join(", ") : "—"}</dd>
        </div>
        <div>
          <dt>Source span refs</dt>
          <dd>
            <UniqueList values={delta.sourceSpanRefIds} />
          </dd>
        </div>
        <div>
          <dt>Evidence refs</dt>
          <dd>
            <UniqueList values={delta.evidenceRefIds} />
          </dd>
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

export function GraphReviewDeltaInspectorPanel({
  selectedNodeId,
  selectedNode = null,
  presentation = null,
  onSelectEvidenceDelta,
  selectedEvidenceDeltaId = null,
}: GraphReviewDeltaInspectorPanelProps) {
  if (!selectedNodeId) {
    return (
      <aside className="graph-review-delta-inspector-panel" aria-label="Selected graph node delta inspector">
        <p className="plan-surface-kicker">Delta inspector</p>
        <p>Select a graph pill to inspect its contextual delta.</p>
      </aside>
    );
  }

  const nodeLabel = selectedNode?.label ?? presentation?.label ?? selectedNodeId;

  if (!presentation) {
    return (
      <aside className="graph-review-delta-inspector-panel" aria-label="Selected graph node delta inspector">
        <p className="plan-surface-kicker">Delta inspector</p>
        <h3>{nodeLabel}</h3>
        <p>No contextual delta is available for this selected live node yet.</p>
      </aside>
    );
  }

  const primaryDelta = presentation.primaryDelta ?? presentation.deltas[0] ?? null;

  return (
    <aside className="graph-review-delta-inspector-panel" aria-label="Selected graph node delta inspector">
      <p className="plan-surface-kicker">Delta inspector</p>
      <header>
        <div>
          <h3>{nodeLabel}</h3>
          <p>Read-only comparison status for the selected live graph node.</p>
        </div>
        <span data-delta-status={presentation.status}>{statusLabelForPill(presentation.status)}</span>
      </header>
      <dl className="graph-review-delta-inspector-grid">
        <div>
          <dt>Status</dt>
          <dd>{statusLabelForPill(presentation.status)}</dd>
        </div>
        <div>
          <dt>Summary</dt>
          <dd>{primaryDelta?.summary ?? "—"}</dd>
        </div>
        <div>
          <dt>Node id</dt>
          <dd>{selectedNodeId}</dd>
        </div>
        <div>
          <dt>Node label</dt>
          <dd>{nodeLabel}</dd>
        </div>
        <div>
          <dt>Source span refs</dt>
          <dd>
            <UniqueList values={presentation.sourceSpanRefIds} />
          </dd>
        </div>
        <div>
          <dt>Evidence refs</dt>
          <dd>
            <UniqueList values={presentation.evidenceRefIds} />
          </dd>
        </div>
      </dl>
      <p className="graph-review-delta-inspector-note">Display summaries are navigation aids, not evidence.</p>
      <div className="graph-review-delta-inspector-deltas">
        {presentation.deltas.map((delta) => (
          <DeltaDetails
            key={delta.deltaId}
            delta={delta}
            primary={delta.deltaId === primaryDelta?.deltaId}
            onSelectEvidenceDelta={onSelectEvidenceDelta}
            selectedEvidenceDeltaId={selectedEvidenceDeltaId}
          />
        ))}
      </div>
    </aside>
  );
}
