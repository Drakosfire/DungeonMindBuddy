import { useCallback, useEffect, useMemo, useState } from "react";

import type { GraphProjectionNodeView } from "../../api/types";
import {
  buildGraphObjectCardFromNodeView,
  type GraphObjectCardViewModel,
} from "../../graphObjectCard";
import { useOptionalProjection } from "../projection/projectionContext";
import { buildPlanGraphObjectActions } from "../reference/buildPlanGraphObjectActions";
import type { PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";
import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
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

function sortNodes(nodes: GraphProjectionNodeView[]): GraphProjectionNodeView[] {
  return [...nodes].sort((a, b) => {
    const kindCmp = String(a.kind).localeCompare(String(b.kind));
    if (kindCmp !== 0) return kindCmp;
    return String(a.label).localeCompare(String(b.label));
  });
}

function buildViewModelForNode(
  node: GraphProjectionNodeView,
  sessionDescriptor: PlanSessionDescriptor,
): GraphObjectCardViewModel {
  const base = buildGraphObjectCardFromNodeView(node);
  const resolution: PlanReferenceResolution = {
    kind: "graph-node",
    locator: `dmb-node:${node.node_id}`,
    refType: node.kind,
    refId: node.node_id,
    graphObject: base,
    graphNodeId: node.node_id,
    fallback: null,
    source: "union-supergraph",
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
  projectionState: PlanReferenceResolution["graphProjectionState"],
): PlanReferenceResolution {
  const graphObject = buildViewModelForNode(node, sessionDescriptor);
  return {
    kind: "graph-node",
    locator: `dmb-node:${node.node_id}`,
    refType: node.kind,
    refId: node.node_id,
    graphObject,
    graphNodeId: node.node_id,
    fallback: null,
    source: "union-supergraph",
    message: `Resolved graph node ${node.label}.`,
    graphProjectionState: projectionState ?? null,
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
  const { projection, projectionState, projectionError } =
    usePlanGraphReferenceResolver(sessionDescriptor);

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

  const availableNodes = useMemo(
    () => sortNodes(Object.values(projection?.node_views ?? {})),
    [projection],
  );

  const addedNodes = useMemo(() => {
    const byId = projection?.node_views ?? {};
    return state.addedNodeIds
      .map((nodeId) => byId[nodeId] ?? null)
      .filter((node): node is GraphProjectionNodeView => Boolean(node));
  }, [projection, state.addedNodeIds]);

  const missingAddedIds = useMemo(() => {
    const byId = projection?.node_views ?? {};
    return state.addedNodeIds.filter((nodeId) => !byId[nodeId]);
  }, [projection, state.addedNodeIds]);

  const activeViewedNodeId =
    projectionApi?.activePlanReference?.kind === "graph-node"
      ? projectionApi.activePlanReference.graphNodeId
      : null;

  const handleAdd = (nodeId: string) => {
    persist(addNodeToDogfoodList(state, nodeId));
  };

  const handleRemove = (nodeId: string) => {
    persist(removeNodeFromDogfoodList(state, nodeId));
  };

  const handleView = (node: GraphProjectionNodeView) => {
    if (!projectionApi) return;
    const next = markNodeViewed(state, node.node_id);
    persist(next);
    projectionApi.openPlanReferenceResolution(
      resolutionFromNode(node, sessionDescriptor, projectionState),
      projectionState,
    );
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
          Add projected campaign objects to a local dogfood list, view them through the real Plan
          card path, remove them from the list, and record whether they are useful. Remove never
          deletes graph or corpus memory.
        </p>
      </header>

      {projectionState === "loading" ? (
        <p className="graph-object-dogfood-status" role="status">
          Loading Union Supergraph projection…
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
        <>
          <div className="graph-object-dogfood-section">
            <h4 className="graph-object-dogfood-section-title">Available projection nodes</h4>
            {availableNodes.length === 0 ? (
              <p className="graph-object-dogfood-empty">No nodes in the current projection.</p>
            ) : (
              <ul className="graph-object-dogfood-node-list" data-testid="graph-object-dogfood-available">
                {availableNodes.map((node) => {
                  const alreadyAdded = state.addedNodeIds.includes(node.node_id);
                  return (
                    <li key={node.node_id} className="graph-object-dogfood-node-row">
                      <div className="graph-object-dogfood-node-copy">
                        <strong>{node.label}</strong>
                        <span className="graph-object-dogfood-node-meta">
                          {node.kind}
                          {node.role ? ` · ${node.role}` : ""}
                        </span>
                      </div>
                      <button
                        type="button"
                        className="graph-object-dogfood-button"
                        disabled={alreadyAdded}
                        onClick={() => handleAdd(node.node_id)}
                      >
                        {alreadyAdded ? "Added" : "Add card"}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="graph-object-dogfood-section">
            <h4 className="graph-object-dogfood-section-title">Dogfood list</h4>
            {activeViewedNodeId && !state.addedNodeIds.includes(activeViewedNodeId) ? (
              <div className="graph-object-dogfood-active-add">
                <p>
                  Viewing a related card that is not on the dogfood list.
                </p>
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
              <ul className="graph-object-dogfood-collection" data-testid="graph-object-dogfood-collection">
                {addedNodes.map((node) => {
                  const model = buildViewModelForNode(node, sessionDescriptor);
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
                  <li key={nodeId} className="graph-object-dogfood-card-item graph-object-dogfood-card-item--missing">
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
        </>
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
