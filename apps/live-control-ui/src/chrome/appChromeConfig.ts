export type AppRouteKey =
  | "index"
  | "surface"
  | "tiptap-callout-spike"
  | "plan"
  | "ingest"
  | "build"
  | "play";

export interface AppNavItem {
  route?: AppRouteKey;
  href: string;
  label: string;
}

/**
 * Primary product surfaces. Play hosts Beats (native) plus Combat / Roll /
 * Items / Statblocks as sub-tabs (prep HTML inlined from `/prep/*`).
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
    route: "play",
    href: "/play",
    label: "Play",
  },
];

export const APP_ROUTE_LABELS: Record<AppRouteKey, string> = {
  index: "Command Board",
  surface: "Live Control",
  plan: "Plan",
  ingest: "Memory Ingest",
  build: "Build",
  "tiptap-callout-spike": "Tiptap callout bridge",
  play: "Play",
};

/** Default campaign for shared World Graph lens when URL has no campaigns yet. */
export const WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID = "longmont-c2" as const;
