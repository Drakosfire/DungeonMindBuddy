import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  useOptionalWorldGraphLensProjection,
  type WorldGraphLensProjectionValue,
} from "../../graphLens/useWorldGraphLensProjection";
import { GraphNodeChipRuntimeProvider } from "../../graphReference/GraphNodeChipRuntime";
import { ResolvedGraphObjectProjection } from "../../graphReference/ResolvedGraphObjectProjection";
import { extractExactGraphReferenceScope, resolveGraphReference } from "../../graphReference/resolveGraphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import { GRAPH_NODE_REF_TYPE, isValidGraphNodeId } from "../../tiptap/references/runbookReferences";
import { adaptWorldGraphNodeViewMap } from "../../worldGraph/worldGraphNodeViewAdapter";

interface ActivationRequest {
  nodeId: string;
  ownerWorldId: string;
  projectionRequestKey: string | null;
  nativeWorldId: string | null;
  revisionId: string | null;
}

interface WorldPlanGraphReferenceActivationValue {
  activateNode: (nodeId: string) => void;
}

const ActivationContext = createContext<WorldPlanGraphReferenceActivationValue | null>(null);

export function useWorldPlanGraphReferenceActivation(): WorldPlanGraphReferenceActivationValue {
  const value = useContext(ActivationContext);
  if (!value) throw new Error("World Plan Graph reference activation requires its provider.");
  return value;
}

function resolutionForRequest(
  worldId: string,
  request: ActivationRequest,
  graph: WorldGraphLensProjectionValue | null,
): GraphReferenceResolution {
  const { nodeId } = request;
  const projectionState = graph?.projectionState ?? "unavailable";
  const projection = graph?.projection ?? null;
  const ref = { kind: "ref" as const, refType: GRAPH_NODE_REF_TYPE, refId: nodeId, label: nodeId };
  if (!isValidGraphNodeId(nodeId)) {
    return {
      kind: "error", locator: nodeId || "unknown", reference: ref, projectionState,
      message: "This Graph reference has an invalid node ID.",
    };
  }
  if (graph && (!graph.request || !request.projectionRequestKey || graph.request.worldId !== worldId
    || graph.requestKey !== request.projectionRequestKey
    || graph.request.scopeMode !== "world" || graph.request.campaignId !== "")) {
    return {
      kind: "error", locator: nodeId, reference: ref, projectionState,
      message: "The selected World Graph request changed or does not match this World. Close and reopen this reference.",
    };
  }
  if (projectionState === "loading") {
    return {
      kind: "unresolved", locator: nodeId, reference: ref, projectionState,
      message: "The selected World Graph is loading. Try opening this reference again shortly.",
    };
  }
  if (projectionState === "unavailable") {
    return {
      kind: "unresolved", locator: nodeId, reference: ref, projectionState,
      message: "The selected World Graph is unavailable, so this reference cannot be inspected.",
    };
  }
  if (projectionState === "error") {
    return {
      kind: "error", locator: nodeId, reference: ref, projectionState,
      message: "The selected World Graph could not be loaded. This reference was not resolved.",
    };
  }
  if (!graph?.request || !request.projectionRequestKey) {
    return {
      kind: "error", locator: nodeId, reference: ref, projectionState,
      message: "The selected World Graph request changed or does not match this World. Close and reopen this reference.",
    };
  }
  if (!projection) {
    return {
      kind: "error", locator: nodeId, reference: ref, projectionState,
      message: "The selected World Graph is marked ready but has no projection.",
    };
  }

  const scope = extractExactGraphReferenceScope(projection);
  if (!scope || scope.scopeMode !== "world" || scope.campaignId !== "") {
    return {
      kind: "error", locator: nodeId, reference: ref, projectionState,
      message: "The loaded Graph projection does not match the selected World.",
    };
  }
  if (request.revisionId && scope.revisionId !== request.revisionId) {
    return {
      kind: "error", locator: nodeId, reference: ref, projectionState,
      message: "The selected World Graph head changed while this reference was open. Close and reopen it to inspect the new head.",
    };
  }
  if (request.nativeWorldId && scope.worldId !== request.nativeWorldId) {
    return {
      kind: "error", locator: nodeId, reference: ref, projectionState,
      message: "The selected World Graph binding changed while this reference was open. Close and reopen it to inspect the current object.",
    };
  }

  const resolution = resolveGraphReference({ ref, projection, projectionState: "ready" });
  if (resolution.kind === "unresolved") {
    return {
      ...resolution,
      message: `Node ${nodeId} was not found in the selected World Graph.`,
    };
  }
  return resolution;
}

function nativeScopeForManagedRequest(
  worldId: string,
  graph: WorldGraphLensProjectionValue | null,
): ReturnType<typeof extractExactGraphReferenceScope> {
  if (graph?.projectionState !== "ready" || graph.request?.worldId !== worldId
    || graph.request.scopeMode !== "world" || graph.request.campaignId !== "" || !graph.projection) return null;
  const scope = extractExactGraphReferenceScope(graph.projection);
  return scope?.scopeMode === "world" && scope.campaignId === "" ? scope : null;
}

