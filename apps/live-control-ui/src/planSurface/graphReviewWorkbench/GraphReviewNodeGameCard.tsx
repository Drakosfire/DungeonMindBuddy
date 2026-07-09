import type { GraphProjectionAdjacencyCandidate, GraphProjectionNodeView } from "../../api/types";
import { GraphReviewRelationshipChips } from "./GraphReviewRelationshipChips";
import {
  GRAPH_REVIEW_RELATIONSHIP_PREDICATES,
  type GraphReviewRelationshipPredicate,
} from "./graphReviewLocalAuthoringState";
import {
  detailsConnectionContextForNode,
  displayAliasesForNode,
  durableIdentitySummaryForNode,
  graphObjectSecondaryRoleLabel,
  graphObjectTypeBadgeLabel,
  mergedIdentityNoteCopy,
  primaryGameSummaryForNode,
  type GraphReviewSelectedNodeViewModel,
} from "./graphReviewSelectionUtils";

export type GraphReviewSelectedObjectAction = {
  id: string;
  label: string;
  helpText?: string;
  disabled?: boolean;
  onClick: () => void;
};

export type GraphReviewNodeGameCardRelationshipStaging = {
  predicate: GraphReviewRelationshipPredicate;
  onPredicateChange: (predicate: GraphReviewRelationshipPredicate) => void;
  canStageRelationship: boolean;
  onStageRelationship: () => void;
  relationshipDraftSourceLabel?: string | null;
  sameObjectAsSource: boolean;
};

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

const VISIBILITY_FRIENDLY_COPY: Record<string, string> = {
  gm_private: "GM private",
  gm: "GM private",
  table_known: "Table known",
  table: "Table",
  player_visible: "Player visible",
  player: "Player",
  character_specific: "Character-specific",
  character: "Character",
  hidden_until_revealed: "Hidden until revealed",
};

