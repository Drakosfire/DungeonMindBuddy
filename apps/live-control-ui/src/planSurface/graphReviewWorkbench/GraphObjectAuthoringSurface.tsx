import { useEffect, useMemo, useState } from "react";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import { GraphObjectAuthoringLinkExistingSection } from "./GraphObjectAuthoringLinkExistingSection";
import type { GraphObjectAuthoringInspectedNode } from "./GraphObjectAuthoringObjectRefPicker";
import { GraphObjectAuthoringObjectForm } from "./GraphObjectAuthoringObjectForm";
import { GraphObjectAuthoringOverlapWarnings } from "./GraphObjectAuthoringOverlapWarnings";
import { GraphObjectAuthoringPrepareCommitPanel } from "./GraphObjectAuthoringPrepareCommitPanel";
import { GraphObjectAuthoringRelationshipForm } from "./GraphObjectAuthoringRelationshipForm";
import { GraphObjectAuthoringSelectedSource } from "./GraphObjectAuthoringSelectedSource";
import {
  GRAPH_OBJECT_AUTHORING_STAGING_TRAY_EMPTY_MESSAGE,
  GRAPH_OBJECT_AUTHORING_STAGING_TRAY_EMPTY_MESSAGE_WORKFLOW,
  GraphObjectAuthoringStagingTray,
} from "./GraphObjectAuthoringStagingTray";
import { GraphObjectAuthoringVisibilitySection } from "./GraphObjectAuthoringVisibilitySection";
import {
  buildOverlapContextFromProjection,
  detectLinkExistingFormOverlapWarnings,
  detectObjectFormOverlapWarnings,
  type GraphObjectAuthoringOverlapContext,
} from "./graphObjectAuthoringOverlap";
import {
  canStageRelationshipForm,
  isValidObjectRef,
  type GraphObjectAuthoringFormState,
  type GraphObjectAuthoringLinkExistingFormState,
  type GraphObjectAuthoringProposal,
  type GraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";
import type { GraphReviewProjectionLaneRole } from "./GraphReviewProjectionLane";
import { useGraphObjectCrossScopeCandidates } from "./useGraphObjectCrossScopeCandidates";
import type { GraphProjectionNodeView } from "../../api/types";

type GraphObjectAuthoringSelectionMode = "object" | "link_existing";

export type GraphObjectAuthoringFocusPanel =
  | "all"
  | "create_new"
  | "relationships"
  | "stage_overlay";

export interface GraphObjectAuthoringSurfaceProps {
  focusPanel?: GraphObjectAuthoringFocusPanel;
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
  onRefreshProjection?: () => Promise<unknown>;
  onReviewMerge?: (candidate: import("./graphObjectMergeCandidates").GraphObjectMergeCandidate) => void;

  existingNodes?: GraphObjectAuthoringInspectedNode[];
  laneRole?: GraphReviewProjectionLaneRole;
  liveRunManifestPath?: string | null;
  previewUnionStorePath?: string | null;
  projectionNodeViews?: Record<string, GraphProjectionNodeView>;
}

export function GraphObjectAuthoringSurface({
  focusPanel = "all",
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
  onRefreshProjection,
  onReviewMerge,
  existingNodes = [],
  laneRole = "live",
  liveRunManifestPath = null,
  previewUnionStorePath = null,
  projectionNodeViews,
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
    relationshipFormState && canStageRelationshipForm(relationshipFormState),
  );

  const overlapContext: GraphObjectAuthoringOverlapContext = useMemo(
    () => buildOverlapContextFromProjection(proposals, existingNodes),
    [proposals, existingNodes],
  );

  const resolverSelectedNode = useMemo(() => {
    if (!selectedSource) return null;
    return {
      node_id:
        selectedSource.existingNodeId ??
        `selection:${selectedSource.normalizedSelectedText || selectedSource.selectedText}`,
      label: selectedSource.selectedText,
      kind: null,
      role: null,
      aliases: [],
      summary: null,
      source_domains: [],
      adjacent_labels: [],
      evidence_ref_ids: [],
    };
  }, [selectedSource]);

  const { candidates: scopeCandidates } = useGraphObjectCrossScopeCandidates({
    campaignId,
    sessionId,
    laneRole,
    query: selectedSource?.selectedText ?? "",
    selectedNode: resolverSelectedNode,
    nodeViews: projectionNodeViews,
    liveRunManifestPath,
    enabled: Boolean(selectedSource?.selectedText.trim()),
  });

  const objectFormOverlapWarnings = useMemo(
    () => detectObjectFormOverlapWarnings(formState, selectedSource, overlapContext),
    [formState, selectedSource, overlapContext],
  );

  const linkExistingOverlapWarnings = useMemo(() => {
    if (!selectedSource || !linkExistingFormState) {
      return [];
    }
    return detectLinkExistingFormOverlapWarnings(
      linkExistingFormState,
      selectedSource.selectedText,
      overlapContext,
    );
  }, [selectedSource, linkExistingFormState, overlapContext]);

  const showCreateNew = focusPanel === "all" || focusPanel === "create_new";
  const showRelationships = focusPanel === "all" || focusPanel === "relationships";
  const showStageOverlay = focusPanel === "all" || focusPanel === "stage_overlay";

  const headerCopy =
    focusPanel === "create_new"
      ? {
          kicker: "Create new object",
          title: "Draft a new graph object",
          hint: "Highlight recap text and choose “Author graph object”.",
        }
      : focusPanel === "relationships"
        ? {
            kicker: "Relationships",
            title: "Stage a relationship",
            hint: "Click graph pills in the recap to set source and target.",
          }
        : focusPanel === "stage_overlay"
          ? {
              kicker: "Stage & commit",
              title: "Review staged memory",
              hint: "These drafts are local until you prepare and commit them. No graph writes until commit.",
            }
          : {
              kicker: "Graph object authoring",
              title: "Author a graph object",
              hint: "Draft only. No graph write has happened.",
            };

  return (
    <section
      className="graph-object-authoring-surface"
      aria-label="Graph object authoring"
      data-testid="graph-object-authoring-surface"
      data-focus-panel={focusPanel}
    >
      <header className="graph-object-authoring-surface-header">
        <p className="plan-surface-kicker">{headerCopy.kicker}</p>
        <h3>{headerCopy.title}</h3>
        <p className="graph-object-authoring-surface-hint">{headerCopy.hint}</p>
      </header>

      {showCreateNew ? (
        selectedSource ? (
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
              <GraphObjectAuthoringOverlapWarnings warnings={objectFormOverlapWarnings} />
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
                scopeCandidates={scopeCandidates}
                overlapContext={overlapContext}
              />
              <GraphObjectAuthoringOverlapWarnings warnings={linkExistingOverlapWarnings} />
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
      )
      ) : null}

      {showRelationships && supportsRelationship && relationshipFormState && onRelationshipFieldChange ? (
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
            scopeCandidates={scopeCandidates}
            overlapContext={overlapContext}
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

      {showStageOverlay ? (
      <section
        className="graph-object-authoring-review-staged-memory"
        aria-label="Review staged memory"
        data-testid="graph-object-authoring-review-staged-memory"
      >
        {focusPanel !== "stage_overlay" ? (
          <header className="graph-object-authoring-review-staged-memory-header">
            <h4>Review staged memory</h4>
            <p className="graph-object-authoring-review-staged-memory-lede">
              These drafts are local until you prepare and commit them.
            </p>
          </header>
        ) : null}

        <GraphObjectAuthoringStagingTray
          proposals={proposals}
          onRemove={onRemoveProposal}
          overlapContext={overlapContext}
          projectionNodeViews={projectionNodeViews}
          onReviewMerge={onReviewMerge}
          emptyMessage={
            focusPanel === "stage_overlay"
              ? GRAPH_OBJECT_AUTHORING_STAGING_TRAY_EMPTY_MESSAGE_WORKFLOW
              : GRAPH_OBJECT_AUTHORING_STAGING_TRAY_EMPTY_MESSAGE
          }
        />

        {campaignId && sessionId && onCommittedProposals ? (
          <GraphObjectAuthoringPrepareCommitPanel
            campaignId={campaignId}
            sessionId={sessionId}
            campaignRel={campaignRel}
            sourceRunId={sourceRunId}
            sourceGraphId={sourceGraphId}
            proposals={proposals}
            previewUnionStorePath={previewUnionStorePath}
            onCommitted={onCommittedProposals}
            onRefreshProjection={onRefreshProjection}
          />
        ) : null}
      </section>
      ) : null}
    </section>
  );
}
