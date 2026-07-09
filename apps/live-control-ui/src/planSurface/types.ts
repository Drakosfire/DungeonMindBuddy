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

export type PlanDocumentStatus = "local_draft" | "durable" | "missing" | "unknown";
export type PlanSourceStatusKind = "ready" | "missing" | "stale" | "unknown";

export interface PlanDocumentDescriptor {
  documentId: string;
  title: string;
  description?: string;
  targetRelpath: string;
  storageKey: string;
  status: PlanDocumentStatus;
}

export interface PlanSessionDescriptor {
  surfaceId: "plan";
  campaignId: string;
  campaignLabel: string;
  prepSession: number;
  memorySession: number;
  liveSession: number;
  sourceStatusLabel: string;
  sourceStatusKind: PlanSourceStatusKind;
  planningDocument: PlanDocumentDescriptor;
}

export interface SurfaceConfig {
  id: SurfaceMode;
  label: string;
  context: PlanContextDescriptor;
  sessionDescriptor?: PlanSessionDescriptor;
  tools: SurfaceToolConfig[];
  canvas: SurfaceCanvasConfig;
  theme: SurfaceThemeConfig;
}

export interface PlanSurfaceConfig extends Omit<SurfaceConfig, "id" | "sessionDescriptor"> {
  id: "plan";
  sessionDescriptor: PlanSessionDescriptor;
}

export interface ActiveProjection {
  kind: ProjectionKind;
  key: string;
  size: ProjectionSize;
  title: string;
  glanceOnly?: boolean;
}
