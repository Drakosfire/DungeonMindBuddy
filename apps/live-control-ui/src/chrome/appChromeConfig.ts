export type AppRouteKey = "index" | "surface" | "tiptap-callout-spike" | "plan" | "ingest" | "build";

export interface AppNavItem {
  route?: AppRouteKey;
  href: string;
  label: string;
}

/** Primary product surfaces only. Eval HTML and tip-tap spike stay URL-reachable. */
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
    route: "surface",
    href: "/surface",
    label: "Live Control",
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
