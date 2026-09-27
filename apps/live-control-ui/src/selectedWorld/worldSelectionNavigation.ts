import { isPrimaryAppPathname, navigatePrimaryAppHref, normalizeAppPathname } from "../chrome/appNavigation";

/** A World switch discards every route-bound object identity, including Run and review pins. */
export function worldSelectionHref(locationSnapshot: string, worldId: string | null): string {
  const current = new URL(locationSnapshot, "http://localhost");
  const pathname = normalizeAppPathname(current.pathname);
  const route = isPrimaryAppPathname(pathname) ? pathname : "/";
  const world = worldId?.trim();
  return world ? `${route}?world=${encodeURIComponent(world)}` : route;
}

export function selectWorldFromLocation(worldId: string | null): void {
  navigatePrimaryAppHref(worldSelectionHref(
    `${window.location.pathname}${window.location.search}${window.location.hash}`,
    worldId,
  ));
}

export function worldScopedSurfaceHref(pathname: string, worldId: string | null): string {
  return worldSelectionHref(pathname, worldId);
}
