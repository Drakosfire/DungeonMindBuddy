import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";

/** Index endpoint keys mirror live API paths — resolved at runtime, not a surface-owned taxonomy. */
export const REFERENCE_INDEX_ENDPOINTS: Record<string, string> = {
  npc: "/api/live/npcs/index",
  location: "/api/live/locations/index",
  statblock: "/api/live/statblocks/index",
  "roll-table": "/api/live/roll-tables/index",
};

export interface ReferenceResolution {
  status: "resolved" | "unresolved" | "error";
  ref: RunbookReferenceAttrs;
  message: string;
  source?: string;
  item?: unknown;
  sourcePath?: string;
}

const indexCache = new Map<string, Promise<unknown>>();

export function resetReferenceIndexCache(): void {
  indexCache.clear();
}

export function normalizeReferenceKey(value: string): string {
  return String(value || "")
    .toLowerCase()
    .replace(/[_\s]+/g, "-")
    .replace(/[^a-z0-9-]+/g, "")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function referencePathStem(value: string): string {
  const path = String(value || "").split(/[?#]/)[0];
  const file = path.split("/").filter(Boolean).pop() || path;
  return file.replace(/\.[^.]+$/, "");
}

function itemsForPayload(type: string, payload: unknown): unknown[] {
  if (!payload || typeof payload !== "object") return [];
  const record = payload as Record<string, unknown>;
  if (Array.isArray(payload)) return payload;
  if (type === "npc") return (record.npcs as unknown[]) ?? (record.items as unknown[]) ?? [];
  if (type === "location") return (record.locations as unknown[]) ?? (record.items as unknown[]) ?? [];
  if (type === "statblock") return (record.statblocks as unknown[]) ?? (record.items as unknown[]) ?? [];
  if (type === "roll-table") {
    return (
      (record.roll_tables as unknown[])
      ?? (record.rollTables as unknown[])
      ?? (record.tables as unknown[])
      ?? (record.items as unknown[])
      ?? []
    );
  }
  return [];
}

function candidateKeysForItem(type: string, item: Record<string, unknown>): string[] {
  const candidates: string[] = [];
  const add = (value: unknown) => {
    const key = normalizeReferenceKey(String(value ?? ""));
    if (key) candidates.push(key);
  };
  [item.slug, item.index_id, item.title, item.table_id].forEach(add);
  [item.primary_doc_path, item.hub_path, item.corpus_display_path].forEach((path) => {
    const stem = referencePathStem(String(path ?? ""));
    add(stem);
    if (type === "statblock") {
      const normalizedStem = normalizeReferenceKey(stem);
      add(normalizedStem.replace(/-statblock-cr[-a-z0-9]+$/, ""));
      add(normalizedStem.replace(/-statblock$/, ""));
    }
  });
  return candidates;
}

export function findIndexItem(type: string, refId: string, payload: unknown): Record<string, unknown> | undefined {
  const refKey = normalizeReferenceKey(refId);
  const items = itemsForPayload(type, payload);
  return items.find((entry) => {
    if (!entry || typeof entry !== "object") return false;
    const item = entry as Record<string, unknown>;
    const candidates = candidateKeysForItem(type, item);
    if (candidates.includes(refKey)) return true;
    if (type === "npc" && item.index_id) {
      return normalizeReferenceKey(String(item.index_id)).endsWith(`-${refKey}`);
    }
    return false;
  }) as Record<string, unknown> | undefined;
}

function sourcePathForItem(type: string, item: Record<string, unknown>): string {
  if (type === "npc") {
    return String(
      item.primary_doc_path ?? item.dossier_path ?? item.seed_path ?? item.hub_path ?? "",
    );
  }
  if (type === "location") {
    return String(item.corpus_display_path ?? item.hub_path ?? "");
  }
  return String(item.corpus_display_path ?? "");
}

/** Validate refId as opaque locator — no path traversal. */
export function isValidReferenceLocator(refId: string): boolean {
  return /^[a-z0-9][a-z0-9_-]*$/i.test(refId.trim());
}

async function fetchIndex(type: string, fetchImpl: typeof fetch = fetch): Promise<unknown> {
  const endpoint = REFERENCE_INDEX_ENDPOINTS[type];
  if (!endpoint) return null;
  if (!indexCache.has(type)) {
    const promise = fetchImpl(endpoint)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Index fetch failed (${response.status})`);
        }
        return response.json();
      })
      .catch((error) => {
        indexCache.delete(type);
        throw error;
      });
    indexCache.set(type, promise);
  }
  return indexCache.get(type)!;
}

export async function resolveReference(
  ref: RunbookReferenceAttrs,
  fetchImpl: typeof fetch = fetch,
): Promise<ReferenceResolution> {
  if (!ref.refId || !isValidReferenceLocator(ref.refId)) {
    return {
      status: "error",
      ref,
      message: "Invalid reference locator.",
    };
  }

  if (ref.kind === "action") {
    return {
      status: "unresolved",
      ref,
      source: "action-placeholder",
      message:
        ref.refType === "combat"
          ? "Combat action placeholder. Launch behavior is intentionally disabled."
          : "Action placeholder. Launch behavior is intentionally disabled.",
    };
  }

  if (ref.refType === "citation") {
    return {
      status: "unresolved",
      ref,
      source: "citation-placeholder",
      message: "Citation resolver pending.",
    };
  }

  const endpoint = REFERENCE_INDEX_ENDPOINTS[ref.refType];
  if (!endpoint) {
    return {
      status: "unresolved",
      ref,
      message: "No index endpoint for this reference type.",
    };
  }

  try {
    const payload = await fetchIndex(ref.refType, fetchImpl);
    const item = findIndexItem(ref.refType, ref.refId, payload);
    if (!item) {
      return {
        status: "unresolved",
        ref,
        message: "Could not resolve this reference.",
      };
    }
    return {
      status: "resolved",
      ref,
      source: `${ref.refType}-index`,
      item,
      sourcePath: sourcePathForItem(ref.refType, item),
      message: `Resolved from live ${ref.refType} index.`,
    };
  } catch (error) {
    return {
      status: "error",
      ref,
      message: error instanceof Error ? error.message : "Resolver unavailable.",
    };
  }
}

export function readReferenceFromElement(element: HTMLElement): RunbookReferenceAttrs | null {
  if (!element.classList.contains("md-ref-chip")) return null;
  const kind = element.getAttribute("data-md-ref-kind");
  const refType = element.getAttribute("data-md-ref-type");
  const refId = element.getAttribute("data-md-ref-id");
  if ((kind !== "ref" && kind !== "action") || !refType || !refId) return null;
  return {
    kind: kind === "action" ? "action" : "ref",
    refType,
    refId,
    label: (element.textContent || "").trim() || refId,
  };
}
