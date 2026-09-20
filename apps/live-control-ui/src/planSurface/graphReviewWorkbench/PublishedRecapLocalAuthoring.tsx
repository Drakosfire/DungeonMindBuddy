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
import type { GraphObjectAuthoringInspectedNode } from "./GraphObjectAuthoringObjectRefPicker";
import { useGraphObjectAuthoringDraft } from "./useGraphObjectAuthoringDraft";

function nullableAttr(value: string | null | undefined): string {
  return value == null || value === "" ? "null" : value;
}

function existingNodesFromViews(
  nodeViews: Record<string, GraphProjectionNodeView>,
): GraphObjectAuthoringInspectedNode[] {
  return Object.values(nodeViews).map((node) => ({
    node_id: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
    aliases: node.aliases,
    sourceAnchorText: node.source_anchor_text,
  }));
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
}: PublishedRecapLocalAuthoringProps) {
  const draft = useGraphObjectAuthoringDraft({ campaignId, sessionId });
  const [pendingSelection, setPendingSelection] = useState<GraphAuthoringSelection | null>(null);

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

  const existingNodes = useMemo(() => existingNodesFromViews(nodeViews), [nodeViews]);

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
      const node = nodeViews[nodeId];
      if (!node) {
        return;
      }
      draft.openWithSelection(
        preserveSourceIdentity(
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
        ),
      );
      seedRelationshipFromNode(node);
    },
    [
      authoringContext,
      campaignId,
      draft,
      graphId,
      nodeViews,
      onInspectNode,
      preserveSourceIdentity,
      seedRelationshipFromNode,
      sessionId,
    ],
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
    },
    [draft, recapGroundedSelection],
  );

  const handleStartManualDraft = useCallback(() => {
    draft.openWithSelection(recapGroundedSelection());
  }, [draft, recapGroundedSelection]);

  const selectedSourceIdentity = draft.selectedSource ?? pendingSelection;

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
    >
      <div className="recap-reader-layout union-supergraph-layout">
        <GraphProjectionReader
          markdown={markdown}
          nodeViews={nodeViews}
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
        onStageLinkExisting={(candidate) => {
          const selected = draft.selectedSource;
          if (!selected) {
            return false;
          }
          return draft.stageLinkExistingFromResolver({
            selection: recapGroundedSelection(selected),
            candidate,
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
        projectionNodeViews={nodeViews}
      />
    </div>
  );
}
