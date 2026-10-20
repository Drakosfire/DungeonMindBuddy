import type { ExtractionRunRecord } from "../api/types";

/** Captured initial navigation data, not continuously current action authority. */
export interface IngestNavigationOwner {
  worldId: string | null;
  search: string;
  generation: number;
  accessGeneration: number;
}
export type IngestInitialRunObservation =
  | { status: "not_applicable" | "loading"; owner: IngestNavigationOwner }
  | { status: "error"; owner: IngestNavigationOwner; message: string }
  | { status: "ready"; owner: IngestNavigationOwner; run: ExtractionRunRecord };
