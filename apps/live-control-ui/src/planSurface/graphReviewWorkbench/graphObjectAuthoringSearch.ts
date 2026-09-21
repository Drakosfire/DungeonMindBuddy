export interface GraphObjectAuthoringSearchItem {
  key: string;
  label: string;
  group: string;
  meta?: string | null;
  searchText: string;
}

export interface RankedGraphObjectAuthoringSearchItem<T extends GraphObjectAuthoringSearchItem> {
  item: T;
  score: number;
}

function normalizeSearchText(value: string): string {
  return value.trim().toLocaleLowerCase().replace(/\s+/g, " ");
}

/**
 * Small, dependency-free fuzzy scorer shared by source and target object
 * pickers. Exact/prefix/substring matches win, while subsequence matching
 * keeps long object lists useful when the operator remembers only part of a
 * label or alias.
 */
export function fuzzySearchScore(query: string, text: string): number | null {
  const normalizedQuery = normalizeSearchText(query);
  const normalizedText = normalizeSearchText(text);
  if (!normalizedQuery) return 0;
  if (!normalizedText) return null;
  if (normalizedText === normalizedQuery) return 1000;
  if (normalizedText.startsWith(normalizedQuery)) return 900 - normalizedText.length / 1000;
  if (normalizedText.includes(normalizedQuery)) return 800 - normalizedText.indexOf(normalizedQuery) / 100;

  let cursor = 0;
  let gaps = 0;
  for (const character of normalizedQuery) {
    const foundAt = normalizedText.indexOf(character, cursor);
    if (foundAt < 0) return null;
    gaps += foundAt - cursor;
    cursor = foundAt + 1;
  }
  return 500 - gaps - (normalizedText.length - normalizedQuery.length) / 1000;
}

export function rankGraphObjectAuthoringSearchItems<T extends GraphObjectAuthoringSearchItem>(
  items: T[],
  query: string,
): Array<RankedGraphObjectAuthoringSearchItem<T>> {
  return items
    .map((item, index) => {
      const searchable = [item.label, item.meta ?? "", item.group, item.searchText].join(" ");
      const score = fuzzySearchScore(query, searchable);
      return score == null ? null : { item, score, index };
    })
    .filter((entry): entry is { item: T; score: number; index: number } => entry !== null)
    .sort((left, right) => right.score - left.score || left.index - right.index)
    .map(({ item, score }) => ({ item, score }));
}
