import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import { GraphObjectAuthoringObjectForm } from "./GraphObjectAuthoringObjectForm";
import { GraphObjectAuthoringSelectedSource } from "./GraphObjectAuthoringSelectedSource";
import { GraphObjectAuthoringStagingTray } from "./GraphObjectAuthoringStagingTray";
import { GraphObjectAuthoringVisibilitySection } from "./GraphObjectAuthoringVisibilitySection";
import type { GraphObjectAuthoringFormState, GraphObjectAuthoringProposal } from "./graphObjectAuthoringDraft";

export interface GraphObjectAuthoringSurfaceProps {
  selectedSource: GraphAuthoringSelection | null;
  formState: GraphObjectAuthoringFormState;
  proposals: GraphObjectAuthoringProposal[];
  onFormFieldChange: <K extends keyof GraphObjectAuthoringFormState>(
    field: K,
    value: GraphObjectAuthoringFormState[K],
  ) => void;
  onStageProposal: () => void;
  onRemoveProposal: (localProposalId: string) => void;
}

export function GraphObjectAuthoringSurface({
  selectedSource,
  formState,
  proposals,
  onFormFieldChange,
  onStageProposal,
  onRemoveProposal,
}: GraphObjectAuthoringSurfaceProps) {
  const canStage = Boolean(selectedSource && formState.label.trim());

  return (
    <section
      className="graph-object-authoring-surface"
      aria-label="Graph object authoring"
      data-testid="graph-object-authoring-surface"
    >
      <header className="graph-object-authoring-surface-header">
        <p className="plan-surface-kicker">Graph object authoring</p>
        <h3>Author a graph object</h3>
        <p className="graph-object-authoring-surface-hint">
          Draft only. No graph write has happened.
        </p>
      </header>

      {selectedSource ? (
        <>
          <GraphObjectAuthoringSelectedSource selection={selectedSource} />
          <GraphObjectAuthoringObjectForm formState={formState} onChange={onFormFieldChange} />
          <GraphObjectAuthoringVisibilitySection
            visibility={formState.visibility}
            onChange={(visibility) => onFormFieldChange("visibility", visibility)}
          />
          <div className="graph-object-authoring-surface-actions">
            <button
              type="button"
              data-testid="graph-object-authoring-stage-button"
              disabled={!canStage}
              onClick={onStageProposal}
            >
              Stage object draft
            </button>
          </div>
        </>
      ) : (
        <p className="graph-object-authoring-surface-empty-hint">
          Highlight source text in the recap and choose “Author graph object” to
          start a draft.
        </p>
      )}

      <GraphObjectAuthoringStagingTray proposals={proposals} onRemove={onRemoveProposal} />
    </section>
  );
}
