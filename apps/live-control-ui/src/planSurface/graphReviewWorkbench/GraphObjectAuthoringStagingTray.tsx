import { GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS, type GraphObjectAuthoringProposal } from "./graphObjectAuthoringDraft";

function visibilityLabel(proposal: GraphObjectAuthoringProposal): string {
  const option = GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS.find(
    (candidate) => candidate.value === proposal.visibility.visibility,
  );
  return option?.label ?? proposal.visibility.visibility;
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
            >
              <div className="graph-object-authoring-staging-tray-item-header">
                <span className="graph-object-authoring-staging-tray-item-label">
                  {proposal.objectRef.label}
                </span>
                <span className="graph-object-authoring-staging-tray-item-kind">
                  {proposal.objectRef.kind}
                </span>
              </div>
              {proposal.objectRef.aliases.length ? (
                <p>Aliases: {proposal.objectRef.aliases.join(", ")}</p>
              ) : null}
              {proposal.objectRef.summary ? <p>{proposal.objectRef.summary}</p> : null}
              <p>Visibility: {visibilityLabel(proposal)}</p>
              <p>Selected source: “{proposal.selection.selectedText}”</p>
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
