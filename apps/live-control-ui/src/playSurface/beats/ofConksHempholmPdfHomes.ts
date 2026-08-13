/**
 * PDF adventure-body → Play/Build home map for Of Conks & Cons v2.1.
 * Source: corpus/of-conks-cons-markdown/Of-Conks-and-Cons-v21.md
 * Omits: Credits & Afterword, OGL/legal, other-product blurbs, ToC chrome.
 */

export type PdfHomeKind = "beat" | "scene" | "sheet" | "panel" | "build";

export type PdfSectionHome = {
  /** Heading text as in the PDF markdown (adventure body only). */
  pdfHeading: string;
  homeKind: PdfHomeKind;
  /** beat id | scene id | node id | play panel | build doc title */
  homeId: string;
};

/** Every adventure-body section must appear here with a reachable home. */
export const OF_CONKS_HEMPHOLM_PDF_HOMES: readonly PdfSectionHome[] = [
  { pdfHeading: "Of Conks & Cons", homeKind: "scene", homeId: "hook" },
  { pdfHeading: "The Greenfields", homeKind: "build", homeId: "Of Conks & Cons v2.1" },
  { pdfHeading: "Adventure Background", homeKind: "sheet", homeId: "npc:lord-fiddlestick" },
  { pdfHeading: "The Alchemist's Despair", homeKind: "beat", homeId: "hook-alchemist" },
  { pdfHeading: "In Service of the Guild", homeKind: "beat", homeId: "hook-guild" },
  { pdfHeading: "A Small Hamlet on the Horizon", homeKind: "beat", homeId: "hook-hill" },
  { pdfHeading: "Adventure Summary", homeKind: "scene", homeId: "arrive" },
  { pdfHeading: "Part 1: Enter Hempholm", homeKind: "scene", homeId: "village-sandbox" },
  { pdfHeading: "Area 1: The Shacks", homeKind: "beat", homeId: "shacks-arrival" },
  { pdfHeading: "Area 2: The Store", homeKind: "beat", homeId: "morwin-store" },
  { pdfHeading: "Area 3: Saladin’s Wagon", homeKind: "beat", homeId: "saladin-wagon" },
  { pdfHeading: "Area 4: The Jove's Home", homeKind: "beat", homeId: "jove-plea" },
  { pdfHeading: "Area 5: The Grotesque Tree", homeKind: "beat", homeId: "tree-tactics" },
  { pdfHeading: "A Broken Distillery", homeKind: "beat", homeId: "distillery" },
  { pdfHeading: "Diamonds In the Rough", homeKind: "beat", homeId: "gem-job" },
  { pdfHeading: "Competition in the Shacks", homeKind: "beat", homeId: "meal-moonshine" },
  { pdfHeading: "The Growth Spurt", homeKind: "beat", homeId: "growth-spurt" },
  { pdfHeading: "Mount the Attack!", homeKind: "beat", homeId: "axe-villagers" },
  { pdfHeading: "A Premature Celebration", homeKind: "beat", homeId: "celebration-party" },
  { pdfHeading: "Never Split the Party", homeKind: "beat", homeId: "never-split" },
  { pdfHeading: "Hempholm Caught Fire?", homeKind: "beat", homeId: "firefighting" },
  { pdfHeading: "Rampage Of the Caretakers", homeKind: "beat", homeId: "caretaker-wave" },
  { pdfHeading: "Down Into the Rabbit Hole", homeKind: "beat", homeId: "rabbit-hole" },
  { pdfHeading: "The Marrow", homeKind: "beat", homeId: "marrow-fight" },
  { pdfHeading: "The Fate of the Child", homeKind: "beat", homeId: "cut-sack" },
  { pdfHeading: "Hempholm’s Gratitude", homeKind: "beat", homeId: "gratitude" },
  { pdfHeading: "An Agent of the Mages’ Guild", homeKind: "beat", homeId: "paelias" },
  { pdfHeading: "Grotesque Tree", homeKind: "sheet", homeId: "threat:grotesque-tree" },
  { pdfHeading: "Guardian", homeKind: "sheet", homeId: "threat:guardian" },
  { pdfHeading: "Maglubiyet’s Statue", homeKind: "sheet", homeId: "item:maglubiyets-statue" },
  { pdfHeading: "Belly’s Mouthwash", homeKind: "sheet", homeId: "item:bellys-mouthwash" },
  { pdfHeading: "Appendix C: Tables", homeKind: "panel", homeId: "roll" },
];

/** Headings deliberately omitted from Play (publishing chrome). */
export const OF_CONKS_HEMPHOLM_PDF_OMITTED: readonly string[] = [
  "Table of Contents",
  "Credits & Afterword",
];
