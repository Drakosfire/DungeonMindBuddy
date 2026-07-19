/** Decide whether a chip glance should dock below or above its token. */

export type GlancePlacement = "below" | "above";

export interface ResolveGlancePlacementArgs {
  tokenTop: number;
  tokenBottom: number;
  cardHeight: number;
  viewportHeight: number;
  /** Top edge of a bottom obstacle (e.g. Ask DungeonBuddy shell). */
  obstacleTop: number | null;
  gap?: number;
}

/**
 * Prefer below. Flip above when the card would intersect the bottom obstacle
 * (or viewport floor) and there is at least as much room above.
 */
export function resolveGlancePlacement({
  tokenTop,
  tokenBottom,
  cardHeight,
  viewportHeight,
  obstacleTop,
  gap = 8,
}: ResolveGlancePlacementArgs): GlancePlacement {
  const floor =
    obstacleTop == null || !Number.isFinite(obstacleTop)
      ? viewportHeight
      : Math.min(obstacleTop, viewportHeight);
  const needed = Math.max(cardHeight, 1) + gap;
  const spaceBelow = floor - tokenBottom;
  const spaceAbove = tokenTop;

  if (spaceBelow >= needed) {
    return "below";
  }
  if (spaceAbove >= needed) {
    return "above";
  }
  return spaceAbove > spaceBelow ? "above" : "below";
}

export function readBottomObstacleTop(
  root: ParentNode | Document = document,
): number | null {
  const shell = root.querySelector(".plan-agent-shell");
  if (!(shell instanceof HTMLElement)) {
    return null;
  }
  // Fullscreen open drawer covers the viewport; don't treat it as a bottom dock.
  if (shell.classList.contains("open")) {
    return null;
  }
  return shell.getBoundingClientRect().top;
}
