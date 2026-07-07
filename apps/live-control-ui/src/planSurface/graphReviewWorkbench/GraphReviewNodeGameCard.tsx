import type { GraphProjectionAdjacencyCandidate, GraphProjectionNodeView } from "../../api/types";
import { GraphReviewRelationshipChips } from "./GraphReviewRelationshipChips";
import {
  gameSummaryForNode,
  type GraphReviewSelectedNodeViewModel,
} from "./graphReviewSelectionUtils";

function isAuthoredNode(node: GraphProjectionNodeView): boolean {
  return Boolean(node.authored || node.source_domains.includes("authored_overlay"));
}

function laneBadgeCopy(viewModel: GraphReviewSelectedNodeViewModel): string {
  const parts: string[] = [];
  if (isAuthoredNode(viewModel.node)) {
    parts.push("Authored memory");
  }
  if (viewModel.laneRole === "gold") {
    parts.push("Gold Fixture");
  } else {
    parts.push("Live Run");
  }
  parts.push("read-only");
  return parts.join(" · ");
}

function friendlyVisibilityCopy(visibility: string): string {
  const normalized = visibility.trim().toLowerCase().replace(/_/g, " ");
  if (normalized === "gm private" || normalized === "gm") return "GM private";
  if (normalized === "table") return "Table";
  if (normalized === "player") return "Player";
  if (normalized === "character") return "Character";
  return visibility;
}

function statusCopy(viewModel: GraphReviewSelectedNodeViewModel): string {
  if (viewModel.status === "matched") return "Matched with the other lane.";
  if (viewModel.status === "gold_only")
    return "Present only in the gold fixture.";
  if (viewModel.status === "live_only")
    return "Present only in the selected live run.";
  if (viewModel.status === "comparator_uncertain")
    return "Comparator uncertain; inspect evidence if needed.";
  if (viewModel.status.startsWith("changed_"))
    return "Matched object with changed projected details.";
  return "No comparison status is available yet.";
}

function shouldShowReviewStatus(viewModel: GraphReviewSelectedNodeViewModel): boolean {
  return (
    viewModel.status !== "unknown" ||
    Boolean(viewModel.counterpart) ||
    Boolean(viewModel.deltaId)
  );
}

function NodeIdentityHeader({ viewModel }: { viewModel: GraphReviewSelectedNodeViewModel }) {
  const node = viewModel.node;
  return (
    <>
      <p className="plan-surface-kicker">{laneBadgeCopy(viewModel)}</p>
      <h4>{node.label}</h4>
      <p className="graph-review-game-kind">
        {[node.kind, node.role].filter(Boolean).join(" / ") || "Graph object"}
      </p>
    </>
  );
}

function NodeGameSummary({ node }: { node: GraphProjectionNodeView }) {
  return (
    <section aria-label="Campaign summary">
      <p>{gameSummaryForNode(node)}</p>
    </section>
  );
}

function NodeAliasMemoryNote({ node }: { node: GraphProjectionNodeView }) {
  if (!isAuthoredNode(node) && !node.aliases.length) return null;

  return (
    <section className="graph-review-alias-memory-note" aria-label="Aliases and memory">
      {isAuthoredNode(node) ? (
        <p className="graph-review-muted">This node includes authored memory.</p>
      ) : null}
      {node.aliases.length ? (
        <p>
          Also known as: {node.aliases.join(", ")}
        </p>
      ) : null}
      {node.source_anchor_text ? (
        <p className="graph-review-muted">
          Grounded from source phrase: “{node.source_anchor_text}”
        </p>
      ) : null}
      {node.visibility ? (
        <p className="graph-review-muted">
          Visibility: {friendlyVisibilityCopy(node.visibility)}
        </p>
      ) : null}
    </section>
  );
}

function NodeRelationshipSection({
  node,
  selectedEdgeId,
  onSelectRelationship,
}: {
  node: GraphProjectionNodeView;
  selectedEdgeId: string | null;
  onSelectRelationship: (relationship: GraphProjectionAdjacencyCandidate) => void;
}) {
  return (
    <section aria-label="Connected objects and relationships">
      <h5>Connected objects / relationships</h5>
      <GraphReviewRelationshipChips
        sourceLabel={node.label}
        relationships={node.adjacency}
        selectedEdgeId={selectedEdgeId}
        onSelect={onSelectRelationship}
      />
    </section>
  );
}

function NodeUsefulSurfacesSection({
  deltaId,
  onSelectEvidenceDelta,
}: {
  deltaId?: string | null;
  onSelectEvidenceDelta?: (deltaId: string | null) => void;
}) {
  return (
    <section aria-label="Useful surfaces">
      <h5>Useful surfaces</h5>
      <div className="graph-review-card-actions">
        <button
          type="button"
          onClick={() => onSelectEvidenceDelta?.(deltaId ?? null)}
          disabled={!deltaId}
        >
          Inspect evidence/source
        </button>
      </div>
    </section>
  );
}