export function WorldPlanGraphReferenceActivationProvider({
  worldId,
  children,
}: {
  worldId: string;
  children: ReactNode;
}) {
  const graph = useOptionalWorldGraphLensProjection();
  const [request, setRequest] = useState<ActivationRequest | null>(null);
  const requestRef = useRef<ActivationRequest | null>(request);
  requestRef.current = request;
  const triggerRef = useRef<HTMLElement | null>(null);
  const triggerNodeIdRef = useRef<string | null>(null);
  const triggerOwnerWorldIdRef = useRef<string | null>(null);
  const currentOwnerWorldIdRef = useRef(worldId);
  currentOwnerWorldIdRef.current = worldId;
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const hadRequestRef = useRef(false);

  const activateNode = useCallback((nodeId: string) => {
    if (!request || request.ownerWorldId !== worldId) {
      triggerRef.current = typeof document !== "undefined" && document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
      triggerNodeIdRef.current = nodeId;
      triggerOwnerWorldIdRef.current = worldId;
    }
    const nativeScope = nativeScopeForManagedRequest(worldId, graph);
    setRequest({
      nodeId,
      ownerWorldId: worldId,
      projectionRequestKey: graph?.requestKey ?? null,
      nativeWorldId: nativeScope?.worldId ?? null,
      revisionId: nativeScope?.revisionId ?? null,
    });
  }, [graph?.projection, graph?.projectionState, graph?.requestKey, request, worldId]);

  const currentRequest = request?.ownerWorldId === worldId ? request : null;
  const resolution = useMemo(
    () => currentRequest
      ? resolutionForRequest(worldId, currentRequest, graph)
      : null,
    [currentRequest, graph, worldId],
  );

  useEffect(() => {
    if (!currentRequest || resolution?.kind !== "resolved_graph"
      || (currentRequest.revisionId && currentRequest.nativeWorldId)) return;
    setRequest((previous) => previous && previous.nodeId === currentRequest.nodeId
      && previous.ownerWorldId === currentRequest.ownerWorldId
      && previous.projectionRequestKey === currentRequest.projectionRequestKey
      ? {
        ...previous,
        nativeWorldId: previous.nativeWorldId ?? resolution.graphScope.worldId,
        revisionId: previous.revisionId ?? resolution.graphScope.revisionId,
      }
      : previous);
  }, [currentRequest, resolution]);

  useEffect(() => {
    if (currentRequest) {
      hadRequestRef.current = true;
      closeButtonRef.current?.focus();
      return;
    }
    if (hadRequestRef.current) {
      hadRequestRef.current = false;
      const triggerOwnerWorldId = triggerOwnerWorldIdRef.current;
      if (triggerOwnerWorldId !== worldId) return;
      let trigger = triggerRef.current;
      if (!trigger?.isConnected && triggerNodeIdRef.current) {
        trigger = Array.from(document.querySelectorAll<HTMLElement>("[data-graph-node-id]"))
          .find((candidate) => candidate.dataset.graphNodeId === triggerNodeIdRef.current) ?? null;
      }
      window.setTimeout(() => {
        if (currentOwnerWorldIdRef.current === triggerOwnerWorldId && requestRef.current === null && trigger?.isConnected) {
          trigger.focus({ preventScroll: true });
        }
      }, 0);
    }
  }, [currentRequest, worldId]);

  const close = useCallback(() => setRequest(null), []);
  const requestMatchesOwner = graph?.request?.worldId === worldId
    && graph.request.scopeMode === "world"
    && graph.request.campaignId === "";
  const candidateProjection = graph?.projectionState === "ready" && requestMatchesOwner ? graph.projection : null;
  const candidateScope = candidateProjection ? extractExactGraphReferenceScope(candidateProjection) : null;
  const readyProjection = candidateScope?.scopeMode === "world" && candidateScope.campaignId === ""
    ? candidateProjection
    : null;
  const nodeViews = useMemo(
    () => readyProjection ? adaptWorldGraphNodeViewMap(
      Object.fromEntries(readyProjection.nodes.map((node) => [node.nodeId, node])),
    ) : {},
    [readyProjection],
  );
  const scope = readyProjection ? extractExactGraphReferenceScope(readyProjection) : null;
  const runtime = useMemo(() => ({
    nodeViews,
    activeNodeId: currentRequest?.nodeId ?? null,
    onSelectNode: activateNode,
    exactGraphScope: scope?.scopeMode === "world" && scope.campaignId === "" ? scope : null,
  }), [activateNode, currentRequest?.nodeId, nodeViews, scope, worldId]);

  return (
    <ActivationContext.Provider value={{ activateNode }}>
      <GraphNodeChipRuntimeProvider value={runtime}>
        {children}
        {currentRequest && resolution ? (
          <section className="world-plan-graph-reference-inspector" role="dialog" aria-modal="false" aria-label="World Graph object">
            <header>
              <h2>{resolution.kind === "resolved_graph" ? resolution.graphObject.label : currentRequest.nodeId}</h2>
              <button ref={closeButtonRef} type="button" onClick={close}>Close</button>
            </header>
            {resolution.kind === "resolved_graph" ? (
              <ResolvedGraphObjectProjection
                resolution={resolution}
                originSurface="plan"
                mode="plan"
                aria-label={`${resolution.graphObject.label} World Graph object`}
              />
            ) : (
              <p role="status">{resolution.message ?? "This Graph reference could not be resolved in the selected World."}</p>
            )}
          </section>
        ) : null}
      </GraphNodeChipRuntimeProvider>
    </ActivationContext.Provider>
  );
}
