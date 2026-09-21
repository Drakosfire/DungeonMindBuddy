import { useCallback, useMemo, useState } from "react";

import type {
  GraphProjectionNodeView,
  RecapArtifactRecord,
} from "../../api/types";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import {
  buildGraphAuthoringSelectionFromRecapNode,
  buildManualGraphAuthoringSelection,
  type GraphAuthoringContext,
  type GraphAuthoringSelection,
} from "./graphAuthoringSelection";
import { buildObjectRefFromInspectedNode } from "./graphObjectAuthoringDraft";
import { GraphObjectAuthoringSurface } from "./GraphObjectAuthoringSurface";
import type { GraphObjectAuthoringContextTab } from "./GraphObjectAuthoringPublishedWizard";
import { GraphReviewAuthorNodeHost } from "./GraphReviewAuthorNodeHost";
import type { GraphObjectAuthoringInspectedNode } from "./GraphObjectAuthoringObjectRefPicker";
import {
  useGraphObjectAuthoringDraft,
  type UseGraphObjectAuthoringDraftResult,
} from "./useGraphObjectAuthoringDraft";
import { derivePublishedRecapWorkingProjection } from "./publishedRecapWorkingProjection";

function nullableAttr(value: string | null | undefined): string {
  return value == null || value === "" ? "null" : value;
}

function existingNodesFromViews(
  nodeViews: Record<string, GraphProjectionNodeView>,
): GraphObjectAuthoringInspectedNode[] {
  return Object.values(nodeViews).map((node) => {
    const domains = new Set(node.source_domains.map((domain) => domain.trim().toLowerCase()));
    const sourceLabel = node.authored || domains.has("authored_overlay")
      ? "Authored memory"
      : domains.has("party") || domains.has("party_pc") || node.role?.trim().toLowerCase() === "pc"
        ? "Party / PCs"
        : domains.has("worldbuilding")
          ? "Worldbuilding"
          : domains.has("campaign_memory")
            ? "Campaign memory"
            : domains.has("gm_private")
              ? "GM private"
              : domains.has("recap") || domains.has("current_recap_projection")
                ? "Current recap"
                : node.source ?? "Other source";
    return {
      node_id: node.node_id,
      label: node.label,
      kind: node.kind,
      role: node.role,
      aliases: node.aliases,
      authored: node.authored,
      graphScope: domains.values().next().value ?? null,
      sourceLabel,
      sourceAnchorText: node.source_anchor_text,
      visibility: node.visibility,
    };
  });
}

export function buildPublishedRecapAuthoringContext(input: {
  campaignId: string;
  sessionId: string;
  graphId?: string | null;
  recapRecord?: RecapArtifactRecord | null;
}): GraphAuthoringContext {
  return {
    campaignId: input.campaignId,
    sessionId: input.sessionId,
    graphId: input.graphId ?? null,
    laneRole: "live",
    sourceArtifactPath: input.recapRecord?.source_recap_path ?? null,
    sourceArtifactSha256: input.recapRecord?.source_sha256 ?? null,
    sourceArtifactId: input.recapRecord?.source_artifact_id ?? null,
  };
}

export interface PublishedRecapLocalAuthoringProps {
  campaignId: string;
  sessionId: string;
  graphId?: string | null;
  markdown: string;
  nodeViews: Record<string, GraphProjectionNodeView>;
  recapRecord?: RecapArtifactRecord | null;
  onInspectNode: (nodeId: string) => void;
  onActiveNodeChange?: (nodeId: string | null) => void;
  draft?: UseGraphObjectAuthoringDraftResult;
}

