import { useEffect, useState } from "react";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import { GraphObjectAuthoringLinkExistingSection } from "./GraphObjectAuthoringLinkExistingSection";
import type { GraphObjectAuthoringInspectedNode } from "./GraphObjectAuthoringObjectRefPicker";
import { GraphObjectAuthoringObjectForm } from "./GraphObjectAuthoringObjectForm";
import { GraphObjectAuthoringPrepareCommitPanel } from "./GraphObjectAuthoringPrepareCommitPanel";
import { GraphObjectAuthoringRelationshipForm } from "./GraphObjectAuthoringRelationshipForm";
import { GraphObjectAuthoringSelectedSource } from "./GraphObjectAuthoringSelectedSource";
import { GraphObjectAuthoringStagingTray } from "./GraphObjectAuthoringStagingTray";
import { GraphObjectAuthoringVisibilitySection } from "./GraphObjectAuthoringVisibilitySection";
import {
  isValidObjectRef,
  type GraphObjectAuthoringFormState,
  type GraphObjectAuthoringLinkExistingFormState,
  type GraphObjectAuthoringProposal,
  type GraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";

type GraphObjectAuthoringSelectionMode = "object" | "link_existing";

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

  linkExistingFormState?: GraphObjectAuthoringLinkExistingFormState;
  onLinkExistingFieldChange?: <K extends keyof GraphObjectAuthoringLinkExistingFormState>(
    field: K,
    value: GraphObjectAuthoringLinkExistingFormState[K],
  ) => void;
  onStageLinkExistingProposal?: () => void;

  relationshipFormState?: GraphObjectAuthoringRelationshipFormState;
  onRelationshipFieldChange?: <K extends keyof GraphObjectAuthoringRelationshipFormState>(
    field: K,
    value: GraphObjectAuthoringRelationshipFormState[K],
  ) => void;
  onStageRelationshipProposal?: () => void;

  campaignId?: string;
  sessionId?: string;
  campaignRel?: string | null;
  sourceRunId?: string | null;
  sourceGraphId?: string | null;
  onCommittedProposals?: (localProposalIds: string[]) => void;

  existingNodes?: GraphObjectAuthoringInspectedNode[];
}

export function GraphObjectAuthoringSurface({
  selectedSource,
  formState,
  proposals,
  onFormFieldChange,
  onStageProposal,
  onRemoveProposal,
  linkExistingFormState,
  onLinkExistingFieldChange,
  onStageLinkExistingProposal,
  relationshipFormState,
  onRelationshipFieldChange,
  onStageRelationshipProposal,
  campaignId,
  sessionId,
  campaignRel,
  sourceRunId,
  sourceGraphId,
  onCommittedProposals,
  existingNodes = [],
}: GraphObjectAuthoringSurfaceProps) {
  const [selectionMode, setSelectionMode] = useState<GraphObjectAuthoringSelectionMode>("object");
  const supportsLinkExisting = Boolean(linkExistingFormState && onLinkExistingFieldChange && onStageLinkExistingProposal);
  const supportsRelationship = Boolean(relationshipFormState && onRelationshipFieldChange && onStageRelationshipProposal);

  useEffect(() => {
    if (selectedSource) {
      setSelectionMode("object");
    }
  }, [selectedSource]);

  const canStage = Boolean(selectedSource && formState.label.trim());
  const canStageLinkExisting = Boolean(
    selectedSource && isValidObjectRef(linkExistingFormState?.existingObjectRef),
  );
  const canStageRelationship = Boolean(
    isValidObjectRef(relationshipFormState?.sourceObjectRef) &&
      isValidObjectRef(relationshipFormState?.targetObjectRef) &&
      relationshipFormState?.relationshipType.trim(),
  );

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

          {supportsLinkExisting ? (
            <div className="graph-object-authoring-mode-tabs" role="tablist" aria-label="Authoring mode">
              <button
                type="button"
                role="tab"
                aria-selected={selectionMode === "object"}
                data-testid="graph-object-authoring-mode-object"
                className={selectionMode === "object" ? "is-active" : ""}
                onClick={() => setSelectionMode("object")}
              >
                Object draft
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={selectionMode === "link_existing"}
                data-testid="graph-object-authoring-mode-link-existing"
                className={selectionMode === "link_existing" ? "is-active" : ""}
                onClick={() => setSelectionMode("link_existing")}
              >
                Link existing
              </button>
            </div>
          ) : null}

          {selectionMode === "object" ? (
            <>
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
          ) : null}

          {selectionMode === "link_existing" && linkExistingFormState && onLinkExistingFieldChange ? (
            <>
              <GraphObjectAuthoringLinkExistingSection
                selectedText={selectedSource.selectedText}
                formState={linkExistingFormState}
                onChange={onLinkExistingFieldChange}
                proposals={proposals}
                existingNodes={existingNodes}
              />
              <GraphObjectAuthoringVisibilitySection
                visibility={linkExistingFormState.visibility}
                onChange={(visibility) => onLinkExistingFieldChange("visibility", visibility)}
                fieldId="graph-object-authoring-link-existing-visibility"
                fieldLabel="Link visibility"
                sectionLabel="Link-existing visibility"
              />
              <div className="graph-object-authoring-surface-actions">
                <button
                  type="button"
                  data-testid="graph-object-authoring-stage-link-existing-button"
                  disabled={!canStageLinkExisting}
                  onClick={onStageLinkExistingProposal}
                >
                  Stage link-existing draft
                </button>
              </div>
            </>
          ) : null}
        </>
      ) : (
        <p className="graph-object-authoring-surface-empty-hint">
          Highlight source text in the recap and choose “Author graph object” to
          start a draft.
        </p>
      )}

      {supportsRelationship && relationshipFormState && onRelationshipFieldChange ? (
        <section className="graph-object-authoring-relationship-section" aria-label="Relationship authoring">
          <header className="graph-object-authoring-relationship-header">
            <h4>Relationship</h4>
            <p className="graph-object-authoring-surface-hint">
              Stage a relationship between two objects. Draft only.
            </p>
          </header>
          <GraphObjectAuthoringRelationshipForm
            formState={relationshipFormState}
            onChange={onRelationshipFieldChange}
            proposals={proposals}
            existingNodes={existingNodes}
          />
          <GraphObjectAuthoringVisibilitySection
            visibility={relationshipFormState.visibility}
            onChange={(visibility) => onRelationshipFieldChange("visibility", visibility)}
            fieldId="graph-object-authoring-relationship-visibility"
            fieldLabel="Relationship visibility"
            sectionLabel="Relationship visibility section"
          />
          <div className="graph-object-authoring-surface-actions">
            <button
              type="button"
              data-testid="graph-object-authoring-stage-relationship-button"
              disabled={!canStageRelationship}
              onClick={onStageRelationshipProposal}
            >
              Stage relationship
            </button>
          </div>
        </section>
      ) : null}

      <GraphObjectAuthoringStagingTray proposals={proposals} onRemove={onRemoveProposal} />

      {campaignId && sessionId && onCommittedProposals ? (
        <GraphObjectAuthoringPrepareCommitPanel
          campaignId={campaignId}
          sessionId={sessionId}
          campaignRel={campaignRel}
          sourceRunId={sourceRunId}
          sourceGraphId={sourceGraphId}
          proposals={proposals}
          onCommitted={onCommittedProposals}
        />
      ) : null}
    </section>
  );
}
