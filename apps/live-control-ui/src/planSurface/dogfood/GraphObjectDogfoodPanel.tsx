import { useCallback, useEffect, useMemo, useState } from "react";

import type { GraphProjectionNodeView, WorldGraphProjection } from "../../api/types";
import {
  buildGraphObjectCardFromNodeView,
  type GraphObjectCardViewModel,
} from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference";
import { extractExactGraphReferenceScope } from "../../graphReference/resolveGraphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import { useOptionalProjection } from "../projection/projectionContext";
import { buildPlanGraphObjectActions } from "../reference/buildPlanGraphObjectActions";
import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
import { adaptWorldGraphNodeForPlanCard } from "../reference/worldGraphProjectionAdapter";
import type { PlanSessionDescriptor } from "../types";
import {
  addNodeToDogfoodList,
  COVERAGE_FLAG_LABELS,
  computeGraphObjectCardCoverage,
  GRAPH_OBJECT_DOGFOOD_USEFULNESS_OPTIONS,
  isThinCardCoverage,
  markNodeViewed,
  removeNodeFromDogfoodList,
  setNodeNotes,
  setNodeUsefulness,
  type GraphObjectDogfoodState,
  type GraphObjectDogfoodUsefulness,
} from "./graphObjectDogfoodModel";
import {
  clearGraphObjectDogfoodState,
  loadGraphObjectDogfoodState,
  saveGraphObjectDogfoodState,
} from "./graphObjectDogfoodStorage";

export interface GraphObjectDogfoodPanelProps {
  sessionDescriptor: PlanSessionDescriptor;
}

function buildViewModelForNode(
  node: GraphProjectionNodeView,
  sessionDescriptor: PlanSessionDescriptor,
  projection: WorldGraphProjection | null,
): GraphObjectCardViewModel {
  const base = buildGraphObjectCardFromNodeView(node);
  const graphScope = extractExactGraphReferenceScope(projection);
  if (!graphScope) {
    return { ...base, actions: [] };
  }
  const resolution: GraphReferenceResolution = {
    kind: "resolved_graph",
    locator: `dmb-node:${node.node_id}`,
    reference: referenceFromGraphNode(node),
    graphObject: base,
    graphNodeId: node.node_id,
    graphScope,
    projectionState: null,
    message: `Resolved graph node ${node.label}.`,
  };
  return {
    ...base,
    actions: buildPlanGraphObjectActions({ resolution, sessionDescriptor }),
  };
}

