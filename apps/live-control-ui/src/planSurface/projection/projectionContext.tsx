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

import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import type { PlanGraphProjectionState, PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";
import type { ActiveProjection, ProjectionSize, SurfaceConfig } from "../types";

interface ProjectionContextValue {
  /** Bound surface config for the active route; null when no surface has bound. */
  surfaceConfig: SurfaceConfig | null;
  active: ActiveProjection | null;
  activePlanReference: PlanReferenceResolution | null;
  planProjectionState: PlanGraphProjectionState | null;
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
  /** R10a: bind/unbind the active surface's toolbox config. */
  bindSurfaceConfig: (config: SurfaceConfig | null) => void;
}

const ProjectionContext = createContext<ProjectionContextValue | null>(null);

function contentSize(resolution: PlanReferenceResolution): ProjectionSize {
  if (resolution.kind === "graph-node" || resolution.kind === "corpus-index") return "wide";
  return "compact";
}

function surfaceConfigKey(config: SurfaceConfig | null): string | null {
  if (!config) return null;
  return [
    config.id,
    config.context.campaignId,
    config.context.ingestSession,
    config.canvas.documentId ?? "",
    config.tools.map((tool) => tool.id).join(","),
  ].join("|");
}

export function ProjectionProvider({
  config: propConfig,
  children,
}: {
  /** Optional initial/test config. App-scoped host omits this; surfaces bind via useBindProjectionSurface. */
  config?: SurfaceConfig;
  children: ReactNode;
}) {
  const [boundConfig, setBoundConfig] = useState<SurfaceConfig | null>(propConfig ?? null);
  const [active, setActive] = useState<ActiveProjection | null>(null);
  const [activePlanReference, setActivePlanReference] = useState<PlanReferenceResolution | null>(null);
  const [planProjectionState, setPlanProjectionState] = useState<PlanGraphProjectionState | null>(null);
  const previousKeyRef = useRef<string | null>(surfaceConfigKey(propConfig ?? null));

  const close = useCallback(() => {
    setActive(null);
    setActivePlanReference(null);
    setPlanProjectionState(null);
  }, []);

  const bindSurfaceConfig = useCallback((config: SurfaceConfig | null) => {
    setBoundConfig(config);
  }, []);

  // Keep prop-driven config (unit tests) in sync.
  useEffect(() => {
    if (propConfig !== undefined) {
      setBoundConfig(propConfig);
    }
  }, [propConfig]);

  // Clear selected projection when the bound surface context changes.
  useEffect(() => {
    const nextKey = surfaceConfigKey(boundConfig);
    if (previousKeyRef.current !== nextKey) {
      previousKeyRef.current = nextKey;
      setActive(null);
      setActivePlanReference(null);
      setPlanProjectionState(null);
    }
  }, [boundConfig]);

  const openTool = useCallback(
    (toolId: string) => {
      const tool = boundConfig?.tools.find((entry) => entry.id === toolId);
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
    [boundConfig?.tools],
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

  const value = useMemo(
    () => ({
      surfaceConfig: boundConfig,
      active,
      activePlanReference,
      planProjectionState,
      openTool,
      openContentFromChip,
      openPlanReferenceResolution,
      expandContent,
      close,
      bindSurfaceConfig,
    }),
    [
      active,
      activePlanReference,
      bindSurfaceConfig,
      boundConfig,
      close,
      expandContent,
      openContentFromChip,
      openPlanReferenceResolution,
      openTool,
      planProjectionState,
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

/**
 * Bind the active route's SurfaceConfig into the app-scoped projection host.
 * Clears the binding (and closes the active projection) on unmount.
 */
export function useBindProjectionSurface(config: SurfaceConfig | null): void {
  const { bindSurfaceConfig } = useProjection();
  const key = surfaceConfigKey(config);

  useEffect(() => {
    bindSurfaceConfig(config);
    return () => {
      bindSurfaceConfig(null);
    };
    // Intentionally key on stable surface identity, not object identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bindSurfaceConfig, key]);
}

export function projectionContainerClass(size: ProjectionSize | undefined): string {
  if (size === "fullscreen") return "plan-projection-container plan-projection-fullscreen";
  if (size === "wide") return "plan-projection-container plan-projection-wide";
  return "plan-projection-container plan-projection-compact";
}
