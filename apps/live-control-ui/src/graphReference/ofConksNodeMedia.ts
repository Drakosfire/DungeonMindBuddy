/**
 * Of Conks module media associations for Play / Threat sheets.
 *
 * Source: illustrated PDF `1399969-20190116_Conks-Cons_v21.pdf` (not the
 * text-only `…_PF_v21.pdf`). Files live under gitignored
 * `corpus/of-conks-cons-markdown/media/` — regenerate with
 * `scripts/mine_of_conks_pdf_media.py`.
 */

export type OfConksNodeMedia = {
  /** Dev-server path served from repo root via Vite `/corpus/…`. */
  src: string;
  alt: string;
  caption?: string;
  kind: "figure" | "map" | "cover" | "plate";
};

const MEDIA_ROOT = "/corpus/of-conks-cons-markdown/media";

function asset(
  filename: string,
  alt: string,
  caption: string,
  kind: OfConksNodeMedia["kind"],
): OfConksNodeMedia {
  return {
    src: `${MEDIA_ROOT}/${filename}`,
    alt,
    caption,
    kind,
  };
}

const COVER = asset(
  "cover-of-conks.jpg",
  "Of Conks & Cons cover",
  "Module cover · Greenfields Adventure Series",
  "cover",
);
const MAP_GREENFIELDS = asset(
  "map-greenfields.jpg",
  "Map of the Greenfields",
  "Module map · Greenfields region (Hempholm marked)",
  "map",
);
const MAP_HEMPHOLM = asset(
  "map-hempholm.jpg",
  "Map of Hempholm",
  "Module map · village areas 1–5",
  "map",
);
const FIG_SHACKS = asset(
  "fig-1-the-shacks.jpg",
  "Fig. 1 — The Shacks / Hempholm village",
  "Module Fig.1 · Hempholm village map",
  "figure",
);
const ART_OAKS = asset(
  "art-greenfields-oaks.jpg",
  "Greenfields pastoral plate",
  "Module plate · pastoral Greenfields mood",
  "plate",
);
const ART_HARVEST = asset(
  "art-area-5-harvest.jpg",
  "Harvest field pastoral plate",
  "Module plate · near the grotesque-tree beat",
  "plate",
);
const ART_CATTLE = asset(
  "art-pastoral-cattle.jpg",
  "Pastoral cattle plate",
  "Module plate · village / farm mood",
  "plate",
);
const ART_TRAVELERS = asset(
  "art-road-travelers.jpg",
  "Road travelers pastoral plate",
  "Module plate · arrival / road mood",
  "plate",
);

const BY_NODE_ID: Readonly<Record<string, OfConksNodeMedia>> = {
  "location:hempholm": MAP_HEMPHOLM,
  "location:the-shacks": FIG_SHACKS,
  "npc:nar-granitetooth": FIG_SHACKS,
  "npc:lord-fiddlestick": MAP_GREENFIELDS,
  "item:the-conk": MAP_GREENFIELDS,
  "location:morwins-store": MAP_HEMPHOLM,
  "npc:morwin-blackwell": MAP_HEMPHOLM,
  "location:saladins-wagon": MAP_HEMPHOLM,
  "npc:saladin": MAP_HEMPHOLM,
  "item:maglubiyets-statue": MAP_HEMPHOLM,
  "location:jove-home": MAP_HEMPHOLM,
  "npc:mark-jove": MAP_HEMPHOLM,
  "npc:torbin-jove": MAP_HEMPHOLM,
  "location:grotesque-tree-site": MAP_HEMPHOLM,
  "threat:grotesque-tree": ART_HARVEST,
  "item:metal-leaves": ART_HARVEST,
  "location:root-corridors": ART_OAKS,
  "location:the-marrow": ART_OAKS,
  "threat:guardian": ART_OAKS,
  "threat:caretakers": ART_CATTLE,
  "npc:helix-child": ART_TRAVELERS,
  "npc:paelias-sian": COVER,
  "faction:baldurs-gate-mages-guild": MAP_GREENFIELDS,
};

export function mediaForOfConksNodeId(nodeId: string): OfConksNodeMedia | null {
  const key = nodeId.trim();
  if (!key) return null;
  return BY_NODE_ID[key] ?? null;
}
