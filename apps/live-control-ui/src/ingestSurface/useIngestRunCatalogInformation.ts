import { useCallback, useEffect, useRef, useState } from "react";

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

/**
 * Owns one APP-STATE ExtractionRun catalog channel for the Ingest page.
 *
 * Channel lifetime is bound to the mount effect (create + dispose), not to a
 * useState singleton. Disposing a useState channel on effect cleanup permanently
 * kills observation under React StrictMode remounts and leaves /ingest stuck on
 * "Loading graph review sessions…".
 */
export function useIngestRunCatalogInformation(): UseIngestRunCatalogInformationResult {
  const [channel, setChannel] = useState(() =>
    createSurfaceInformationChannel<ExtractionRunCatalogResponse>(INGEST_RUN_CATALOG_DESCRIPTOR),
  );
  const channelRef = useRef(channel);
  channelRef.current = channel;

  useEffect(() => {
    const owned = createSurfaceInformationChannel<ExtractionRunCatalogResponse>(
      INGEST_RUN_CATALOG_DESCRIPTOR,
    );
    channelRef.current = owned;
    setChannel(owned);
    loadCatalog(owned);
    return () => {
      owned.dispose();
    };
  }, []);

  const refresh = useCallback(() => {
    loadCatalog(channelRef.current);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onRunsChanged = () => refresh();
    window.addEventListener(GRAPH_REVIEW_RUNS_CHANGED_EVENT, onRunsChanged);
    return () => window.removeEventListener(GRAPH_REVIEW_RUNS_CHANGED_EVENT, onRunsChanged);
  }, [refresh]);

  return { channel, refresh };
}
