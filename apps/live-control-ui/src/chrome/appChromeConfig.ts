export type AppRouteKey =
  | "index"
  | "surface"
  | "tiptap-callout-spike"
  | "plan"
  | "ingest"
  | "build";

export interface AppNavItem {
  route?: AppRouteKey;
  href: string;
  label: string;
}

/**
 * Primary product surfaces. Combat Tracker opens the mature Mireward command-board
 * tracker (`evals/c2_live_prep/mireward-prep/combat.html`), not the Live Control
 * React roster module. Full `/surface` board stays URL-reachable only.
 */
export const APP_NAV_ITEMS: AppNavItem[] = [
  {
    route: "index",
    href: "/",
    label: "Index",
  },
  {
    route: "plan",
    href: "/plan",
    label: "Plan",
  },
  {
    route: "ingest",
    href: "/ingest",
    label: "Ingest",
  },
  {
    route: "build",
    href: "/build",
    label: "Build",
  },
  {
    href: "/combat",
    label: "Combat Tracker",
  },
];

export const APP_ROUTE_LABELS: Record<AppRouteKey, string> = {
  index: "Command Board",
  surface: "Live Control",
  plan: "Plan",
  ingest: "Memory Ingest",
  build: "Build",
  "tiptap-callout-spike": "Tiptap callout bridge",
};
