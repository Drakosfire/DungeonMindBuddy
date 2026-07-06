import {
  GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS,
  type GraphObjectAuthoringLinkExistingProposal,
  type GraphObjectAuthoringObjectProposal,
  type GraphObjectAuthoringProposal,
  type GraphObjectAuthoringRelationshipProposal,
} from "./graphObjectAuthoringDraft";

function visibilityLabel(
  visibility: GraphObjectAuthoringProposal["visibility"]["visibility"],
): string {
  const option = GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS.find(
    (candidate) => candidate.value === visibility,
  );
  return option?.label ?? visibility;
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
  const arrow = proposal.direction === "directed" ? "→" : "↔";
  return (
    <>
      <div className="graph-object-authoring-staging-tray-item-header">
        <span className="graph-object-authoring-staging-tray-item-kind-badge">Relationship</span>
        <span className="graph-object-authoring-staging-tray-item-label">
          {objectRefDisplayLabel(proposal.sourceObjectRef)} {proposal.relationshipType} {arrow}{" "}
          {objectRefDisplayLabel(proposal.targetObjectRef)}
        </span>
      </div>
      {proposal.relationshipLabel ? <p>Label: {proposal.relationshipLabel}</p> : null}
      {proposal.summary ? <p>{proposal.summary}</p> : null}
      <p>Visibility: {visibilityLabel(proposal.visibility.visibility)}</p>
      {proposal.selection ? <p>Selected source: “{proposal.selection.selectedText}”</p> : null}
    </>
  );
}

export function GraphObjectAuthoringStagingTray({
  proposals,
  onRemove,
}: {
  proposals: GraphObjectAuthoringProposal[];
  onRemove: (localProposalId: string) => void;
}) {
  return (
    <section className="graph-object-authoring-staging-tray" aria-label="Staged graph object drafts">
      <header>
        <h4>Staged drafts</h4>
        <p className="graph-object-authoring-staging-tray-lede">
          Staged locally. No graph write has happened.
        </p>
      </header>
      {proposals.length === 0 ? (
        <p className="graph-object-authoring-staging-tray-empty">
          No object drafts staged yet.
        </p>
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
    </section>
  );
}
