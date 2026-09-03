import { useCallback, useEffect, useState } from "react";

import {
  createSurfaceInformationChannel,
  type SurfaceInformationChannel,
} from "../surfaceInformation";
import { getExtractionRunCatalog, type ExtractionRunCatalogResponse } from "./ingestRunCatalogApi";
import {
  INGEST_RUN_CATALOG_DESCRIPTOR,
  mapIngestRunCatalogObservation,
} from "./ingestRunCatalogSurfaceInformation";
import { GRAPH_REVIEW_RUNS_CHANGED_EVENT } from "../planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils";

export interface UseIngestRunCatalogInformationResult {
  channel: SurfaceInformationChannel<ExtractionRunCatalogResponse>;
  refresh: () => void;
}

function loadCatalog(channel: SurfaceInformationChannel<ExtractionRunCatalogResponse>): void {
  const ticket = channel.beginObservation();
  if (!ticket) return;
  void (async () => {
    try {
      const response = await getExtractionRunCatalog();
      channel.commit(ticket, mapIngestRunCatalogObservation({ response }));
    } catch (error) {
      channel.commit(ticket, mapIngestRunCatalogObservation({ error }));
    }
  })();
}

export function useIngestRunCatalogInformation(): UseIngestRunCatalogInformationResult {
  const [channel] = useState(() =>
    createSurfaceInformationChannel<ExtractionRunCatalogResponse>(INGEST_RUN_CATALOG_DESCRIPTOR),
  );

  useEffect(() => {
    loadCatalog(channel);
    return () => {
      channel.dispose();
    };
  }, [channel]);

  const refresh = useCallback(() => {
    loadCatalog(channel);
  }, [channel]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onRunsChanged = () => refresh();
    window.addEventListener(GRAPH_REVIEW_RUNS_CHANGED_EVENT, onRunsChanged);
    return () => window.removeEventListener(GRAPH_REVIEW_RUNS_CHANGED_EVENT, onRunsChanged);
  }, [refresh]);

  return { channel, refresh };
}
