/**
 * Of Conks module media associations for Play / Threat sheets.
 *
 * The source PDF has no embedded adventure illustrations (map / Fig.1 slots are
 * empty). Mined assets are high-res module **page rasters** for table reference.
 * Files live under gitignored `corpus/of-conks-cons-markdown/media/`.
 */

export type OfConksNodeMedia = {
  /** Dev-server path served from repo root via Vite `/corpus/…`. */
  src: string;
  alt: string;
  caption?: string;
  /** Provenance of the bitmap. */
  kind: "module-page";
};

const MEDIA_ROOT = "/corpus/of-conks-cons-markdown/media";

function page(
  filename: string,
  alt: string,
  caption: string,
): OfConksNodeMedia {
  return {
    src: `${MEDIA_ROOT}/${filename}`,
    alt,
    caption,
    kind: "module-page",
  };
}

const GREENFIELDS = page(
  "page-04-greenfields.jpg",
  "Of Conks module page — The Greenfields",
  "Module p.4 · region context (PDF has no separate map art)",
);
const SHACKS = page(
  "page-07-area-1-the-shacks.jpg",
  "Of Conks module page — Area 1: The Shacks",
  "Module p.7 · The Shacks (Fig.1 plate empty in this PDF)",
);
const STORE_WAGON = page(
  "page-09-area-2-3-store-wagon.jpg",
  "Of Conks module page — Area 2–3: Store and Saladin’s wagon",
  "Module p.9 · Morwin’s store + Saladin’s Mobile Emporium",
);
const JOVE = page(
  "page-10-area-4-jove-home.jpg",
  "Of Conks module page — Area 4: The Jove's Home",
  "Module p.10 · Jove home / garden approach",
);
const TREE = page(
  "page-11-area-5-grotesque-tree.jpg",
  "Of Conks module page — Area 5: The Grotesque Tree",
  "Module p.11 · tree site tactics and treasure",
);
const MARROW = page(
  "page-15-descent-marrow.jpg",
  "Of Conks module page — Descent / The Marrow",
  "Module p.15 · root corridors and Marrow",
);

const BY_NODE_ID: Readonly<Record<string, OfConksNodeMedia>> = {
  "location:hempholm": SHACKS,
  "location:the-shacks": SHACKS,
  "npc:nar-granitetooth": SHACKS,
  "npc:lord-fiddlestick": GREENFIELDS,
  "item:the-conk": GREENFIELDS,
  "location:morwins-store": STORE_WAGON,
  "npc:morwin-blackwell": STORE_WAGON,
  "location:saladins-wagon": STORE_WAGON,
  "npc:saladin": STORE_WAGON,
  "item:maglubiyets-statue": STORE_WAGON,
  "location:jove-home": JOVE,
  "npc:mark-jove": JOVE,
  "npc:torbin-jove": JOVE,
  "location:grotesque-tree-site": TREE,
  "threat:grotesque-tree": TREE,
  "item:metal-leaves": TREE,
  "location:root-corridors": MARROW,
  "location:the-marrow": MARROW,
  "threat:guardian": MARROW,
  "threat:caretakers": MARROW,
  "npc:helix-child": MARROW,
  "npc:paelias-sian": MARROW,
  "faction:baldurs-gate-mages-guild": GREENFIELDS,
};

export function mediaForOfConksNodeId(nodeId: string): OfConksNodeMedia | null {
  const key = nodeId.trim();
  if (!key) return null;
  return BY_NODE_ID[key] ?? null;
}
