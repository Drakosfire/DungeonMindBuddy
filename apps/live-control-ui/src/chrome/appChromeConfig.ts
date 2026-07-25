import { appHref } from "./appBasePath";

export type AppRouteKey =
  | "index"
  | "surface"
  | "tiptap-callout-spike"
  | "plan"
  | "ingest"
  | "build"
  | "dev";

export interface AppNavItem {
  route?: AppRouteKey;
  href: string;
  label: string;
}

export const APP_NAV_ITEMS: AppNavItem[] = [
  {
    route: "index",
    href: appHref("/"),
    label: "Home",
  },
  {
    route: "plan",
    href: appHref("/plan"),
    label: "Plan",
  },
  {
    route: "ingest",
    href: appHref("/ingest"),
    label: "Ingest",
  },
  {
    route: "build",
    href: appHref("/build"),
    label: "Build",
  },
  {
    route: "surface",
    href: appHref("/surface"),
    label: "Live Control",
  },
  {
    route: "dev",
    href: appHref("/dev"),
    label: "Dev tools",
  },
  {
    route: "tiptap-callout-spike",
    href: appHref("/tiptap-callout-spike"),
    label: "Tiptap Spike",
  },
];

export const APP_ROUTE_LABELS: Record<AppRouteKey, string> = {
  index: "DungeonBuddy",
  surface: "Live Control",
  plan: "Plan",
  ingest: "Memory Ingest",
  build: "Build",
  dev: "Dev tools",
  "tiptap-callout-spike": "Tiptap callout bridge",
};
