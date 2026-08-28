import { workspaceDocumentSelectionSearch } from "../workspaceDocument/workspaceDocumentNavigation";

/**
 * Exact WorkObject navigation from Play to the ordinary TipTap authoring surface.
 * Identity is the opaque document UUID. Title, path, session, and list position
 * are never used.
 */
export function playRunbookAuthoringHref(
  documentId: string,
  currentSearch: string | null | undefined = "",
): string {
  return `/plan${workspaceDocumentSelectionSearch(currentSearch, documentId)}`;
}
