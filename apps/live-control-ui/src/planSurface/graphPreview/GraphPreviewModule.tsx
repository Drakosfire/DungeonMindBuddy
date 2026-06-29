import { useEffect, useState } from "react";

import { getRecapArtifacts } from "../../api/liveApi";
import type { RecapArtifactRecord } from "../../api/types";
import type { PlanContextDescriptor } from "../types";
import { GraphIngestProjectionPanel } from "./GraphIngestProjectionPanel";
import {
  filterNumericRecapArtifactRecords,
  sortRecapArtifactRecords,
} from "./recapSessionLabels";

interface GraphPreviewModuleProps {
  context: PlanContextDescriptor;
}

function requestedSessionFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  const session = new URLSearchParams(window.location.search).get("session")?.trim();
  return session || null;
}

export function GraphPreviewModule({ context }: GraphPreviewModuleProps) {
  const requestedSessionId = requestedSessionFromLocation();
  const fallbackSessionId = `session-${context.ingestSession}`;
  const [sessionRecords, setSessionRecords] = useState<RecapArtifactRecord[]>([]);
  const [artifactsLoaded, setArtifactsLoaded] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState(requestedSessionId ?? fallbackSessionId);

  const selectedRecord = sessionRecords.find((record) => record.session_id === selectedSessionId);

  useEffect(() => {
    let cancelled = false;
    setArtifactsLoaded(false);

    void getRecapArtifacts(context.campaignId)
      .then((response) => {
        if (cancelled) return;
        const records = sortRecapArtifactRecords(filterNumericRecapArtifactRecords(response.records));
        setSessionRecords(records);
        setSelectedSessionId(requestedSessionId ?? records.at(-1)?.session_id ?? fallbackSessionId);
        setArtifactsLoaded(true);
      })
      .catch(() => {
        if (!cancelled) {
          setSessionRecords([]);
          setSelectedSessionId(requestedSessionId ?? fallbackSessionId);
          setArtifactsLoaded(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [context.campaignId, fallbackSessionId, requestedSessionId]);

  if (!artifactsLoaded) {
    return <p className="plan-projection-empty">Loading graph-ingest projection…</p>;
  }

  return (
    <div className="graph-preview-root">
      <GraphIngestProjectionPanel
        context={context}
        sessionId={selectedSessionId}
        sourceRecapPath={selectedRecord?.source_recap_path}
        sourceRecapSha256={selectedRecord?.source_sha256 ?? undefined}
      />
    </div>
  );
}
