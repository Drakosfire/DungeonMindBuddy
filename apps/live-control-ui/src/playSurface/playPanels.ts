/** Table-tool panels hosted under the Play chrome shell. */

export const PLAY_PANEL_IDS = ["beats", "combat", "roll", "items", "statblocks"] as const;

export type PlayPanelId = (typeof PLAY_PANEL_IDS)[number];

export type PlayPanelHostKind = "native" | "prep";

export interface PlayPanelDefinition {
  id: PlayPanelId;
  label: string;
  host: PlayPanelHostKind;
  /** Static mireward-prep page served under /prep/* (inlined into Play host). */
  prepPath?: string;
  /** Accessible label for the inlined panel region. */
  iframeTitle?: string;
}

export const PLAY_PANELS: Record<PlayPanelId, PlayPanelDefinition> = {
  beats: {
    id: "beats",
    label: "Beats",
    host: "native",
  },
  combat: {
    id: "combat",
    label: "Combat",
    host: "prep",
    prepPath: "/prep/combat",
    iframeTitle: "Combat tracker",
  },
  roll: {
    id: "roll",
    label: "Roll",
    host: "prep",
    prepPath: "/prep/roll",
    iframeTitle: "Roll tables",
  },
  items: {
    id: "items",
    label: "Items",
    host: "prep",
    prepPath: "/prep/items",
    iframeTitle: "Items",
  },
  statblocks: {
    id: "statblocks",
    label: "Statblocks",
    host: "prep",
    prepPath: "/prep/statblocks",
    iframeTitle: "Statblocks",
  },
};

export function isPlayPanelId(value: string | null | undefined): value is PlayPanelId {
  return value != null && (PLAY_PANEL_IDS as readonly string[]).includes(value);
}

export function isPrepPlayPanel(panel: PlayPanelId): boolean {
  return PLAY_PANELS[panel].host === "prep";
}

/** Canonical Play path for a panel (`/play/combat`). */
export function playPanelHref(panel: PlayPanelId): string {
  return `/play/${panel}`;
}

export function playPanelFromPath(
  pathname: string | null | undefined = typeof window !== "undefined"
    ? window.location.pathname
    : null,
): PlayPanelId | null {
  const path = (pathname ?? "").replace(/\/+$/, "") || "/";
  if (path === "/play" || path === "/play/") return "beats";
  const playMatch = path.match(/^\/play\/([a-z]+)$/);
  if (playMatch && isPlayPanelId(playMatch[1])) return playMatch[1];
  // Legacy product URLs → same panels
  if (path === "/combat") return "combat";
  if (path === "/roll") return "roll";
  if (path === "/items") return "items";
  if (path === "/statblocks") return "statblocks";
  return null;
}

export function isPlayPath(
  pathname: string | null | undefined = typeof window !== "undefined"
    ? window.location.pathname
    : null,
): boolean {
  return playPanelFromPath(pathname) != null;
}

/** Build prep embed URL: same-origin /prep page + lens query (inlined, not iframe). */
export function buildPlayPanelEmbedSrc(
  panel: PlayPanelId,
  search: string | null | undefined,
  selectedCampaignIds: readonly string[] | null | undefined = null,
): string | null {
  const def = PLAY_PANELS[panel];
  if (def.host !== "prep" || !def.prepPath) return null;
  const params = new URLSearchParams(
    search && search.startsWith("?") ? search.slice(1) : search ?? "",
  );
  params.set("embed", "1");
  if (selectedCampaignIds && selectedCampaignIds.length > 0) {
    params.set("campaigns", selectedCampaignIds.join(","));
  }
  const query = params.toString();
  return `${def.prepPath}?${query}`;
}