function friendlyVisibilityCopy(visibility: string): string {
  const key = visibility.trim().toLowerCase();
  return VISIBILITY_FRIENDLY_COPY[key] ?? visibility;
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

function NodeIdentityHeader({ node }: { node: GraphProjectionNodeView }) {
  const aliases = displayAliasesForNode(node);
  const typeBadge = graphObjectTypeBadgeLabel(node.kind, node.role);
  const secondaryRole = graphObjectSecondaryRoleLabel(node.kind, node.role);

  return (
    <header className="graph-review-node-identity-header">
      <div className="graph-review-node-identity-title-row">
        <span
          className="graph-review-object-type-badge"
          aria-label={`Object type: ${typeBadge}`}
        >
          {typeBadge}
        </span>
        <h4>{node.label}</h4>
      </div>
      {secondaryRole ? (
        <p className="graph-review-node-role-subtitle">{secondaryRole}</p>
      ) : null}
      {aliases.length ? (
        <p className="graph-review-node-aliases">
          Also known as: {aliases.join(", ")}
        </p>
      ) : null}
    </header>
  );
}

function NodeGameSummary({ node }: { node: GraphProjectionNodeView }) {
  const summary = primaryGameSummaryForNode(node);
  if (!summary) return null;

  return (
    <section aria-label="Campaign summary">
      <p>{summary}</p>
    </section>
  );
}

function NodeRelationshipSection({
  node,
  selectedEdgeId,
  onSelectRelationship,
  onClearRelationship,
}: {
  node: GraphProjectionNodeView;
  selectedEdgeId: string | null;
  onSelectRelationship: (relationship: GraphProjectionAdjacencyCandidate) => void;
  onClearRelationship?: () => void;
}) {
  return (
    <section
      className="graph-review-node-relationships-primary"
      aria-label="Connected objects and relationships"
    >
      <h5>Related objects</h5>
      <GraphReviewRelationshipChips
        relationships={node.adjacency}
        selectedEdgeId={selectedEdgeId}
        onSelect={onSelectRelationship}
        onClear={onClearRelationship}
      />
    </section>
  );
}

function NodeActionsSection({
  actions,
  deltaId,
  onSelectEvidenceDelta,
  draftActionsNote,
  relationshipStaging,
}: {
  actions: GraphReviewSelectedObjectAction[];
  deltaId?: string | null;
  onSelectEvidenceDelta?: (deltaId: string | null) => void;
  draftActionsNote?: string;
  relationshipStaging?: GraphReviewNodeGameCardRelationshipStaging;
}) {
  const evidenceAvailable = Boolean(deltaId && onSelectEvidenceDelta);
  const hasActions = actions.length > 0 || evidenceAvailable;

  if (!hasActions && !relationshipStaging) return null;

  return (
    <section aria-label="Actions">
      <h5>Actions</h5>
      {draftActionsNote ? (
        <p className="graph-review-muted graph-review-actions-note">{draftActionsNote}</p>
      ) : null}
      {hasActions ? (
        <div className="graph-review-card-actions">
          {actions.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={action.onClick}
              disabled={action.disabled}
              title={action.helpText}
            >
              {action.label}
            </button>
          ))}
          {evidenceAvailable ? (
            <button
              type="button"
              onClick={() => onSelectEvidenceDelta?.(deltaId ?? null)}
            >
              Inspect evidence/source
            </button>
          ) : null}
        </div>
      ) : null}
      {relationshipStaging ? (
        <div className="graph-review-relationship-staging-row">
          <label>
            Relationship type{" "}
            <select
              value={relationshipStaging.predicate}
              onChange={(event) =>
                relationshipStaging.onPredicateChange(
                  event.target.value as GraphReviewRelationshipPredicate,
                )
              }
            >
              {GRAPH_REVIEW_RELATIONSHIP_PREDICATES.map((predicate) => (
                <option key={predicate} value={predicate}>
                  {predicate}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={relationshipStaging.onStageRelationship}
            disabled={!relationshipStaging.canStageRelationship}
          >
            Stage relationship
          </button>
          {relationshipStaging.sameObjectAsSource ? (
            <p className="graph-review-muted">
              This object is already the relationship source. Choose a different
              object as the target.
            </p>
          ) : relationshipStaging.relationshipDraftSourceLabel ? (
            <p className="graph-review-muted">
              Relationship source: {relationshipStaging.relationshipDraftSourceLabel}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function NodeDetailsPanel({
  viewModel,
  sourceAnchorShownAbove,
  onSelectEvidenceDelta,
}: {
  viewModel: GraphReviewSelectedNodeViewModel;
  sourceAnchorShownAbove: boolean;
  onSelectEvidenceDelta?: (deltaId: string | null) => void;
}) {
  const node = viewModel.node;
  const durableSummary = durableIdentitySummaryForNode(node);
  const showReviewStatus = shouldShowReviewStatus(viewModel);
  const connectionContext = detailsConnectionContextForNode(node);
  const mergedIdentityCopy = durableSummary
    ? mergedIdentityNoteCopy(durableSummary, node.aliases, {
        adjacencyCount: node.adjacency.length,
        evidenceCount: node.evidence_badges.length,
      })
    : null;

  return (
    <details className="graph-review-details-panel">
      <summary>Details</summary>
      <section className="graph-review-details-section" aria-label="Memory and visibility">
        <p className="graph-review-muted">{laneBadgeCopy(viewModel)}</p>
        {isAuthoredNode(node) ? (
          <p className="graph-review-muted">This node includes authored memory.</p>
        ) : null}
        {node.visibility ? (
          <p className="graph-review-muted">
            Visibility: {friendlyVisibilityCopy(node.visibility)}
          </p>
        ) : null}
        {!sourceAnchorShownAbove && node.source_anchor_text ? (
          <p className="graph-review-muted">
            Grounded from source phrase: “{node.source_anchor_text}”
          </p>
        ) : null}
      </section>
      {mergedIdentityCopy ? (
        <section className="graph-review-details-section" aria-label="Merged identity">
          <h6>Merged identity</h6>
          <p>
            {mergedIdentityCopy.foldedLine} {mergedIdentityCopy.contextLine}
          </p>
        </section>
      ) : null}
      {connectionContext ? (
        <section className="graph-review-details-section" aria-label="Connection context">
          <p>{connectionContext}</p>
        </section>
      ) : null}
      {showReviewStatus ? (
        <section className="graph-review-details-section" aria-label="Review status">
          <h6>Review status</h6>
          <p>{statusCopy(viewModel)}</p>
          {viewModel.counterpart ? (
            <p>
              <strong>Counterpart:</strong> {viewModel.counterpart.label} (
              {viewModel.counterpart.laneRole})
            </p>
          ) : null}
        </section>
      ) : null}
      <section className="graph-review-details-section" aria-label="Evidence and source">
        <h6>Evidence and source</h6>
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
        {viewModel.deltaId && onSelectEvidenceDelta ? (
          <div className="graph-review-card-actions">
            <button type="button" onClick={() => onSelectEvidenceDelta(viewModel.deltaId ?? null)}>
              Open evidence
            </button>
          </div>
        ) : null}
      </section>
      <section className="graph-review-details-section" aria-label="Identifiers">
        <h6>Identifiers</h6>
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
        {durableSummary ? (
          <div className="graph-review-merge-provenance-details" aria-label="Merge provenance">
            <h6>Merge provenance</h6>
            {durableSummary.mergedAwayIds.length ? (
              <p>
                <strong>Merged-away IDs:</strong> {durableSummary.mergedAwayIds.join(", ")}
              </p>
            ) : null}
            {durableSummary.mergeAssertionIds.length ? (
              <p>
                <strong>Merge assertion IDs:</strong>{" "}
                {durableSummary.mergeAssertionIds.join(", ")}
              </p>
            ) : null}
            {durableSummary.redirectIds.length ? (
              <p>
                <strong>Redirect IDs:</strong> {durableSummary.redirectIds.join(", ")}
              </p>
            ) : null}
            {durableSummary.mergeRecordIds.length ? (
              <p>
                <strong>Merge record IDs:</strong>{" "}
                {durableSummary.mergeRecordIds.join(", ")}
              </p>
            ) : null}
          </div>
        ) : null}
      </section>
    </details>
  );
}

export function GraphReviewNodeGameCard({
  viewModel,
  selectedEdgeId,
  onSelectRelationship,
  onClearRelationship,
  onSelectEvidenceDelta,
  actions = [],
  draftActionsNote,
  relationshipStaging,
}: {
  viewModel: GraphReviewSelectedNodeViewModel;
  selectedEdgeId: string | null;
  onSelectRelationship: (
    relationship: GraphProjectionAdjacencyCandidate,
  ) => void;
  onClearRelationship?: () => void;
  onSelectEvidenceDelta?: (deltaId: string | null) => void;
  actions?: GraphReviewSelectedObjectAction[];
  draftActionsNote?: string;
  relationshipStaging?: GraphReviewNodeGameCardRelationshipStaging;
}) {
  const node = viewModel.node;
  const sourceAnchorShownAbove = false;

  return (
    <article
      className="graph-review-node-game-card"
      aria-label={`${node.label} game card`}
    >
      <NodeIdentityHeader node={node} />
      <NodeRelationshipSection
        node={node}
        selectedEdgeId={selectedEdgeId}
        onSelectRelationship={onSelectRelationship}
        onClearRelationship={onClearRelationship}
      />
      <NodeGameSummary node={node} />
      <NodeActionsSection
        actions={actions}
        deltaId={viewModel.deltaId}
        onSelectEvidenceDelta={onSelectEvidenceDelta}
        draftActionsNote={draftActionsNote}
        relationshipStaging={relationshipStaging}
      />
      <NodeDetailsPanel
        viewModel={viewModel}
        sourceAnchorShownAbove={sourceAnchorShownAbove}
        onSelectEvidenceDelta={onSelectEvidenceDelta}
      />
    </article>
  );
}