function resolutionFromNode(
  node: GraphProjectionNodeView,
  sessionDescriptor: PlanSessionDescriptor,
  projectionState: GraphReferenceResolution["projectionState"],
  projection: WorldGraphProjection | null,
): GraphReferenceResolution {
  const graphScope = extractExactGraphReferenceScope(projection);
  if (!graphScope) {
    return {
      kind: "error",
      locator: `dmb-node:${node.node_id}`,
      reference: referenceFromGraphNode(node),
      projectionState: projectionState ?? null,
      message:
        "World Graph projection snapshot lacks exact world, campaign, or revision scope; dogfood open blocked.",
    };
  }
  const graphObject = buildViewModelForNode(node, sessionDescriptor, projection);
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${node.node_id}`,
    reference: referenceFromGraphNode(node),
    graphObject,
    graphNodeId: node.node_id,
    graphScope,
    projectionState: projectionState ?? null,
    message: `Resolved graph node ${node.label}.`,
  };
}

function CardCoverageBadges({ model }: { model: GraphObjectCardViewModel }) {
  const coverage = computeGraphObjectCardCoverage(model);
  const thin = isThinCardCoverage(coverage);

  return (
    <div className="graph-object-dogfood-coverage" data-testid="graph-object-dogfood-coverage">
      <p className="graph-object-dogfood-coverage-label">Card coverage</p>
      {thin ? (
        <p className="graph-object-dogfood-thin" role="status">
          Thin card — summary, relationships, or evidence missing.
        </p>
      ) : null}
      <ul className="graph-object-dogfood-coverage-list">
        {coverage.flags.map((flag) => (
          <li key={flag} className="graph-object-dogfood-coverage-flag">
            {COVERAGE_FLAG_LABELS[flag]}
          </li>
        ))}
        {coverage.missing.map((flag) => (
          <li
            key={`missing-${flag}`}
            className="graph-object-dogfood-coverage-flag graph-object-dogfood-coverage-flag--missing"
          >
            Missing: {COVERAGE_FLAG_LABELS[flag].replace(/^Has /, "").toLowerCase()}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function GraphObjectDogfoodPanel({ sessionDescriptor }: GraphObjectDogfoodPanelProps) {
  const projectionApi = useOptionalProjection();
  const { projection, projectionState, projectionError } = usePlanGraphReferenceResolver();

  const [state, setState] = useState<GraphObjectDogfoodState>(() =>
    loadGraphObjectDogfoodState(window.localStorage, sessionDescriptor),
  );

  useEffect(() => {
    setState(loadGraphObjectDogfoodState(window.localStorage, sessionDescriptor));
  }, [sessionDescriptor]);

  const persist = useCallback(
    (next: GraphObjectDogfoodState) => {
      setState(next);
      saveGraphObjectDogfoodState(window.localStorage, sessionDescriptor, next);
    },
    [sessionDescriptor],
  );

  const addedNodes = useMemo(() => {
    const byId = new Map(
      (projection?.nodes ?? []).map((node) => [
        node.nodeId,
        adaptWorldGraphNodeForPlanCard(node),
      ]),
    );
    return state.addedNodeIds
      .map((nodeId) => byId.get(nodeId) ?? null)
      .filter((node): node is GraphProjectionNodeView => Boolean(node));
  }, [projection, state.addedNodeIds]);

  const missingAddedIds = useMemo(() => {
    const byId = new Set((projection?.nodes ?? []).map((node) => node.nodeId));
    return state.addedNodeIds.filter((nodeId) => !byId.has(nodeId));
  }, [projection, state.addedNodeIds]);

  const activeViewedNodeId =
    projectionApi?.activeGraphReference?.kind === "resolved_graph"
      ? projectionApi.activeGraphReference.graphNodeId
      : null;

  const handleRemove = (nodeId: string) => {
    persist(removeNodeFromDogfoodList(state, nodeId));
  };

  const handleView = (node: GraphProjectionNodeView) => {
    if (!projectionApi) return;
    const next = markNodeViewed(state, node.node_id);
    persist(next);
    projectionApi.openGraphReference({
      resolution: resolutionFromNode(node, sessionDescriptor, projectionState, projection),
      projectionState,
    });
  };

  const handleUsefulness = (nodeId: string, usefulness: GraphObjectDogfoodUsefulness) => {
    persist(setNodeUsefulness(state, nodeId, usefulness));
  };

  const handleNotes = (nodeId: string, notes: string) => {
    persist(setNodeNotes(state, nodeId, notes));
  };

  const handleClear = () => {
    clearGraphObjectDogfoodState(window.localStorage, sessionDescriptor);
    setState(loadGraphObjectDogfoodState(window.localStorage, sessionDescriptor));
  };

  const handleAddActive = () => {
    if (!activeViewedNodeId) return;
    persist(addNodeToDogfoodList(state, activeViewedNodeId));
  };

  return (
    <section
      className="graph-object-dogfood-panel"
      aria-label="Graph object dogfood"
      data-testid="graph-object-dogfood-panel"
    >
      <header className="graph-object-dogfood-header">
        <h3 className="graph-object-dogfood-title">Graph objects</h3>
        <p className="graph-object-dogfood-subtitle">
          Use Edit → World Graph objects to find and open cards. This panel keeps the local dogfood
          list, coverage, usefulness, and notes. Remove never deletes graph or corpus memory.
        </p>
      </header>

      {projectionState === "loading" ? (
        <p className="graph-object-dogfood-status" role="status">
          Loading World Graph projection…
        </p>
      ) : null}
      {projectionState === "error" ? (
        <p className="graph-object-dogfood-status graph-object-dogfood-status--error" role="alert">
          Could not load graph projection{projectionError ? `: ${projectionError}` : "."}
        </p>
      ) : null}
      {projectionState === "unavailable" ? (
        <p className="graph-object-dogfood-status" role="status">
          Graph projection unavailable for this session.
        </p>
      ) : null}

      {projectionState === "ready" ? (
        <div className="graph-object-dogfood-section">
          <h4 className="graph-object-dogfood-section-title">Dogfood list</h4>
          {activeViewedNodeId && !state.addedNodeIds.includes(activeViewedNodeId) ? (
            <div className="graph-object-dogfood-active-add">
              <p>Viewing a related card that is not on the dogfood list.</p>
              <button
                type="button"
                className="graph-object-dogfood-button"
                onClick={handleAddActive}
              >
                Add this card to dogfood list
              </button>
            </div>
          ) : null}

          {addedNodes.length === 0 && missingAddedIds.length === 0 ? (
            <p className="graph-object-dogfood-empty">No cards on the dogfood list yet.</p>
          ) : (
            <ul
              className="graph-object-dogfood-collection"
              data-testid="graph-object-dogfood-collection"
            >
              {addedNodes.map((node) => {
                const model = buildViewModelForNode(node, sessionDescriptor, projection);
                const usefulness = state.usefulnessByNodeId[node.node_id] ?? "unknown";
                const notes = state.notesByNodeId[node.node_id] ?? "";
                return (
                  <li key={node.node_id} className="graph-object-dogfood-card-item">
                    <div className="graph-object-dogfood-card-header">
                      <div>
                        <strong>{node.label}</strong>
                        <span className="graph-object-dogfood-node-meta">
                          {node.kind}
                          {node.role ? ` · ${node.role}` : ""}
                        </span>
                      </div>
                      <div className="graph-object-dogfood-card-actions">
                        <button
                          type="button"
                          className="graph-object-dogfood-button graph-object-dogfood-button--primary"
                          onClick={() => handleView(node)}
                        >
                          View card
                        </button>
                        <button
                          type="button"
                          className="graph-object-dogfood-button"
                          onClick={() => handleRemove(node.node_id)}
                        >
                          Remove from dogfood list
                        </button>
                      </div>
                    </div>

                    <CardCoverageBadges model={model} />

                    <label className="graph-object-dogfood-field-label">
                      Usefulness
                      <select
                        value={usefulness}
                        aria-label={`Usefulness for ${node.label}`}
                        onChange={(event) =>
                          handleUsefulness(
                            node.node_id,
                            event.target.value as GraphObjectDogfoodUsefulness,
                          )
                        }
                      >
                        {GRAPH_OBJECT_DOGFOOD_USEFULNESS_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="graph-object-dogfood-field-label">
                      Notes
                      <textarea
                        rows={2}
                        value={notes}
                        aria-label={`Notes for ${node.label}`}
                        placeholder="Does this card tell you what it is? Why it matters? Anything wrong or missing?"
                        onChange={(event) => handleNotes(node.node_id, event.target.value)}
                      />
                    </label>
                  </li>
                );
              })}
              {missingAddedIds.map((nodeId) => (
                <li
                  key={nodeId}
                  className="graph-object-dogfood-card-item graph-object-dogfood-card-item--missing"
                >
                  <p>
                    Previously added node <code>{nodeId}</code> is not in the current projection.
                  </p>
                  <button
                    type="button"
                    className="graph-object-dogfood-button"
                    onClick={() => handleRemove(nodeId)}
                  >
                    Remove from dogfood list
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      <div className="graph-object-dogfood-footer">
        <button type="button" className="graph-object-dogfood-button" onClick={handleClear}>
          Clear graph object dogfood list
        </button>
        <p className="graph-object-dogfood-footer-note">
          Clears local dogfood list, usefulness, and notes only. Does not delete graph nodes or
          corpus markdown.
        </p>
      </div>
    </section>
  );
}
