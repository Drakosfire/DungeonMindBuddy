export type AppRouteKey =
  | "index"
  | "graph"
  | "surface"
  | "plan"
  | "play"
  | "ingest"
  | "build"
  | "combat"
  | "statblock";

export interface AppNavItem {
  route?: AppRouteKey;
  href: string;
  label: string;
}

/** Native product surfaces share AppChrome and selected-World navigation. */
export const APP_NAV_ITEMS: AppNavItem[] = [
  {
    route: "index",
    href: "/",
    label: "Home",
  },
  {
    route: "graph",
    href: "/graph",
    label: "Graph",
  },
  {
    route: "plan",
    href: "/plan",
    label: "Plan",
  },
  {
    route: "play",
    href: "/play",
    label: "Play",
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
    route: "combat",
    href: "/combat",
    label: "Combat Tracker",
  },
];

export const APP_ROUTE_LABELS: Record<AppRouteKey, string> = {
  index: "Home",
  graph: "Graph",
  surface: "Live Control",
  plan: "Plan",
  play: "Play",
  ingest: "Memory Ingest",
  build: "Build",
  combat: "Combat",
  statblock: "Statblock",
};

/** Default campaign for shared World Graph lens when URL has no campaigns yet. */
export const WORLD_GRAPH_LENS_DEFAULT_CAMPAIGN_ID = "longmont-c2" as const;
