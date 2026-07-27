import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import type { PlanGraphProjectionState, PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";
import type { ActiveProjection, ProjectionSize, SurfaceConfig } from "../types";
import type {
  GraphReviewDiagnosticsProjectionPayload,
  PlanReferenceProjectionBinding,
  RegisterableToolProjectionId,
  ToolProjectionPayloadMap,
} from "./projectionBindings";
import { GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID } from "./projectionBindings";

interface BindingRegistration<T> {
  token: symbol;
  value: T;
}

interface ProjectionContextValue {
  active: ActiveProjection | null;
  activePlanReference: PlanReferenceResolution | null;
  planProjectionState: PlanGraphProjectionState | null;
  planReferenceBinding: PlanReferenceProjectionBinding | null;
  graphReviewDiagnosticsPayload: GraphReviewDiagnosticsProjectionPayload | null;
  openTool: (toolId: string) => void;
  openContentFromChip: (
    ref: RunbookReferenceAttrs,
    resolution: PlanReferenceResolution,
    glanceOnly?: boolean,
    projectionState?: PlanGraphProjectionState | null,
  ) => void;
  /** Open a Plan reference resolution without a chip click (e.g. relationship traversal). */
  openPlanReferenceResolution: (
    resolution: PlanReferenceResolution,
    projectionState?: PlanGraphProjectionState | null,
  ) => void;
  expandContent: () => void;
  close: () => void;
  registerPlanReferenceBinding: (binding: PlanReferenceProjectionBinding) => () => void;
  registerToolProjectionPayload: <K extends RegisterableToolProjectionId>(
    toolId: K,
    payload: ToolProjectionPayloadMap[K],
  ) => () => void;
}

const ProjectionContext = createContext<ProjectionContextValue | null>(null);

function contentSize(resolution: PlanReferenceResolution): ProjectionSize {
  if (resolution.kind === "graph-node" || resolution.kind === "corpus-index") return "wide";
  return "compact";
}

export function ProjectionProvider({
  config,
  children,
}: {
  config: SurfaceConfig;
  children: ReactNode;
}) {
  const [active, setActive] = useState<ActiveProjection | null>(null);
  const [activePlanReference, setActivePlanReference] = useState<PlanReferenceResolution | null>(null);
  const [planProjectionState, setPlanProjectionState] = useState<PlanGraphProjectionState | null>(null);
  const [planReferenceRegistration, setPlanReferenceRegistration] = useState<
    BindingRegistration<PlanReferenceProjectionBinding> | null
  >(null);
  const [diagnosticsRegistration, setDiagnosticsRegistration] = useState<
    BindingRegistration<GraphReviewDiagnosticsProjectionPayload> | null
  >(null);
  const planReferenceRegistrationRef = useRef(planReferenceRegistration);
  planReferenceRegistrationRef.current = planReferenceRegistration;

  const close = useCallback(() => {
    setActive(null);
    setActivePlanReference(null);
    setPlanProjectionState(null);
  }, []);

  const openTool = useCallback(
    (toolId: string) => {
      const tool = config.tools.find((entry) => entry.id === toolId);
      if (!tool) return;
      setActivePlanReference(null);
      setPlanProjectionState(null);
      setActive({
        kind: "tool",
        key: toolId,
        size: tool.size,
        title: tool.label,
      });
    },
    [config.tools],
  );

  const openContentFromChip = useCallback(
    (
      ref: RunbookReferenceAttrs,
      resolution: PlanReferenceResolution,
      glanceOnly = true,
      projectionState: PlanGraphProjectionState | null = resolution.graphProjectionState ?? null,
    ) => {
      setActivePlanReference(resolution);
      setPlanProjectionState(projectionState);
      setActive({
        kind: "content",
        key: ref.refType,
        size: glanceOnly ? "compact" : contentSize(resolution),
        title: ref.label,
        glanceOnly,
      });
    },
    [],
  );

  const openPlanReferenceResolution = useCallback(
    (
      resolution: PlanReferenceResolution,
      projectionState: PlanGraphProjectionState | null = resolution.graphProjectionState ?? null,
    ) => {
      const title =
        resolution.graphObject?.label
        ?? resolution.fallback?.ref.label
        ?? resolution.locator
        ?? "Related object";
      setActivePlanReference(resolution);
      setPlanProjectionState(projectionState);
      setActive({
        kind: "content",
        key: resolution.refType ?? resolution.graphNodeId ?? "plan-reference",
        size: contentSize(resolution),
        title,
        glanceOnly: false,
      });
    },
    [],
  );

  const expandContent = useCallback(() => {
    setActive((current) => {
      if (!current || current.kind !== "content") return current;
      return { ...current, size: "wide", glanceOnly: false };
    });
  }, []);

  const registerPlanReferenceBinding = useCallback((binding: PlanReferenceProjectionBinding) => {
    const token = Symbol("plan-reference-binding");
    setPlanReferenceRegistration({ token, value: binding });
    return () => {
      setPlanReferenceRegistration((current) => (current?.token === token ? null : current));
    };
  }, []);

  const registerToolProjectionPayload = useCallback(
    <K extends RegisterableToolProjectionId>(toolId: K, payload: ToolProjectionPayloadMap[K]) => {
      if (toolId !== GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID) {
        return () => undefined;
      }
      const token = Symbol(`tool-payload:${toolId}`);
      const typedPayload = payload as GraphReviewDiagnosticsProjectionPayload;
      setDiagnosticsRegistration({ token, value: typedPayload });
      return () => {
        setDiagnosticsRegistration((current) => (current?.token === token ? null : current));
      };
    },
    [],
  );

  /**
   * Expose the registered Plan binding with open* actions gated on the active
   * registration token so a superseded adapter cannot commit after an await.
   */
  const planReferenceBinding = useMemo((): PlanReferenceProjectionBinding | null => {
    const registration = planReferenceRegistration;
    if (!registration) return null;
    const { token, value: binding } = registration;
    return {
      resolverState: binding.resolverState,
      resolveRelationship: (relationship) => binding.resolveRelationship(relationship),
      openResolvedReference: (resolution, projectionState) => {
        const current = planReferenceRegistrationRef.current;
        if (!current || current.token !== token) return;
        current.value.openResolvedReference(resolution, projectionState);
      },
      openTool: (toolId) => {
        const current = planReferenceRegistrationRef.current;
        if (!current || current.token !== token) return;
        current.value.openTool(toolId);
      },
    };
  }, [planReferenceRegistration]);

  const value = useMemo(
    () => ({
      active,
      activePlanReference,
      planProjectionState,
      planReferenceBinding,
      graphReviewDiagnosticsPayload: diagnosticsRegistration?.value ?? null,
      openTool,
      openContentFromChip,
      openPlanReferenceResolution,
      expandContent,
      close,
      registerPlanReferenceBinding,
      registerToolProjectionPayload,
    }),
    [
      active,
      activePlanReference,
      close,
      diagnosticsRegistration,
      expandContent,
      openContentFromChip,
      openPlanReferenceResolution,
      openTool,
      planProjectionState,
      planReferenceBinding,
      registerPlanReferenceBinding,
      registerToolProjectionPayload,
    ],
  );

  return <ProjectionContext.Provider value={value}>{children}</ProjectionContext.Provider>;
}

export function useProjection(): ProjectionContextValue {
  const context = useContext(ProjectionContext);
  if (!context) {
    throw new Error("useProjection must be used within ProjectionProvider");
  }
  return context;
}

export function useOptionalProjection(): ProjectionContextValue | null {
  return useContext(ProjectionContext);
}

export function projectionContainerClass(size: ProjectionSize | undefined): string {
  if (size === "fullscreen") return "plan-projection-container plan-projection-fullscreen";
  if (size === "wide") return "plan-projection-container plan-projection-wide";
  return "plan-projection-container plan-projection-compact";
}
