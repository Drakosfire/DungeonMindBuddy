/**
 * Collision-free membership comparison for published projection IDs.
 * Compares full string IDs via Set equality — never delimiter-composes identity.
 */

export function sameStringSetMembership(
  left: ReadonlySet<string>,
  right: ReadonlySet<string>,
): boolean {
  if (left.size !== right.size) return false;
  for (const value of left) {
    if (!right.has(value)) return false;
  }
  return true;
}

/**
 * Return `previous` when membership is unchanged so React deps stay stable across
 * same-identity preferredSize updates that rebuild the descriptor array.
 */
export function stabilizeStringSetMembership(
  previous: ReadonlySet<string>,
  nextIds: readonly string[],
): ReadonlySet<string> {
  const next = new Set(nextIds);
  return sameStringSetMembership(previous, next) ? previous : next;
}
