import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import type { ReferenceResolution } from "../reference/referenceResolver";
import type { ActiveProjection, ProjectionSize, SurfaceConfig } from "../types";

interface ProjectionContextValue {
  active: ActiveProjection | null;
  activeResolution: ReferenceResolution | null;
  openTool: (toolId: string) => void;
  openContentFromChip: (ref: RunbookReferenceAttrs, resolution: ReferenceResolution, glanceOnly?: boolean) => void;
  expandContent: () => void;
  close: () => void;
}

const ProjectionContext = createContext<ProjectionContextValue | null>(null);

function contentSize(resolution: ReferenceResolution): ProjectionSize {
  if (resolution.status === "resolved") return "wide";
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
  const [activeResolution, setActiveResolution] = useState<ReferenceResolution | null>(null);

  const close = useCallback(() => {
    setActive(null);
    setActiveResolution(null);
  }, []);

  const openTool = useCallback(
    (toolId: string) => {
      const tool = config.tools.find((entry) => entry.id === toolId);
      if (!tool) return;
      setActiveResolution(null);
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
    (ref: RunbookReferenceAttrs, resolution: ReferenceResolution, glanceOnly = true) => {
      setActiveResolution(resolution);
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
      activeResolution,
      openTool,
      openContentFromChip,
      expandContent,
      close,
    }),
    [active, activeResolution, close, expandContent, openContentFromChip, openTool],
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

export function projectionContainerClass(size: ProjectionSize | undefined): string {
  if (size === "fullscreen") return "plan-projection-container plan-projection-fullscreen";
  if (size === "wide") return "plan-projection-container plan-projection-wide";
  return "plan-projection-container plan-projection-compact";
}
