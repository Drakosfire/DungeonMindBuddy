/** Persist Graph Review "Load recap" selection across browser refresh. */

export interface GraphReviewAppliedSelection {
  campaignId: string;
  sessionId: string;
  manifestPath: string | null;
}

export const GRAPH_REVIEW_APPLIED_SELECTION_STORAGE_KEY =
  "dmb.graph-review.applied-selection.v1";

function canUseWindow(): boolean {
  return typeof window !== "undefined";
}

export function readAppliedSelectionFromUrl(
  search: string | null | undefined = canUseWindow() ? window.location.search : null,
): GraphReviewAppliedSelection | null {
  if (search == null) return null;
  const params = new URLSearchParams(search);
  const sessionId = params.get("session")?.trim() || "";
  const campaignId = params.get("campaign")?.trim() || "";
  if (!sessionId || !campaignId) return null;
  const manifestPath = params.get("run")?.trim() || null;
  return { campaignId, sessionId, manifestPath };
}

export function writeAppliedSelectionToUrl(
  selection: GraphReviewAppliedSelection,
  pathname: string | null | undefined = canUseWindow() ? window.location.pathname : null,
  search: string | null | undefined = canUseWindow() ? window.location.search : null,
): void {
  if (!canUseWindow()) return;
  const params = new URLSearchParams(search ?? "");
  params.set("session", selection.sessionId);
  params.set("campaign", selection.campaignId);
  if (selection.manifestPath) {
    params.set("run", selection.manifestPath);
  } else {
    params.delete("run");
  }
  const path = (pathname ?? "/plan").replace(/\/+$/, "") || "/plan";
  const surfacePath = path === "/ingest" ? "/ingest" : "/plan";
  window.history.replaceState({}, "", `${surfacePath}?${params.toString()}`);
}

export function readAppliedSelectionFromStorage(
  storage: Pick<Storage, "getItem"> | null | undefined = canUseWindow()
    ? window.sessionStorage
    : null,
): GraphReviewAppliedSelection | null {
  if (!storage) return null;
  try {
    const raw = storage.getItem(GRAPH_REVIEW_APPLIED_SELECTION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<GraphReviewAppliedSelection>;
    const campaignId = typeof parsed.campaignId === "string" ? parsed.campaignId.trim() : "";
    const sessionId = typeof parsed.sessionId === "string" ? parsed.sessionId.trim() : "";
    if (!campaignId || !sessionId) return null;
    const manifestPath =
      typeof parsed.manifestPath === "string" && parsed.manifestPath.trim()
        ? parsed.manifestPath.trim()
        : null;
    return { campaignId, sessionId, manifestPath };
  } catch {
    return null;
  }
}

export function writeAppliedSelectionToStorage(
  selection: GraphReviewAppliedSelection,
  storage: Pick<Storage, "setItem" | "removeItem"> | null | undefined = canUseWindow()
    ? window.sessionStorage
    : null,
): void {
  if (!storage) return;
  try {
    storage.setItem(GRAPH_REVIEW_APPLIED_SELECTION_STORAGE_KEY, JSON.stringify(selection));
  } catch {
    // Ignore quota / private-mode failures; URL remains the primary restore path.
  }
}

export function clearAppliedSelectionStorage(
  storage: Pick<Storage, "removeItem"> | null | undefined = canUseWindow()
    ? window.sessionStorage
    : null,
): void {
  if (!storage) return;
  try {
    storage.removeItem(GRAPH_REVIEW_APPLIED_SELECTION_STORAGE_KEY);
  } catch {
    // ignore
  }
}

/**
 * Prefer an explicit URL selection. Session storage only fills a missing `run`
 * for the same campaign/session — it never restores a load onto a bare `/ingest`.
 */
export function resolvePersistedAppliedSelection(options?: {
  search?: string | null;
  storage?: Pick<Storage, "getItem"> | null;
}): GraphReviewAppliedSelection | null {
  const fromUrl = readAppliedSelectionFromUrl(options?.search);
  if (!fromUrl) return null;
  const fromStorage = readAppliedSelectionFromStorage(options?.storage);
  if (
    fromStorage &&
    fromStorage.campaignId === fromUrl.campaignId &&
    fromStorage.sessionId === fromUrl.sessionId
  ) {
    return {
      ...fromUrl,
      manifestPath: fromUrl.manifestPath ?? fromStorage.manifestPath,
    };
  }
  return fromUrl;
}
