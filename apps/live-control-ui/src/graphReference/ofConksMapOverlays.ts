/**
 * Prototype coordinate overlays for Of Conks maps.
 * Pins use percentage coords (0–100) of the displayed image box — resolution-independent.
 * Not graph canon; table projection only.
 */

export type OfConksMapPin = {
  id: string;
  label: string;
  nodeId: string;
  /** Percent from left edge of the map image. */
  xPct: number;
  /** Percent from top edge of the map image. */
  yPct: number;
  /** Module area number when applicable. */
  areaNumber?: number;
};

export type OfConksMapOverlay = {
  /** Basename under /corpus/of-conks-cons-markdown/media/ */
  mediaFile: string;
  title: string;
  pins: OfConksMapPin[];
};

const HEMPHOLM_VILLAGE: OfConksMapOverlay = {
  mediaFile: "map-hempholm.jpg",
  title: "Hempholm — areas",
  pins: [
    {
      id: "area-1",
      label: "The Shacks",
      nodeId: "location:the-shacks",
      xPct: 82,
      yPct: 40,
      areaNumber: 1,
    },
    {
      id: "area-2",
      label: "Morwin's",
      nodeId: "location:morwins-store",
      xPct: 58,
      yPct: 30,
      areaNumber: 2,
    },
    {
      id: "area-3",
      label: "Saladin's wagon",
      nodeId: "location:saladins-wagon",
      xPct: 48,
      yPct: 44,
      areaNumber: 3,
    },
    {
      id: "area-4",
      label: "Jove home",
      nodeId: "location:jove-home",
      xPct: 52,
      yPct: 56,
      areaNumber: 4,
    },
    {
      id: "area-5",
      label: "Grotesque Tree",
      nodeId: "location:grotesque-tree-site",
      xPct: 54,
      yPct: 70,
      areaNumber: 5,
    },
  ],
};

/** Fig.1 plate is the same village map bitmap. */
const FIG_SHACKS_OVERLAY: OfConksMapOverlay = {
  ...HEMPHOLM_VILLAGE,
  mediaFile: "fig-1-the-shacks.jpg",
  title: "Fig.1 — Hempholm areas",
};

const GREENFIELDS: OfConksMapOverlay = {
  mediaFile: "map-greenfields.jpg",
  title: "Greenfields — region",
  pins: [
    {
      id: "hempholm",
      label: "Hempholm",
      nodeId: "location:hempholm",
      xPct: 48,
      yPct: 28,
    },
  ],
};

const BY_MEDIA_FILE: Readonly<Record<string, OfConksMapOverlay>> = {
  [HEMPHOLM_VILLAGE.mediaFile]: HEMPHOLM_VILLAGE,
  [FIG_SHACKS_OVERLAY.mediaFile]: FIG_SHACKS_OVERLAY,
  [GREENFIELDS.mediaFile]: GREENFIELDS,
};

export function mapOverlayForMediaSrc(src: string | null | undefined): OfConksMapOverlay | null {
  if (!src) return null;
  const file = src.split("/").pop()?.trim() ?? "";
  if (!file) return null;
  return BY_MEDIA_FILE[file] ?? null;
}

export function mapOverlayPinForNode(
  overlay: OfConksMapOverlay,
  nodeId: string,
): OfConksMapPin | null {
  const key = nodeId.trim();
  return overlay.pins.find((pin) => pin.nodeId === key) ?? null;
}
