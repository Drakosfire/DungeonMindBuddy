import { useMemo } from "react";

import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import { useWorldGraphLensProjection } from "../graphLens";
import { referenceFromGraphNode } from "../graphReference";
import { extractExactGraphReferenceScope } from "../graphReference/resolveGraphReference";
import { ResolvedGraphObjectProjection } from "../graphReference/ResolvedGraphObjectProjection";
import type { GraphReferenceResolution } from "../graphReference/types";
import {
  GRAPH_NODE_REF_TYPE,
  type RunbookReferenceAttrs,
} from "../tiptap/references/runbookReferences";
import { adaptWorldGraphNodeView } from "../worldGraph/worldGraphNodeViewAdapter";
import "./embedThreatSheet.css";

function readEmbedThreatQuery(search: string): {
  nodeId: string;
  labelHint: string;
} {
  const params = new URLSearchParams(search);
  return {
    nodeId: params.get("nodeId")?.trim() || "",
    labelHint: params.get("label")?.trim() || "",
  };
}

function embedNodeReference(nodeId: string, label: string): RunbookReferenceAttrs {
  const id = nodeId.trim();
  return {
    kind: "ref",
    refType: GRAPH_NODE_REF_TYPE,
    refId: id,
    label: label.trim() || id || "Threat",
  };
}

/**
 * Bare Threat sheet host for combat (and other static pages) iframes.
 * Reuses World Graph projection + ThreatSheetProjection — no Plan navigation.
 */
export function EmbedThreatSheetPage() {
  const { nodeId, labelHint } = useMemo(
    () => readEmbedThreatQuery(typeof window !== "undefined" ? window.location.search : ""),
    [],
  );
  const { projection, projectionState, projectionError } = useWorldGraphLensProjection();

  const resolution = useMemo<GraphReferenceResolution | null>(() => {
    if (!nodeId) {
      return {
        kind: "error",
        locator: "dmb-node:",
        reference: embedNodeReference("", labelHint || "Threat"),
        projectionState,
        message: "Missing nodeId query param for Threat sheet embed.",
      };
    }

    if (projectionState !== "ready" || !projection) {
      return null;
    }

    const rawNode = projection.nodes.find((node) => node.nodeId === nodeId);
    if (!rawNode) {
      return {
        kind: "error",
        locator: `dmb-node:${nodeId}`,
        reference: embedNodeReference(nodeId, labelHint || nodeId),
        projectionState,
        message: `Graph node ${nodeId} is not in the loaded World Graph projection.`,
      };
    }

    const nodeView = adaptWorldGraphNodeView(rawNode);
    const graphScope = extractExactGraphReferenceScope(projection);
    if (!graphScope) {
      return {
        kind: "error",
        locator: `dmb-node:${nodeId}`,
        reference: referenceFromGraphNode(nodeView),
        projectionState,
        message:
          "World Graph projection snapshot lacks exact world, campaign, or revision scope.",
      };
    }

    return {
      kind: "resolved_graph",
      locator: `dmb-node:${nodeId}`,
      reference: referenceFromGraphNode(nodeView),
      graphObject: buildGraphObjectCardFromNodeView(nodeView),
      graphNodeId: nodeId,
      graphScope,
      projectionState,
      message: `Resolved graph node ${nodeView.label}.`,
    };
  }, [labelHint, nodeId, projection, projectionState]);

  const title =
    (resolution && resolution.kind === "resolved_graph"
      ? resolution.graphObject.label
      : null) ||
    labelHint ||
    nodeId ||
    "Threat sheet";

  return (
    <main className="embed-threat-sheet" data-testid="embed-threat-sheet">
      <header className="embed-threat-sheet__hd">
        <h1 className="embed-threat-sheet__title">{title}</h1>
        {nodeId ? (
          <p className="embed-threat-sheet__meta mono">{nodeId}</p>
        ) : null}
      </header>

      {projectionState === "loading" || (projectionState === "ready" && !resolution) ? (
        <p className="embed-threat-sheet__status" role="status">
          Loading World Graph projection…
        </p>
      ) : null}

      {projectionState === "error" ? (
        <div className="embed-threat-sheet__error" role="alert">
          <strong>Projection failed</strong>
          <p>{projectionError || "Unable to load World Graph projection."}</p>
        </div>
      ) : null}

      {resolution?.kind === "error" ? (
        <div className="embed-threat-sheet__error" role="alert">
          <strong>Could not open Threat sheet</strong>
          <p>{resolution.message}</p>
        </div>
      ) : null}

      {resolution?.kind === "resolved_graph" ? (
        <div className="embed-threat-sheet__body">
          <ResolvedGraphObjectProjection
            resolution={resolution}
            projectionState={projectionState}
            glanceOnly={false}
            aria-label={`${resolution.graphObject.label} Threat sheet`}
          />
        </div>
      ) : null}
    </main>
  );
}
