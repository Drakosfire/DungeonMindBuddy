export type AppRouteKey = "index" | "surface" | "tiptap-callout-spike" | "plan" | "ingest";

export interface AppNavItem {
  route?: AppRouteKey;
  href: string;
  label: string;
}

export const APP_NAV_ITEMS: AppNavItem[] = [
  {
    route: "index",
    href: "/",
    label: "Index",
  },
  {
    href: "/evals/c2_live_prep/mireward-prep/live-play.html",
    label: "Live play",
  },
  {
    href: "/evals/c2_live_prep/mireward-prep/retrieval.html",
    label: "Retrieval",
  },
  {
    href: "/evals/c2_live_prep/mireward-prep/combat.html",
    label: "Combat tracker",
  },
  {
    href: "/evals/c2_live_prep/mireward-prep/live-notes.html",
    label: "Live notes",
  },
  {
    href: "/evals/c2_live_prep/mireward-prep/timeline.html",
    label: "Timeline",
  },
  {
    href: "/evals/c2_live_prep/mireward-prep/locations.html",
    label: "Locations",
  },
  {
    href: "/evals/c2_live_prep/mireward-prep/npcs.html",
    label: "NPCs",
  },
  {
    href: "/evals/c2_live_prep/mireward-prep/roll-tables.html",
    label: "Roll tables",
  },
  {
    href: "/evals/c2_live_prep/mireward-prep/statblocks.html",
    label: "Statblocks",
  },
  {
    route: "surface",
    href: "/surface",
    label: "Live Control",
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
    route: "tiptap-callout-spike",
    href: "/tiptap-callout-spike",
    label: "Tiptap Spike",
  },
];

export const APP_ROUTE_LABELS: Record<AppRouteKey, string> = {
  index: "Mireward local tools",
  surface: "Live Control",
  plan: "Plan",
  ingest: "Memory Ingest",
  "tiptap-callout-spike": "Tiptap callout bridge",
};
