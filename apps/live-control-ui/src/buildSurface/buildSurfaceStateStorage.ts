/**
 * Explicit Build surface checkpoint (UI + TipTap draft).
 * Not a durable Markdown commit and not an SIH lease publication.
 */

export const BUILD_SURFACE_STATE_SCHEMA = "dmb_build_surface_state_v1" as const;

export interface BuildSurfaceUiState {
  isLocked: boolean;
  isEditDockOpen: boolean;
  graphRefSearchQuery: string;
  activeToolId: string | null;
  activeGraphNodeId: string | null;
}

export interface BuildSurfaceStateSnapshot {
  schema: typeof BUILD_SURFACE_STATE_SCHEMA;
  surfaceId: "build";
  documentId: string;
  updatedAt: string;
  ui: BuildSurfaceUiState;
  /** TipTap JSON draft frozen at checkpoint time. */
  draft: { tiptap_json: unknown } | null;
}

export function buildSurfaceStateStorageKey(documentId: string): string {
  return `dmb.buildSurfaceState.${documentId}`;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function buildBuildSurfaceStateSnapshot(input: {
  documentId: string;
  ui: BuildSurfaceUiState;
  draftJson?: unknown | null;
  now?: string;
}): BuildSurfaceStateSnapshot {
  return {
    schema: BUILD_SURFACE_STATE_SCHEMA,
    surfaceId: "build",
    documentId: input.documentId,
    updatedAt: input.now ?? new Date().toISOString(),
    ui: {
      isLocked: input.ui.isLocked,
      isEditDockOpen: input.ui.isEditDockOpen,
      graphRefSearchQuery: input.ui.graphRefSearchQuery,
      activeToolId: input.ui.activeToolId,
      activeGraphNodeId: input.ui.activeGraphNodeId,
    },
    draft:
      input.draftJson === undefined || input.draftJson === null
        ? null
        : { tiptap_json: input.draftJson },
  };
}

export function writeBuildSurfaceState(
  storage: Pick<Storage, "setItem">,
  snapshot: BuildSurfaceStateSnapshot,
): void {
  storage.setItem(buildSurfaceStateStorageKey(snapshot.documentId), JSON.stringify(snapshot));
}

export function readBuildSurfaceState(
  storage: Pick<Storage, "getItem">,
  documentId: string,
): BuildSurfaceStateSnapshot | null {
  const raw = storage.getItem(buildSurfaceStateStorageKey(documentId));
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isObject(parsed)) return null;
    if (parsed.schema !== BUILD_SURFACE_STATE_SCHEMA) return null;
    if (parsed.surfaceId !== "build") return null;
    if (parsed.documentId !== documentId) return null;
    if (typeof parsed.updatedAt !== "string") return null;
    if (!isObject(parsed.ui)) return null;
    const ui = parsed.ui;
    if (typeof ui.isLocked !== "boolean") return null;
    if (typeof ui.isEditDockOpen !== "boolean") return null;
    if (typeof ui.graphRefSearchQuery !== "string") return null;
    if (ui.activeToolId !== null && typeof ui.activeToolId !== "string") return null;
    if (ui.activeGraphNodeId !== null && typeof ui.activeGraphNodeId !== "string") return null;
    let draft: BuildSurfaceStateSnapshot["draft"] = null;
    if (parsed.draft !== null && parsed.draft !== undefined) {
      if (!isObject(parsed.draft) || !("tiptap_json" in parsed.draft)) return null;
      draft = { tiptap_json: parsed.draft.tiptap_json };
    }
    return {
      schema: BUILD_SURFACE_STATE_SCHEMA,
      surfaceId: "build",
      documentId,
      updatedAt: parsed.updatedAt,
      ui: {
        isLocked: ui.isLocked,
        isEditDockOpen: ui.isEditDockOpen,
        graphRefSearchQuery: ui.graphRefSearchQuery,
        activeToolId: ui.activeToolId,
        activeGraphNodeId: ui.activeGraphNodeId,
      },
      draft,
    };
  } catch {
    return null;
  }
}

export function clearBuildSurfaceState(
  storage: Pick<Storage, "removeItem">,
  documentId: string,
): void {
  storage.removeItem(buildSurfaceStateStorageKey(documentId));
}
