/** Parse `?openNode=` from Plan location search (combat → Plan Threat sheet deep link). */
export function readOpenNodeFromSearch(search: string | null | undefined): string | null {
  if (!search) return null;
  const raw = search.startsWith("?") ? search.slice(1) : search;
  const value = new URLSearchParams(raw).get("openNode")?.trim() || "";
  return value || null;
}

/** Drop `openNode` while preserving other query params. Returns path+query (no hash). */
export function stripOpenNodeFromLocation(
  pathname: string,
  search: string,
  hash = "",
): string {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  params.delete("openNode");
  const query = params.toString();
  const keepHash = hash && !hash.startsWith("tool=") ? hash : hash.startsWith("tool=") ? "" : hash;
  return query ? `${pathname}?${query}${keepHash}` : `${pathname}${keepHash}`;
}
