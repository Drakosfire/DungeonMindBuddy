/**
 * Exact opaque workspace `documentId` navigation helper.
 *
 * Sets `documentId` and preserves every unrelated query parameter (graph lens,
 * session focus, tool state, dogfood flags). Never infers session, campaign,
 * title, kind, or list position as document identity.
 */
export function workspaceDocumentSelectionSearch(
  currentSearch: string | null | undefined,
  documentId: string,
): string {
  const params = new URLSearchParams(currentSearch ?? "");
  params.set("documentId", documentId);
  const query = params.toString();
  return query ? `?${query}` : "";
}