function NodeReviewStatusDetails({ viewModel }: { viewModel: GraphReviewSelectedNodeViewModel }) {
  if (!shouldShowReviewStatus(viewModel)) return null;

  return (
    <section aria-label="Review status">
      <h5>Review status</h5>
      <p>{statusCopy(viewModel)}</p>
      {viewModel.counterpart ? (
        <p>
          <strong>Counterpart:</strong> {viewModel.counterpart.label} (
          {viewModel.counterpart.laneRole})
        </p>
      ) : null}
    </section>
  );
}

function NodeEvidenceSourceDetails({
  node,
  sourceAnchorShownAbove,
  deltaId,
  onSelectEvidenceDelta,
}: {
  node: GraphProjectionNodeView;
  sourceAnchorShownAbove: boolean;
  deltaId?: string | null;
  onSelectEvidenceDelta?: (deltaId: string | null) => void;
}) {
  return (
    <details className="graph-review-evidence-source-panel">
      <summary>Evidence / Source</summary>
      <p>
        {node.evidence_badges.length} evidence badge
        {node.evidence_badges.length === 1 ? "" : "s"}
        {node.source_domains.length
          ? `; source domains: ${node.source_domains.join(", ")}`
          : "; no source domains"}
        .
      </p>
      {!sourceAnchorShownAbove && node.source_anchor_text ? (
        <p>
          <strong>Source phrase:</strong> {node.source_anchor_text}
        </p>
      ) : null}
      {deltaId && onSelectEvidenceDelta ? (
        <div className="graph-review-card-actions">
          <button type="button" onClick={() => onSelectEvidenceDelta(deltaId)}>
            Open evidence
          </button>
        </div>
      ) : null}
    </details>
  );
}

function NodeTechnicalDetails({ viewModel }: { viewModel: GraphReviewSelectedNodeViewModel }) {
  const node = viewModel.node;
  const hasTechnicalContent =
    node.assertion_id ||
    node.visibility ||
    (node.graph_scope && node.graph_scope.length) ||
    node.source_domains.length ||
    viewModel.laneRole ||
    node.node_id ||
    viewModel.deltaId;

  if (!hasTechnicalContent) return null;

  return (
    <details className="graph-review-technical-details-panel">
      <summary>Technical details</summary>
      {node.assertion_id ? (
        <p>
          <strong>Assertion ID:</strong> {node.assertion_id}
        </p>
      ) : null}
      {node.visibility ? (
        <p>
          <strong>Visibility:</strong> {node.visibility}
        </p>
      ) : null}
      {node.graph_scope?.length ? (
        <p>
          <strong>Graph scope:</strong> {node.graph_scope.join(", ")}
        </p>
      ) : null}
      {node.source_domains.length ? (
        <p>
          <strong>Source domains:</strong> {node.source_domains.join(", ")}
        </p>
      ) : null}
      <p>
        <strong>Lane role:</strong> {viewModel.laneRole}
      </p>
      <p>
        <strong>Node ID:</strong> {node.node_id}
      </p>
      {viewModel.deltaId ? (
        <p>
          <strong>Delta ID:</strong> {viewModel.deltaId}
        </p>
      ) : null}
    </details>
  );
}

export function GraphReviewNodeGameCard({
  viewModel,
  selectedEdgeId,
  onSelectRelationship,
  onSelectEvidenceDelta,
  showUsefulSurfaces = true,
}: {
  viewModel: GraphReviewSelectedNodeViewModel;
  selectedEdgeId: string | null;
  onSelectRelationship: (
    relationship: GraphProjectionAdjacencyCandidate,
  ) => void;
  onSelectEvidenceDelta?: (deltaId: string | null) => void;
  showUsefulSurfaces?: boolean;
}) {
  const node = viewModel.node;
  const sourceAnchorShownAbove = Boolean(isAuthoredNode(node) && node.source_anchor_text);

  return (
    <article
      className="graph-review-node-game-card"
      aria-label={`${node.label} game card`}
    >
      <NodeIdentityHeader viewModel={viewModel} />
      <NodeGameSummary node={node} />
      <NodeAliasMemoryNote node={node} />
      <NodeRelationshipSection
        node={node}
        selectedEdgeId={selectedEdgeId}
        onSelectRelationship={onSelectRelationship}
      />
      {showUsefulSurfaces ? (
        <NodeUsefulSurfacesSection
          deltaId={viewModel.deltaId}
          onSelectEvidenceDelta={onSelectEvidenceDelta}
        />
      ) : null}
      <NodeReviewStatusDetails viewModel={viewModel} />
      <NodeEvidenceSourceDetails
        node={node}
        sourceAnchorShownAbove={sourceAnchorShownAbove}
        deltaId={viewModel.deltaId}
        onSelectEvidenceDelta={onSelectEvidenceDelta}
      />
      <NodeTechnicalDetails viewModel={viewModel} />
    </article>
  );
}
