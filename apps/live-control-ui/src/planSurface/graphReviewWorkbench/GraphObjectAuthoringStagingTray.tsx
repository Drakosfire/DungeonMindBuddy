import {
  friendlyVisibilityLabel,
  formatAuthoringRelationshipStatement,
  type GraphObjectAuthoringLinkExistingProposal,
  type GraphObjectAuthoringMergeProposal,
  type GraphObjectAuthoringObjectProposal,
  type GraphObjectAuthoringProposal,
  type GraphObjectAuthoringRelationshipProposal,
} from "./graphObjectAuthoringDraft";
import { GraphObjectAuthoringOverlapWarnings } from "./GraphObjectAuthoringOverlapWarnings";
import {
  detectProposalOverlapWarnings,
  type GraphObjectAuthoringOverlapContext,
  type GraphObjectAuthoringOverlapWarning,
} from "./graphObjectAuthoringOverlap";
import {
  buildMergeCandidateFromOverlapWarning,
  type GraphObjectMergeCandidate,
} from "./graphObjectMergeCandidates";
import type { GraphProjectionNodeView } from "../../api/types";

export const GRAPH_OBJECT_AUTHORING_STAGING_TRAY_EMPTY_MESSAGE =
  "No staged memory yet. Create an object, link, relationship, or merge draft above.";

export const GRAPH_OBJECT_AUTHORING_STAGING_TRAY_EMPTY_MESSAGE_WORKFLOW =
  "No staged memory yet. Stage a draft from New object, Existing object, Merge candidates, or Relationships.";

function visibilityLabel(
  visibility: GraphObjectAuthoringProposal["visibility"]["visibility"],
): string {
  return friendlyVisibilityLabel(visibility);
}

function objectRefDisplayLabel(ref: { label: string; kind?: string | null }): string {
  return ref.kind ? `${ref.label} (${ref.kind})` : ref.label;
}

function ObjectProposalCard({ proposal }: { proposal: GraphObjectAuthoringObjectProposal }) {
  return (
    <>
      <div className="graph-object-authoring-staging-tray-item-header">
        <span className="graph-object-authoring-staging-tray-item-kind-badge">Object</span>
        <span className="graph-object-authoring-staging-tray-item-label">
          {proposal.objectRef.label}
        </span>
        <span className="graph-object-authoring-staging-tray-item-kind">{proposal.objectRef.kind}</span>
      </div>
      {proposal.objectRef.aliases.length ? (
        <p>Aliases: {proposal.objectRef.aliases.join(", ")}</p>
      ) : null}
      {proposal.objectRef.summary ? <p>{proposal.objectRef.summary}</p> : null}
      <p>Visibility: {visibilityLabel(proposal.visibility.visibility)}</p>
      <p>Selected source: “{proposal.selection.selectedText}”</p>
    </>
  );
}

function LinkExistingProposalCard({
  proposal,
}: {
  proposal: GraphObjectAuthoringLinkExistingProposal;
}) {
  return (
    <>
      <div className="graph-object-authoring-staging-tray-item-header">
        <span className="graph-object-authoring-staging-tray-item-kind-badge">Link existing</span>
        <span className="graph-object-authoring-staging-tray-item-label">
          {proposal.selectedText}
        </span>
      </div>
      <p>
        Links to existing object: {objectRefDisplayLabel(proposal.existingObjectRef)}
      </p>
      <p>Operation: {proposal.operation.replaceAll("_", " ")}</p>
      {proposal.aliasText ? <p>Alias text: {proposal.aliasText}</p> : null}
      <p>Visibility: {visibilityLabel(proposal.visibility.visibility)}</p>
      <p>Selected source: “{proposal.selection.selectedText}”</p>
    </>
  );
}

function RelationshipProposalCard({
  proposal,
}: {
  proposal: GraphObjectAuthoringRelationshipProposal;
}) {
  const statement = formatAuthoringRelationshipStatement(
    proposal.sourceObjectRef.label,
    proposal.targetObjectRef.label,
    proposal.relationshipType,
    {
      relationshipLabel: proposal.relationshipLabel,
      direction: proposal.direction,
    },
  );
  return (
    <>
      <div className="graph-object-authoring-staging-tray-item-header">
        <span className="graph-object-authoring-staging-tray-item-kind-badge">Relationship</span>
        <span className="graph-object-authoring-staging-tray-item-label">{statement}</span>
      </div>
      {proposal.summary ? <p>{proposal.summary}</p> : null}
      <p>Visibility: {visibilityLabel(proposal.visibility.visibility)}</p>
      {proposal.selection ? <p>Selected source: “{proposal.selection.selectedText}”</p> : null}
    </>
  );
}

