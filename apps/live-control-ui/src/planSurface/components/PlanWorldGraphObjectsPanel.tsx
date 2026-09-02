import { useCallback, useMemo, useSyncExternalStore } from "react";

import type { WorldGraphProjection } from "../../api/types";
import { useOptionalAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { GraphReferenceSearch } from "../../graphReference/GraphReferenceSearch";
import { referenceFromGraphNode } from "../../graphReference/referenceFromGraphNode";
import { extractExactGraphReferenceScope } from "../../graphReference/resolveGraphReference";
import type {
  GraphReferenceProjectionState,
  GraphReferenceSearchItem,
} from "../../graphReference/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { useOptionalWorldGraphLensInformationChannel } from "../../graphLens/useWorldGraphLensProjection";
import type {
  SurfaceInformationChannel,
  SurfaceInformationSnapshot,
  SurfaceInformationState,
} from "../../surfaceInformation";
import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import { formatReviewCampaignLabel } from "../sessionCampaignContext";
import { adaptWorldGraphNodeForPlanCard } from "../reference/worldGraphProjectionAdapter";

export interface PlanWorldGraphObjectsPanelProps {
  insertEnabled: boolean;
  onInsertReference: (reference: RunbookReferenceAttrs) => void;
}

function nodeScopeLabel(campaignScope: string | null | undefined): string {
  const scope = campaignScope?.trim();
  if (!scope) return "World";
  return formatReviewCampaignLabel(scope);
}

function searchItemsFromProjection(
  projection: WorldGraphProjection,
): GraphReferenceSearchItem[] {
  return projection.nodes.map((node) => {
    const adapted = adaptWorldGraphNodeForPlanCard(node);
    return {
      nodeId: adapted.node_id,
      label: adapted.label,
      kind: adapted.kind,
      role: adapted.role,
      summary: adapted.summary ?? null,
      aliases: adapted.aliases ?? [],
      scopeLabel: nodeScopeLabel(adapted.campaign_scope),
      reference: referenceFromGraphNode(adapted),
      nodeView: adapted,
    };
  });
}

function graphSearchState(
  state: SurfaceInformationState<WorldGraphProjection>,
): {
  projectionState: GraphReferenceProjectionState;
  projectionError: string | null;
  items: readonly GraphReferenceSearchItem[];
  insertDisabled: boolean;
} {
  if (state.status === "loading") {
    return {
      projectionState: "loading",
      projectionError: null,
      items: [],
      insertDisabled: true,
    };
  }
  if (state.status === "unavailable") {
    return {
      projectionState: "unavailable",
      projectionError: null,
      items: [],
      insertDisabled: true,
    };
  }
  if (state.status === "integrity_error") {
    return {
      projectionState: "error",
      projectionError: state.reason,
      items: [],
      insertDisabled: true,
    };
  }
  if (state.status === "empty") {
    return {
      projectionState: "ready",
      projectionError: null,
      items: [],
      insertDisabled: true,
    };
  }
  if (state.status === "stale") {
    return {
      projectionState: "ready",
      projectionError: null,
      items: searchItemsFromProjection(state.value),
      insertDisabled: true,
    };
  }
  return {
    projectionState: "ready",
    projectionError: null,
    items: searchItemsFromProjection(state.value),
    insertDisabled: false,
  };
}

function PlanWorldGraphObjectsChannelPanel({
  channel,
  insertEnabled,
  onInsertReference,
}: PlanWorldGraphObjectsPanelProps & {
  channel: SurfaceInformationChannel<WorldGraphProjection>;
}) {
  const snapshot = useSyncExternalStore(
    channel.subscribe,
    channel.getSnapshot,
    channel.getSnapshot,
  ) as SurfaceInformationSnapshot<WorldGraphProjection>;
  const interaction = useOptionalAgentInteraction();
  const search = useMemo(() => graphSearchState(snapshot.state), [snapshot.state]);

  const handleView = useCallback(
    (item: GraphReferenceSearchItem) => {
      const state = snapshot.state;
      if (state.status !== "ready" && state.status !== "stale") return;
      const projection = state.value;
      const graphScope = extractExactGraphReferenceScope(projection);
      const openGraphReference = interaction?.openGraphReference;
      if (!openGraphReference) return;
      if (!graphScope) {
        openGraphReference({
          resolution: {
            kind: "error",
            locator: `dmb-node:${item.nodeId}`,
            reference: item.reference,
            projectionState: "error",
            message:
              "World Graph projection snapshot lacks exact world, campaign, or revision scope; graph search open blocked.",
          },
          projectionState: "error",
        });
        return;
      }
      const selected = projection.nodes.find((node) => node.nodeId === item.nodeId);
      if (!selected) return;
      openGraphReference({
        resolution: {
          kind: "resolved_graph",
          locator: `dmb-node:${item.nodeId}`,
          reference: item.reference,
          graphObject: buildGraphObjectCardFromNodeView(item.nodeView),
          graphNodeId: item.nodeId,
          graphScope,
          projectionState: "ready",
          message: `Resolved graph node ${item.label}.`,
        },
        projectionState: "ready",
      });
    },
    [interaction, snapshot.state],
  );

  const handleInsert = useCallback(
    (item: GraphReferenceSearchItem) => {
      if (snapshot.state.status === "stale") return;
      if (snapshot.state.status !== "ready") return;
      if (!insertEnabled) return;
      onInsertReference(item.reference);
    },
    [insertEnabled, onInsertReference, snapshot.state.status],
  );

  return (
    <section
      className="plan-world-graph-objects-panel"
      data-testid="plan-world-graph-objects-panel"
      data-status={snapshot.state.status}
      data-generation={String(snapshot.generation)}
    >
      {snapshot.state.status === "stale" ? (
        <p className="graph-reference-search__status" role="status">
          World Graph information is stale. View remains available; insert is blocked.
        </p>
      ) : null}
      <GraphReferenceSearch
        items={search.items}
        projectionState={search.projectionState}
        projectionError={search.projectionError}
        insertDisabled={!insertEnabled || search.insertDisabled}
        onInsert={handleInsert}
        onView={handleView}
      />
    </section>
  );
}

export function PlanWorldGraphObjectsPanel({
  insertEnabled,
  onInsertReference,
}: PlanWorldGraphObjectsPanelProps) {
  const channel = useOptionalWorldGraphLensInformationChannel();
  if (!channel) {
    return (
      <section
        className="plan-world-graph-objects-panel"
        data-testid="plan-world-graph-objects-panel"
        data-status="no-request"
      >
        <p className="graph-reference-search__status" role="status">
          No active World Graph lens request is selected.
        </p>
      </section>
    );
  }
  return (
    <PlanWorldGraphObjectsChannelPanel
      channel={channel}
      insertEnabled={insertEnabled}
      onInsertReference={onInsertReference}
    />
  );
}
