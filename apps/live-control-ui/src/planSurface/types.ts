import type { SurfaceInteractionWorkObjectIdentity } from "../surfaceInteraction/types";
import type { ProjectionSize } from "../surfaceInteraction/projection/types";

export type SurfaceMode = "plan" | "ingest" | "build" | "combat" | "play";

export type { ProjectionSize };

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
  /** Durable workspace document id when admitted; null for local blank shells. */
  documentId?: string | null;
  /** Explicit Canvas/Edit work target; falls back to document id when omitted. */
  workObject?: SurfaceInteractionWorkObjectIdentity | null;
}

export interface PlanContextDescriptor {
  campaignId: string;
  liveSession: number;
  /**
   * Recap/tool fallback session: explicit `?session=` when present, else the live
   * packet session. Never invents live-1 as a stale memory default.
   */
  ingestSession: number;
  headerLabel: string;
}

export type PlanDocumentStatus = "active" | "discarded";
export type PlanDocumentContentStatus = "draft" | "committed";
export type PlanSourceStatusKind = "ready" | "missing" | "stale" | "unknown";

export interface PlanDocumentDescriptor {
  documentId: string;
  title: string;
  description?: string;
  campaignId: string;
  targetSession: number | null;
  targetRelpath: string | null;
  storageKey: string;
  status: PlanDocumentStatus;
  contentStatus: PlanDocumentContentStatus;
  revision: number;
  kind: "plan" | "runbook";
}

export interface PlanSessionDescriptor {
  surfaceId: "plan";
  campaignId: string;
  campaignLabel: string;
  /** Explicit `?session=` memory/graph focus; null → world-union focus (do not invent live-1). */
  memorySession: number | null;
  liveSession: number;
  sourceStatusLabel: string;
  sourceStatusKind: PlanSourceStatusKind;
  planningDocument: PlanDocumentDescriptor;
}

export interface SurfaceConfig {
  id: SurfaceMode;
  label: string;
  /** Null for non-consuming surfaces (Build empty-tools host publication). */
  context: PlanContextDescriptor | null;
  sessionDescriptor?: PlanSessionDescriptor;
  tools: SurfaceToolConfig[];
  canvas: SurfaceCanvasConfig;
  theme: SurfaceThemeConfig;
}

export interface PlanSurfaceConfig extends Omit<SurfaceConfig, "id" | "sessionDescriptor" | "context"> {
  id: "plan";
  context: PlanContextDescriptor;
  sessionDescriptor: PlanSessionDescriptor;
}
