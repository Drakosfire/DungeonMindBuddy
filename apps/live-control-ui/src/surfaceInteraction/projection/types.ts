import type {
  SurfaceInteractionProjectionKind,
  SurfaceInteractionProjectionSize,
} from "../types";

/**
 * Canonical Projection host runtime types (BLD-SIH-03a).
 * Owned by surfaceInteraction/projection — not Plan.
 */
export type ProjectionKind = SurfaceInteractionProjectionKind;
export type ProjectionSize = SurfaceInteractionProjectionSize;

export interface ActiveProjection {
  kind: ProjectionKind;
  key: string;
  size: ProjectionSize;
  title: string;
  glanceOnly?: boolean;
  /**
   * Tool contribution id that launched this projection (tool kind only).
   * Distinct from `key`, which is the Projection descriptor id. Host navigation
   * compares against this when present so Tool ID ≠ Projection ID stays truthful.
   */
  launchingToolId?: string;
}

/** Neutral host navigation item (presentation only). */
export interface ProjectionHostNavigationItem {
  id: string;
  label: string;
}

/** Neutral host theme presentation. */
export interface ProjectionHostTheme {
  themeId?: string;
  tokens?: Readonly<Record<string, string>>;
}

/** Neutral host chrome copy. */
export interface ProjectionHostLabels {
  toggleTitle: string;
  closedDrawerLabel: string;
  navigationLabel: string;
  closeLabel: string;
  toolKicker: string;
  contentKicker: string;
  toolTitle: string;
  contentTitle: string;
}
