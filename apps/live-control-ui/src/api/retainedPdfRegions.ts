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
