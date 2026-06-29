import { useCallback, useEffect, useMemo, useState } from "react";

import {
  LiveApiError,
  getRecapArtifacts,
  getUnionSupergraphProjection,
} from "../../api/liveApi";
import type {
  RecapArtifactRecord,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import type { PlanContextDescriptor } from "../types";
import { UnionSupergraphRecapProjection } from "./UnionSupergraphRecapProjection";
import {
  filterNumericRecapArtifactRecords,
  sortRecapArtifactRecords,
} from "./recapSessionLabels";

type LoadStatus = "loading" | "ready" | "error";
export type RecapProjectionSource =
  | "latest-graph-ingest"
  | "recap-only"
  | "default-preview-source"
  | "legacy"
  | "unavailable";

interface RecapGraphModuleProps {
  context: PlanContextDescriptor;
}

const DOGFOOD_SESSION_OPTIONS = ["session-21", "session-22", "session-23"];

function requestedSessionFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  const session = new URLSearchParams(window.location.search).get("session")?.trim();
  return session || null;
}

function isExpectedProjectionMiss(error: unknown): boolean {
  return error instanceof LiveApiError && (error.status === 400 || error.status === 404);
}

export function RecapGraphModule({ context }: RecapGraphModuleProps) {
  const requestedSessionId = requestedSessionFromLocation();
  const fallbackSessionId = `session-${context.ingestSession}`;
  const defaultSessionId = requestedSessionId ?? fallbackSessionId;
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [unionPayload, setUnionPayload] = useState<UnionSupergraphProjectionResponse | null>(null);
  const [projectionSource, setProjectionSource] = useState<RecapProjectionSource>("unavailable");
  const [sessionRecords, setSessionRecords] = useState<RecapArtifactRecord[]>([]);
  const [artifactsLoaded, setArtifactsLoaded] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState(defaultSessionId);

  const sessionOptions = useMemo(() => {
    const options = new Set(sessionRecords.length > 0 ? [] : DOGFOOD_SESSION_OPTIONS);
    options.add(`session-${context.ingestSession}`);
    options.add(defaultSessionId);
    sessionRecords.forEach((record) => options.add(record.session_id));
    return [...options].sort((left, right) => {
      const leftNum = Number.parseInt(left.replace("session-", ""), 10);
      const rightNum = Number.parseInt(right.replace("session-", ""), 10);
      return leftNum - rightNum;
    });
  }, [context.ingestSession, defaultSessionId, sessionRecords]);


  const loadUnionProjection = useCallback(async (sessionId = selectedSessionId) => {
    setStatus("loading");
    setError(null);
    const selectedRecord = sessionRecords.find((record) => record.session_id === sessionId);
    try {
      const projection = await getUnionSupergraphProjection({
        campaignId: context.campaignId,
        sessionId,
        useLatestGraphIngest: true,
        sourceRecapPath: selectedRecord?.source_recap_path,
        sourceRecapSha256: selectedRecord?.source_sha256,
      });
      setUnionPayload(projection);
      setProjectionSource("latest-graph-ingest");
      setStatus("ready");
      return;
    } catch (latestError) {
      if (!isExpectedProjectionMiss(latestError)) {
        setUnionPayload(null);
        setProjectionSource("unavailable");
        setError(latestError instanceof Error ? latestError.message : "Failed to load latest graph-ingest projection");
        setStatus("error");
        return;
      }
    }

    if (selectedRecord) {
      setUnionPayload(null);
      setProjectionSource("unavailable");
      setError(
        `Graph projection is not ready for ${sessionId}. Recap memory exists, but no lineage-matched preview union projection was found.`,
      );
      setStatus("error");
      return;
    }

    setUnionPayload(null);
    setProjectionSource("unavailable");
    setError(`No ingested recap artifact or union-supergraph projection is available for ${sessionId}.`);
    setStatus("error");
  }, [context.campaignId, selectedSessionId, sessionRecords]);

  useEffect(() => {
    let cancelled = false;
    setArtifactsLoaded(false);

    void getRecapArtifacts(context.campaignId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        const records = sortRecapArtifactRecords(filterNumericRecapArtifactRecords(response.records));
        setSessionRecords(records);
        setSelectedSessionId(requestedSessionId ?? records.at(-1)?.session_id ?? fallbackSessionId);
        setArtifactsLoaded(true);
      })
      .catch(() => {
        if (!cancelled) {
          setSessionRecords([]);
          setSelectedSessionId(defaultSessionId);
          setArtifactsLoaded(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [context.campaignId, defaultSessionId, fallbackSessionId, requestedSessionId]);

  useEffect(() => {
    if (!artifactsLoaded) {
      return;
    }
    void loadUnionProjection(selectedSessionId);
  }, [artifactsLoaded, loadUnionProjection, selectedSessionId]);

  if (status === "loading") {
    return <p className="plan-projection-empty">Loading union supergraph projection…</p>;
  }

  if (status === "error") {
    return (
      <div className="recap-reader-root">
        <p className="graph-preview-error" role="alert">
          {error ?? `No union-supergraph projection is available for ${selectedSessionId}.`}
        </p>
        <button type="button" onClick={() => void loadUnionProjection(selectedSessionId)}>
          Retry
        </button>
      </div>
    );
  }

  if (unionPayload) {
    return (
      <UnionSupergraphRecapProjection
        payload={unionPayload}
        selectedSessionId={selectedSessionId}
        onSelectSession={(sessionId) => {
          setSelectedSessionId(sessionId);
        }}
        sessionOptions={sessionOptions}
        projectionSource={projectionSource}
      />
    );
  }

  return <p className="plan-projection-empty">No union-supergraph projection loaded.</p>;
}
