/**
 * Same-document primary-surface navigation.
 *
 * `window.location` remains source of truth. React observes popstate.
 * Eligible unmodified same-tab clicks on primary in-app hrefs push history
 * instead of loading a new document. Combat and modified/native gestures
 * stay with the browser.
 */

import type { MouseEvent as ReactMouseEvent } from "react";

export type AppLocationRoute =
  | "index"
  | "surface"
  | "tiptap-callout-spike"
  | "plan"
  | "play"
  | "ingest"
  | "build";

const PRIMARY_APP_PATHNAMES = new Set(["/", "/plan", "/play", "/ingest", "/build"]);

export interface NavigationClickLike {
  defaultPrevented: boolean;
  button: number;
  metaKey: boolean;
  ctrlKey: boolean;
  shiftKey: boolean;
  altKey: boolean;
}

export function normalizeAppPathname(pathname: string): string {
  return pathname.replace(/\/+$/, "") || "/";
}

export function isPrimaryAppPathname(pathname: string): boolean {
  return PRIMARY_APP_PATHNAMES.has(normalizeAppPathname(pathname));
}

export function getAppLocationSnapshot(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

export function subscribeAppLocation(onStoreChange: () => void): () => void {
  window.addEventListener("popstate", onStoreChange);
  return () => window.removeEventListener("popstate", onStoreChange);
}

export function pathnameFromLocationSnapshot(snapshot: string): string {
  const withoutHash = snapshot.split("#")[0] ?? snapshot;
  const pathname = withoutHash.split("?")[0] ?? withoutHash;
  return normalizeAppPathname(pathname);
}

export function appRouteFromPathname(pathname: string): AppLocationRoute {
  const path = normalizeAppPathname(pathname);
  if (path === "/surface" || path === "/live-control") return "surface";
  if (path === "/tiptap-callout-spike") return "tiptap-callout-spike";
  if (path === "/plan") return "plan";
  if (path === "/play") return "play";
  if (path === "/ingest") return "ingest";
  if (path === "/build") return "build";
  return "index";
}

export function appRouteFromLocationSnapshot(snapshot: string): AppLocationRoute {
  return appRouteFromPathname(pathnameFromLocationSnapshot(snapshot));
}

function resolveSameOriginUrl(href: string): URL | null {
  try {
    const url = new URL(href, window.location.origin);
    if (url.origin !== window.location.origin) return null;
    return url;
  } catch {
    return null;
  }
}

export function isPrimaryAppHref(href: string): boolean {
  const url = resolveSameOriginUrl(href);
  if (!url) return false;
  return isPrimaryAppPathname(url.pathname);
}

export function shouldInterceptPrimaryNavigationClick(
  event: NavigationClickLike,
  anchor: HTMLAnchorElement,
): boolean {
  if (event.defaultPrevented) return false;
  if (event.button !== 0) return false;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
  const target = anchor.target.trim();
  if (target !== "" && target.toLowerCase() !== "_self") return false;
  if (anchor.hasAttribute("download")) return false;
  const href = anchor.getAttribute("href");
  if (!href) return false;
  return isPrimaryAppHref(href);
}

export function navigatePrimaryAppHref(href: string): void {
  const url = resolveSameOriginUrl(href);
  if (!url) return;
  const pathname = normalizeAppPathname(url.pathname);
  if (!isPrimaryAppPathname(pathname)) return;
  if (normalizeAppPathname(window.location.pathname) === pathname) return;
  const next = `${pathname}${url.search}${url.hash}`;
  window.history.pushState({}, "", next);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function interceptPrimaryNavigationClick(
  event: ReactMouseEvent<HTMLAnchorElement>,
): void {
  const anchor = event.currentTarget;
  if (!shouldInterceptPrimaryNavigationClick(event, anchor)) return;
  event.preventDefault();
  const href = anchor.getAttribute("href");
  if (!href) return;
  navigatePrimaryAppHref(href);
}