function MergeProposalCard({ proposal }: { proposal: GraphObjectAuthoringMergeProposal }) {
  const mergedLabels = proposal.mergedObjectRefs.map((ref) => ref.label).join(", ");
  return (
    <>
      <div className="graph-object-authoring-staging-tray-item-header">
        <span className="graph-object-authoring-staging-tray-item-kind-badge">Merge</span>
        <span className="graph-object-authoring-staging-tray-item-label">
          {proposal.survivorObjectRef.label} ← {mergedLabels}
        </span>
      </div>
      <p>
        Survivor: <strong>{proposal.survivorObjectRef.label}</strong>
      </p>
      <p>Merged-away: {mergedLabels}</p>
      {proposal.matchedFeatures.length ? (
        <p>Matched features: {proposal.matchedFeatures.join(", ")}</p>
      ) : null}
      <p>
        Policy: preserve aliases, relationships, and evidence ({proposal.aliasPolicy},{" "}
        {proposal.relationshipPolicy}, {proposal.evidencePolicy})
      </p>
      <p className="graph-review-info">
        Merge staged locally. No objects have been deleted. Commit will write an
        identity merge assertion.
      </p>
      <p>Status: staged local</p>
    </>
  );
}

export function GraphObjectAuthoringStagingTray({
  proposals,
  onRemove,
  overlapContext,
  projectionNodeViews,
  onReviewMerge,
  emptyMessage = GRAPH_OBJECT_AUTHORING_STAGING_TRAY_EMPTY_MESSAGE,
}: {
  proposals: GraphObjectAuthoringProposal[];
  onRemove: (localProposalId: string) => void;
  overlapContext?: GraphObjectAuthoringOverlapContext;
  projectionNodeViews?: Record<string, GraphProjectionNodeView> | null;
  onReviewMerge?: (candidate: GraphObjectMergeCandidate) => void;
  emptyMessage?: string;
}) {
  function overlapAction(
    proposal: GraphObjectAuthoringProposal,
    warning: GraphObjectAuthoringOverlapWarning,
  ) {
    if (!onReviewMerge || !warning.relatedNodeId) {
      return null;
    }
    const candidate = buildMergeCandidateFromOverlapWarning(
      proposal,
      warning,
      projectionNodeViews,
    );
    if (!candidate) {
      return null;
    }
    return (
      <button
        type="button"
        className="graph-object-authoring-overlap-review-merge"
        onClick={() => onReviewMerge(candidate)}
      >
        Review merge
      </button>
    );
  }

  return (
    <div className="graph-object-authoring-staging-tray" aria-label="Staged memory drafts">
      {proposals.length === 0 ? (
        <p className="graph-object-authoring-staging-tray-empty">{emptyMessage}</p>
      ) : (
        <ul className="graph-object-authoring-staging-tray-list">
          {proposals.map((proposal) => (
            <li
              key={proposal.localProposalId}
              className="graph-object-authoring-staging-tray-item"
              data-testid="graph-object-authoring-staged-proposal"
              data-proposal-kind={proposal.proposalKind}
            >
              {proposal.proposalKind === "object" ? (
                <ObjectProposalCard proposal={proposal} />
              ) : null}
              {proposal.proposalKind === "link_existing" ? (
                <LinkExistingProposalCard proposal={proposal} />
              ) : null}
              {proposal.proposalKind === "relationship" ? (
                <RelationshipProposalCard proposal={proposal} />
              ) : null}
              {proposal.proposalKind === "merge_objects" ? (
                <MergeProposalCard proposal={proposal} />
              ) : null}
              {overlapContext ? (
                <GraphObjectAuthoringOverlapWarnings
                  warnings={detectProposalOverlapWarnings(proposal, overlapContext)}
                  title="Possible duplicates for this draft"
                  renderAction={(warning) => overlapAction(proposal, warning)}
                />
              ) : null}
              <button
                type="button"
                onClick={() => onRemove(proposal.localProposalId)}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
