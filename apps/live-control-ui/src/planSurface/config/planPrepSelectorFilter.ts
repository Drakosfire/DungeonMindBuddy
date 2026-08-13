/** Workspace Plan docs that belong on product tabs, not the Plan prep dropdown. */

export type PrepSelectorRecordLike = {
  title?: string | null;
};

/**
 * Returns true when a workspace Plan document should appear in the Plan prep
 * selector. Roll tables → `/roll`, items → `/items`, mechanics/tactics cards →
 * `/statblocks` workbench drafts.
 */
export function isPlanPrepSelectorDocument(record: PrepSelectorRecordLike): boolean {
  const title = String(record.title ?? "").trim();
  if (!title) return true;
  if (/—\s*roll\s*table\b/i.test(title) || /\broll\s*table\b/i.test(title)) {
    return false;
  }
  if (/—\s*item\b/i.test(title)) {
    return false;
  }
  if (/—\s*mechanics\b/i.test(title) || /—\s*tactics\b/i.test(title)) {
    return false;
  }
  return true;
}
