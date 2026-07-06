export type SurfaceMode = "plan" | "ingest" | "build" | "combat" | "play";

export type ProjectionKind = "tool" | "content";

export type ProjectionSize = "compact" | "wide" | "fullscreen";

export interface SurfaceThemeConfig {
  themeId?: string;
  tokens?: Record<string, string>;
}

export interface SurfaceToolConfig {
  id: string;
  label: string;
  size: ProjectionSize;
}

export interface SurfaceCanvasConfig {
  documentId: string;
}

export interface PlanContextDescriptor {
  campaignId: string;
  liveSession: number;
  prepSession: number;
  ingestSession: number;
  headerLabel: string;
}

export interface SurfaceConfig {
  id: SurfaceMode;
  label: string;
  context: PlanContextDescriptor;
  tools: SurfaceToolConfig[];
  canvas: SurfaceCanvasConfig;
  theme: SurfaceThemeConfig;
}

export interface ActiveProjection {
  kind: ProjectionKind;
  key: string;
  size: ProjectionSize;
  title: string;
  glanceOnly?: boolean;
}
