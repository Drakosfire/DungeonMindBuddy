import { authenticatedApiFetch } from "./liveApi";

export type PdfReceipt = { source_revision_id: string; content_sha256: string };
export type PdfLocator = PdfReceipt & { page: number; left: number; top: number; right: number; bottom: number };

export type RetainedPdf = { name: string; locator: PdfLocator };

export function retainedPdfKey(worldId: string) {
  return `buddy:retained-pdf-region:${encodeURIComponent(worldId)}:`;
}

export function pdfRegionKey(locator: PdfLocator) {
  return JSON.stringify([locator.source_revision_id, locator.content_sha256, locator.page,
    locator.left, locator.top, locator.right, locator.bottom]);
}

export function readRetainedPdfRegions(worldId: string): RetainedPdf[] {
  try {
    const prefix = retainedPdfKey(worldId);
    const entries = new Map<string, RetainedPdf>();
    for (const key of Object.keys(localStorage)) {
      if (!key.startsWith(prefix)) continue;
      try {
        const entry = JSON.parse(localStorage.getItem(key) ?? "null") as RetainedPdf | null;
        if (entry?.locator && typeof entry.name === "string") {
          entries.set(pdfRegionKey(entry.locator), entry);
        }
      } catch {
        // A damaged entry must not hide other captures.
      }
    }
    return [...entries.values()];
  } catch {
    return [];
  }
}

export function retainedPdfBuildHref(worldId: string, entry: RetainedPdf) {
  return "/build?" + new URLSearchParams({ world: worldId, pdf: entry.locator.source_revision_id });
}

export function readRetainedPdfDocuments(worldId: string): RetainedPdf[] {
  const documents = new Map<string, RetainedPdf>();
  for (const entry of readRetainedPdfRegions(worldId)) {
    const id = entry.locator.source_revision_id;
    const existing = documents.get(id);
    if (!existing || entry.locator.page < existing.locator.page) documents.set(id, entry);
  }
  return [...documents.values()];
}

export async function listRetainedPdfDocuments(worldId: string, signal: AbortSignal): Promise<RetainedPdf[]> {
  const shortcuts = new Map(readRetainedPdfDocuments(worldId)
    .map(entry => [entry.locator.source_revision_id, entry]));
  const documents = new Map<string, RetainedPdf>();
  const path = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources`;
  let after: string | null = "";
  do {
    const { response } = await authenticatedApiFetch(
      path + "?" + new URLSearchParams({ after }), { signal },
    );
    if (!response.ok) throw new Error("PDF catalog unavailable");
    const page: { documents: Array<PdfReceipt & { created_at: string }>; next: string | null } =
      await response.json();
    for (const { created_at, ...receipt } of page.documents) {
      const shortcut = shortcuts.get(receipt.source_revision_id);
      documents.set(receipt.source_revision_id, {
        name: shortcut?.name ?? `PDF · ${created_at.slice(0, 10)} · ${receipt.content_sha256.slice(0, 8)}`,
        locator: shortcut?.locator.content_sha256 === receipt.content_sha256 ? shortcut.locator
          : { ...receipt, page: 1, left: 0, top: 0, right: 1, bottom: 1 },
      });
    }
    if (page.next === after) throw new Error("PDF catalog did not advance");
    after = page.next;
  } while (after);
  return [...documents.values()];
}
