// PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION:
// Retained until PR007/PR008 removes preview/latest-ingest selectors from surface APIs.
import { useMemo } from "react";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
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
  detectObjectFormOverlapWarnings,
  type GraphObjectAuthoringOverlapContext,
} from "./graphObjectAuthoringOverlap";
import {
  canStageRelationshipForm,
  type GraphObjectAuthoringFormState,
  type GraphObjectAuthoringProposal,
  type GraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";
import type { GraphReviewProjectionLaneRole } from "./GraphReviewProjectionLane";
import { useGraphObjectCrossScopeCandidates } from "./useGraphObjectCrossScopeCandidates";
import type { GraphProjectionNodeView } from "../../api/types";

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
  onStartManualDraft?: () => void;
  pendingSelection?: GraphAuthoringSelection | null;
  onUseSelectedText?: (selection: GraphAuthoringSelection) => void;
  creatingObject?: boolean;
  createObjectError?: string | null;

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
  onStartManualDraft,
  pendingSelection = null,
  onUseSelectedText,
  creatingObject = false,
  createObjectError = null,
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
  const supportsRelationship = Boolean(relationshipFormState && onRelationshipFieldChange && onStageRelationshipProposal);

  const canStage = Boolean(selectedSource && formState.label.trim());
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

  const showCreateNew = focusPanel === "all" || focusPanel === "create_new";
  const showRelationships = focusPanel === "all" || focusPanel === "relationships";
  const showStageOverlay = focusPanel === "all" || focusPanel === "stage_overlay";

  const hasUnusedPendingSelection = Boolean(
    pendingSelection &&
      pendingSelection.selectedText.trim() &&
      (!selectedSource || selectedSource.selectedText !== pendingSelection.selectedText),
  );

  const headerCopy =
    focusPanel === "create_new"
      ? {
          kicker: "Create new object",
          title: "Create a graph object",
          hint:
            "Highlight recap text, then use it below. Create object saves to authored memory immediately, then continues in Existing object.",
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
        <>
          {hasUnusedPendingSelection && pendingSelection && onUseSelectedText ? (
            <div
              className="graph-object-authoring-pending-selection"
              data-testid="graph-object-authoring-pending-selection"
            >
              <p className="graph-object-authoring-pending-selection-label">
                Highlighted in recap
              </p>
              <p className="graph-object-authoring-pending-selection-quote">
                “{pendingSelection.selectedText}”
              </p>
              <div className="graph-object-authoring-surface-actions">
                <button
                  type="button"
                  data-testid="graph-object-authoring-use-selected-text-button"
                  onClick={() => onUseSelectedText(pendingSelection)}
                >
                  Use this text
                </button>
              </div>
            </div>
          ) : null}

          {selectedSource ? (
            <>
              <GraphObjectAuthoringSelectedSource selection={selectedSource} />

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
                  disabled={!canStage || creatingObject}
                  onClick={onStageProposal}
                >
                  {creatingObject ? "Creating…" : "Create object"}
                </button>
              </div>
              {createObjectError ? (
                <p className="graph-object-authoring-prepare-commit-error" role="alert">
                  {createObjectError}
                </p>
              ) : null}
            </>
          ) : (
            <div className="graph-object-authoring-surface-empty-state">
              <p className="graph-object-authoring-surface-empty-hint">
                Highlight source text in the recap to use it here, or start a draft
                directly below.
              </p>
              {onStartManualDraft ? (
                <div className="graph-object-authoring-surface-actions">
                  <button
                    type="button"
                    data-testid="graph-object-authoring-start-manual-draft-button"
                    onClick={onStartManualDraft}
                  >
                    Create new object
                  </button>
                </div>
              ) : null}
            </div>
          )}
        </>
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