export function PublishedRecapLocalAuthoring({
  campaignId,
  sessionId,
  graphId,
  markdown,
  nodeViews,
  recapRecord = null,
  onInspectNode,
  onActiveNodeChange,
  draft: suppliedDraft,
}: PublishedRecapLocalAuthoringProps) {
  const ownedDraft = useGraphObjectAuthoringDraft(
    suppliedDraft ? undefined : { campaignId, sessionId },
  );
  const draft = suppliedDraft ?? ownedDraft;
  const [pendingSelection, setPendingSelection] = useState<GraphAuthoringSelection | null>(null);
  const [authorNodeOpen, setAuthorNodeOpen] = useState(false);
  const [workingProjectionPreviewOpen, setWorkingProjectionPreviewOpen] = useState(false);
  const [authoringContextTabs, setAuthoringContextTabs] = useState<GraphObjectAuthoringContextTab[]>([]);

  const authoringContext = useMemo(
    () =>
      buildPublishedRecapAuthoringContext({
        campaignId,
        sessionId,
        graphId,
        recapRecord,
      }),
    [campaignId, graphId, recapRecord, sessionId],
  );

  const workingProjection = useMemo(
    () => derivePublishedRecapWorkingProjection({
      markdown,
      nodeViews,
      proposals: draft.proposals,
      sessionId,
    }),
    [draft.proposals, markdown, nodeViews, sessionId],
  );
  const existingNodes = useMemo(
    () => existingNodesFromViews(workingProjection.nodeViews),
    [workingProjection.nodeViews],
  );

  const preserveSourceIdentity = useCallback(
    (selection: GraphAuthoringSelection): GraphAuthoringSelection => ({
      ...selection,
      campaignId,
      sessionId,
      graphId: selection.graphId ?? graphId ?? null,
      laneRole: selection.laneRole ?? "live",
      sourceArtifactPath: selection.sourceArtifactPath ?? authoringContext.sourceArtifactPath ?? null,
      sourceArtifactSha256:
        selection.sourceArtifactSha256 ?? authoringContext.sourceArtifactSha256 ?? null,
      sourceArtifactId: selection.sourceArtifactId ?? authoringContext.sourceArtifactId ?? null,
      sourceSpanRefId: selection.sourceSpanRefId ?? null,
    }),
    [authoringContext, campaignId, graphId, sessionId],
  );

  const seedRelationshipFromNode = useCallback(
    (node: GraphProjectionNodeView) => {
      const inspectedRef = buildObjectRefFromInspectedNode({
        node_id: node.node_id,
        label: node.label,
        kind: node.kind,
        role: node.role,
      });
      const sourceRef = draft.relationshipFormState.sourceObjectRef;
      const sourceNodeId =
        sourceRef?.refKind === "existing_graph_node" ? (sourceRef.nodeId ?? null) : null;
      if (sourceNodeId && sourceNodeId !== node.node_id) {
        draft.updateRelationshipField("targetObjectRef", inspectedRef);
        return;
      }
      if (!sourceNodeId) {
        draft.updateRelationshipField("sourceObjectRef", inspectedRef);
      }
    },
    [draft],
  );

  const handleInspectNode = useCallback(
    (nodeId: string) => {
      onInspectNode(nodeId);
      const node = workingProjection.nodeViews[nodeId];
      if (!node) {
        return;
      }
      const selection = preserveSourceIdentity(
        buildGraphAuthoringSelectionFromRecapNode({
          campaignId,
          sessionId,
          graphId,
          sourceArtifactPath: authoringContext.sourceArtifactPath,
          sourceArtifactSha256: authoringContext.sourceArtifactSha256,
          sourceArtifactId: authoringContext.sourceArtifactId,
          laneRole: "live",
          node: {
            node_id: node.node_id,
            label: node.label,
            source_anchor_text: node.source_anchor_text,
          },
        }),
      );
      draft.openWithSelection(selection);
      setAuthoringContextTabs((tabs) => [
        ...tabs.filter((tab) => tab.key !== `node:${node.node_id}`),
        { key: `node:${node.node_id}`, label: node.label, selection },
      ]);
      seedRelationshipFromNode(node);
      setAuthorNodeOpen(true);
    },
    [
      authoringContext,
      campaignId,
      draft,
      graphId,
      onInspectNode,
      preserveSourceIdentity,
      seedRelationshipFromNode,
      sessionId,
      workingProjection.nodeViews,
    ],
  );

  const handleSelectAuthoringContext = useCallback(
    (selection: GraphAuthoringSelection) => {
      draft.openWithSelection(preserveSourceIdentity(selection));
      setAuthorNodeOpen(true);
    },
    [draft, preserveSourceIdentity],
  );

  const recapGroundedSelection = useCallback(
    (selection?: GraphAuthoringSelection | null): GraphAuthoringSelection => {
      if (selection) {
        return preserveSourceIdentity(selection);
      }
      return buildManualGraphAuthoringSelection({
        campaignId,
        sessionId,
        graphId,
        laneRole: "live",
        sourceArtifactPath: authoringContext.sourceArtifactPath,
        sourceArtifactSha256: authoringContext.sourceArtifactSha256,
        sourceArtifactId: authoringContext.sourceArtifactId,
      });
    },
    [authoringContext, campaignId, graphId, preserveSourceIdentity, sessionId],
  );

  const handleGraphAuthoringAction = useCallback(
    (selection: GraphAuthoringSelection) => {
      draft.openWithSelection(recapGroundedSelection(selection));
      setAuthorNodeOpen(true);
    },
    [draft, recapGroundedSelection],
  );

  const handleStartManualDraft = useCallback(() => {
    draft.openWithSelection(recapGroundedSelection());
  }, [draft, recapGroundedSelection]);

  const selectedSourceIdentity = draft.selectedSource ?? pendingSelection;
  const authoringSurface = (
    <GraphObjectAuthoringSurface
      localStageOnly
      selectedSource={draft.selectedSource}
      formState={draft.formState}
      proposals={draft.proposals}
      onFormFieldChange={draft.updateFormField}
      onStageProposal={draft.stageProposal}
      onRemoveProposal={draft.removeProposal}
      onStartManualDraft={handleStartManualDraft}
      pendingSelection={pendingSelection}
      onUseSelectedText={(selection) =>
        draft.openWithSelection(recapGroundedSelection(selection))
      }
      onStageLinkExisting={(candidate, operation) => {
        const selected = draft.selectedSource;
        if (!selected) {
          return false;
        }
        return draft.stageLinkExistingFromResolver({
          selection: recapGroundedSelection(selected),
          candidate,
          operation,
        });
      }}
      onStageLinkExistingComplete={draft.dismissSelection}
      relationshipFormState={draft.relationshipFormState}
      onRelationshipFieldChange={draft.updateRelationshipField}
      onStageRelationshipProposal={() => {
        draft.stageRelationshipProposal(recapGroundedSelection(draft.selectedSource));
      }}
      campaignId={campaignId}
      sessionId={sessionId}
      existingNodes={existingNodes}
      laneRole="live"
      projectionNodeViews={workingProjection.nodeViews}
      publishedLocalWizard
      contextTabs={authoringContextTabs}
      onSelectContextTab={handleSelectAuthoringContext}
    />
  );

  const workingProjectionPreview = (
    <div
      className="published-recap-working-projection-preview"
      data-testid="published-recap-working-projection-preview"
    >
      <button
        type="button"
        className="published-recap-working-projection-preview-toggle"
        data-testid="published-recap-working-projection-preview-toggle"
        aria-expanded={workingProjectionPreviewOpen}
        aria-controls="published-recap-working-projection-preview-content"
        onClick={() => setWorkingProjectionPreviewOpen((current) => !current)}
      >
        <span>{workingProjectionPreviewOpen ? "Hide working projection" : "Show working projection"}</span>
        <span aria-hidden="true">{workingProjectionPreviewOpen ? "−" : "+"}</span>
      </button>
      {workingProjectionPreviewOpen ? (
        <div id="published-recap-working-projection-preview-content">
          <div className="published-recap-working-projection-preview-header">
            <strong>Working projection</strong>
            <span>Updates as local drafts are staged.</span>
          </div>
          <GraphProjectionReader
            markdown={workingProjection.markdown}
            nodeViews={workingProjection.nodeViews}
            nodeDeltaPresentations={workingProjection.nodeDeltaPresentations}
            sourceSpans={[]}
            graphId={graphId}
            showGraphId={false}
            documentLabel="Working projection preview"
            resetKey={`preview:${campaignId}:${sessionId}:${graphId ?? ""}`}
            onInspectNode={handleInspectNode}
            className="published-recap-working-projection-preview-reader"
          />
        </div>
      ) : null}
    </div>
  );

  return (
    <div
      className="published-recap-local-authoring"
      data-testid="published-recap-local-authoring"
      data-write-authority="none"
      data-campaign-id={campaignId}
      data-session-id={sessionId}
      data-source-artifact-id={nullableAttr(authoringContext.sourceArtifactId)}
      data-source-artifact-path={nullableAttr(authoringContext.sourceArtifactPath)}
      data-source-artifact-sha256={nullableAttr(authoringContext.sourceArtifactSha256)}
      data-source-span-ref-id={nullableAttr(selectedSourceIdentity?.sourceSpanRefId)}
      data-existing-node-id={nullableAttr(draft.selectedSource?.existingNodeId)}
      data-local-proposal-count={draft.proposals.length}
    >
      <GraphReviewAuthorNodeHost
        mode="published-local"
        open={authorNodeOpen}
        onOpenChange={setAuthorNodeOpen}
        publishedLocalPanel={authoringSurface}
        publishedLocalPreview={workingProjectionPreview}
        projection={(
          <div className="published-recap-working-projection">
            <div
              className="published-recap-working-projection-notice"
              data-testid="published-recap-working-projection-notice"
              role="status"
            >
              <strong>Working projection</strong>
              <span>Local and uncommitted. Canonical recap and World memory are unchanged.</span>
              {workingProjection.diagnostics.length ? (
                <span data-testid="published-recap-working-projection-diagnostics">
                  {workingProjection.diagnostics[0]}
                </span>
              ) : null}
            </div>
            <GraphProjectionReader
              markdown={workingProjection.markdown}
              nodeViews={workingProjection.nodeViews}
              nodeDeltaPresentations={workingProjection.nodeDeltaPresentations}
              sourceSpans={[]}
              graphId={graphId}
              showGraphId={false}
              documentLabel="Published recap"
              resetKey={`${campaignId}:${sessionId}:${graphId ?? ""}`}
              onInspectNode={handleInspectNode}
              onActiveNodeChange={onActiveNodeChange}
              className="world-graph-recap-reader"
              authoringEnabled
              authoringContext={authoringContext}
              onGraphAuthoringSelection={setPendingSelection}
              onGraphAuthoringAction={handleGraphAuthoringAction}
            />
          </div>
        )}
      />
    </div>
  );
}
