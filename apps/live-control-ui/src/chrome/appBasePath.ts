/**
 * Vite `base` for the Buddy app (production path: /dungeonbuddy/).
 * `import.meta.env.BASE_URL` always ends with `/` (e.g. `/dungeonbuddy/`).
 */
export const APP_BASE_URL = import.meta.env.BASE_URL || "/";

/** Base without trailing slash: `/dungeonbuddy` or `` when mounted at root. */
export const APP_BASE_PATH = APP_BASE_URL.replace(/\/+$/, "");

/**
 * Build an absolute in-app href under the Buddy base.
 * Accepts paths like `/plan`, `/plan?tool=recap`, or `plan`.
 */
export function appHref(path: string): string {
  if (/^https?:\/\//i.test(path) || path.startsWith("mailto:")) {
    return path;
  }

  const match = path.match(/^([^?#]*)([?#].*)?$/);
  const rawPath = match?.[1] ?? path;
  const suffix = match?.[2] ?? "";
  let normalized = rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
  if (normalized.length > 1) {
    normalized = normalized.replace(/\/+$/, "");
  }

  if (!APP_BASE_PATH) {
    return `${normalized}${suffix}`;
  }
  if (normalized === "/") {
    return suffix ? `${APP_BASE_PATH}/${suffix}` : `${APP_BASE_PATH}/`;
  }
  return `${APP_BASE_PATH}${normalized}${suffix}`;
}

/** Strip Buddy base from a browser pathname for route matching. */
export function stripAppBasePath(pathname: string): string {
  const cleaned = pathname.replace(/\/+$/, "") || "/";
  if (!APP_BASE_PATH) {
    return cleaned;
  }
  if (cleaned === APP_BASE_PATH) {
    return "/";
  }
  if (cleaned.startsWith(`${APP_BASE_PATH}/`)) {
    return cleaned.slice(APP_BASE_PATH.length) || "/";
  }
  return cleaned;
}

/** True when pathname is under the Buddy mount (or app is at root). */
export function isBuddyPath(pathname: string): boolean {
  if (!APP_BASE_PATH) {
    return true;
  }
  const cleaned = pathname.replace(/\/+$/, "") || "/";
  return cleaned === APP_BASE_PATH || cleaned.startsWith(`${APP_BASE_PATH}/`);
}
