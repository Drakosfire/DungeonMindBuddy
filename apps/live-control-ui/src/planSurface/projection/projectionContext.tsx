import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import type { PlanGraphProjectionState, PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";
import type { ActiveProjection, ProjectionSize, SurfaceConfig } from "../types";

interface ProjectionContextValue {
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
  expandContent: () => void;
  close: () => void;
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

  const expandContent = useCallback(() => {
    setActive((current) => {
      if (!current || current.kind !== "content") return current;
      return { ...current, size: "wide", glanceOnly: false };
    });
  }, []);

  const value = useMemo(
    () => ({
      active,
      activePlanReference,
      planProjectionState,
      openTool,
      openContentFromChip,
      expandContent,
      close,
    }),
    [active, activePlanReference, close, expandContent, openContentFromChip, openTool, planProjectionState],
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
