/** Persist Graph Review "Load recap" selection across browser refresh. */

export interface GraphReviewAppliedSelection {
  campaignId: string;
  sessionId: string;
  runId: string | null;
}

export const GRAPH_REVIEW_APPLIED_SELECTION_STORAGE_KEY =
  "dmb.graph-review.applied-selection.v2";

const LEGACY_STORAGE_KEY = "dmb.graph-review.applied-selection.v1";

function canUseWindow(): boolean {
  return typeof window !== "undefined";
}

export function isInadmissibleRunIdentity(value: string | null | undefined): boolean {
  const trimmed = value?.trim() ?? "";
  if (!trimmed) return false;
  if (trimmed.includes("/") || trimmed.includes("\\")) return true;
  if (trimmed.toLowerCase().endsWith(".json")) return true;
  if (trimmed.toLowerCase().includes("manifest")) return true;
  return false;
}

function admissibleRunId(value: string | null | undefined): string | null {
  const trimmed = value?.trim() || null;
  if (!trimmed) return null;
  if (isInadmissibleRunIdentity(trimmed)) return null;
  return trimmed;
}

export function readAppliedSelectionFromUrl(
  search: string | null | undefined = canUseWindow() ? window.location.search : null,
): GraphReviewAppliedSelection | null {
  if (search == null) return null;
  const params = new URLSearchParams(search);
  const sessionId = params.get("session")?.trim() || "";
  const campaignId = params.get("campaign")?.trim() || "";
  if (!sessionId || !campaignId) return null;
  return { campaignId, sessionId, runId: admissibleRunId(params.get("run")) };
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
  const runId = admissibleRunId(selection.runId);
  if (runId) {
    params.set("run", runId);
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
    const parsed = JSON.parse(raw) as Partial<GraphReviewAppliedSelection> & {
      manifestPath?: unknown;
    };
    const campaignId = typeof parsed.campaignId === "string" ? parsed.campaignId.trim() : "";
    const sessionId = typeof parsed.sessionId === "string" ? parsed.sessionId.trim() : "";
    if (!campaignId || !sessionId) return null;
    if ("manifestPath" in parsed && !("runId" in parsed)) {
      return { campaignId, sessionId, runId: null };
    }
    return {
      campaignId,
      sessionId,
      runId: admissibleRunId(typeof parsed.runId === "string" ? parsed.runId : null),
    };
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
    storage.removeItem(LEGACY_STORAGE_KEY);
    storage.setItem(
      GRAPH_REVIEW_APPLIED_SELECTION_STORAGE_KEY,
      JSON.stringify({
        campaignId: selection.campaignId,
        sessionId: selection.sessionId,
        runId: admissibleRunId(selection.runId),
      }),
    );
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
    storage.removeItem(LEGACY_STORAGE_KEY);
  } catch {
    // ignore
  }
}

/**
 * Prefer an explicit URL selection. Session storage only fills a missing `run`
 * for the same campaign/session — it never restores a load onto a bare `/ingest`.
 * Legacy path-shaped `run` values are ignored, not migrated by file scan.
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
      runId: fromUrl.runId ?? fromStorage.runId,
    };
  }
  return fromUrl;
}
