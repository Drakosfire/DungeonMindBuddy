import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  LiveApiError,
  getRecapArtifacts,
  postWorldGraphRecapProjection,
} from "../../api/liveApi";
import type { RecapArtifactRecord, WorldGraphRecapProjection } from "../../api/types";
import { buildWorldGraphRecapProjectionRequest } from "../../worldGraph/worldGraphSurfaceContext";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import type { PlanContextDescriptor } from "../types";
import {
  defaultRecapSessionIdForCampaign,
  requestedRecapSessionIdFromLocation,
  resolveInitialReviewCampaignId,
  resolveSessionRecapContext,
} from "../sessionCampaignContext";
import {
  filterNumericRecapArtifactRecords,
  sortRecapArtifactRecords,
} from "./recapSessionLabels";
import { WorldGraphRecapProjectionView } from "./WorldGraphRecapProjection";

type LoadStatus = "loading" | "ready" | "error";

/** Legacy Union recap source labels retained for GraphIngestProjectionPanel consumers. */
export type RecapProjectionSource =
  | "latest-graph-ingest"
  | "recap-only"
  | "default-preview-source"
  | "legacy"
  | "unavailable";

interface RecapGraphModuleProps {
  context: PlanContextDescriptor;
}

const DOGFOOD_SESSION_OPTIONS = ["session-1", "session-21", "session-22", "session-23"];

function requestedSessionFromLocation(): string | null {
  return requestedRecapSessionIdFromLocation();
}

function syncRecapSurfaceUrl(campaignId: string, sessionId?: string) {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  params.set("campaign", campaignId);
  params.set("scopeMode", "campaign");
  params.delete("run");
  if (sessionId) {
    params.set("session", sessionId);
  }
  const path = window.location.pathname.replace(/\/+$/, "") || "/plan";
  const surfacePath = path === "/ingest" ? "/ingest" : "/plan";
  window.history.replaceState({}, "", `${surfacePath}?${params.toString()}`);
}

function recapUnavailableMessage(error: unknown, sessionId: string, campaignId: string): string {
  if (error instanceof LiveApiError) {
    if (error.status === 404 && error.code === "recap_markdown_unavailable") {
      return `Canonical normalized recap is unavailable for ${sessionId} in ${campaignId}.`;
    }
    if (error.status === 404 || error.status === 400) {
      return `Published World Graph recap is unavailable for ${sessionId} in ${campaignId}.`;
    }
    if (error.status === 422) {
      return error.message || "World Graph recap request was invalid for the selected context.";
    }
    return error.message;
  }
  return error instanceof Error ? error.message : "Failed to load published World Graph recap.";
}

export function RecapGraphModule({ context }: RecapGraphModuleProps) {
  const requestedSessionId = requestedSessionFromLocation();
  const fallbackSessionId = `session-${context.ingestSession}`;
  const defaultSessionId = requestedSessionId ?? fallbackSessionId;
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [recapPayload, setRecapPayload] = useState<WorldGraphRecapProjection | null>(null);
  const [sessionRecords, setSessionRecords] = useState<RecapArtifactRecord[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState(defaultSessionId);
  const [selectedCampaignId, setSelectedCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
  const [readyRecapContext, setReadyRecapContext] = useState<{
    campaignId: string;
    sessionId: string;
  } | null>(null);
  const honorExplicitUrlSessionRef = useRef(requestedSessionId != null);
  const selectedSessionIdRef = useRef(selectedSessionId);
  selectedSessionIdRef.current = selectedSessionId;

  const campaignSessionRecords = useMemo(
    () => sessionRecords.filter((record) => record.campaign_id === selectedCampaignId),
    [selectedCampaignId, sessionRecords],
  );

  const sessionOptions = useMemo(() => {
    const options = new Set(campaignSessionRecords.length > 0 ? [] : DOGFOOD_SESSION_OPTIONS);
    options.add(`session-${context.ingestSession}`);
    options.add(selectedSessionId);
    if (honorExplicitUrlSessionRef.current && requestedSessionId) {
      options.add(requestedSessionId);
    }
    campaignSessionRecords.forEach((record) => options.add(record.session_id));
    return [...options].sort((left, right) => {
      const leftNum = Number.parseInt(left.replace("session-", ""), 10);
      const rightNum = Number.parseInt(right.replace("session-", ""), 10);
      return leftNum - rightNum;
    });
  }, [campaignSessionRecords, context.ingestSession, requestedSessionId, selectedSessionId]);

  const loadRecapProjection = useCallback(async (sessionId = selectedSessionId) => {
    setStatus("loading");
    setError(null);
    const { campaignId } = resolveSessionRecapContext(
      sessionId,
      selectedCampaignId,
      sessionRecords,
    );
    const request = buildWorldGraphRecapProjectionRequest({ campaignId, sessionId });
    if (!request) {
      setRecapPayload(null);
      setError(`World Graph mapping is unavailable for campaign ${campaignId}.`);
      setStatus("error");
      return;
    }

    try {
      const projection = await postWorldGraphRecapProjection(request);
      setRecapPayload(projection);
      setStatus("ready");
    } catch (loadError) {
      setRecapPayload(null);
      setError(recapUnavailableMessage(loadError, sessionId, campaignId));
      setStatus("error");
    }
  }, [selectedCampaignId, selectedSessionId, sessionRecords]);

  useEffect(() => {
    let cancelled = false;
    setReadyRecapContext(null);

    void getRecapArtifacts(selectedCampaignId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        const records = sortRecapArtifactRecords(
          filterNumericRecapArtifactRecords(response.records),
        );
        setSessionRecords(records);
        const campaignRecords = records.filter((record) => record.campaign_id === selectedCampaignId);
        const honorExplicitUrl = honorExplicitUrlSessionRef.current;
        const explicitSessionId = honorExplicitUrl ? requestedRecapSessionIdFromLocation() : null;
        const currentSessionId = selectedSessionIdRef.current;
        const stillValid = campaignRecords.some((record) => record.session_id === currentSessionId);
        // Explicit hard-load ?session= reaches the recap endpoint unchanged, even when
        // the artifact listing is stale. Interactive campaign switch must not carry a
        // previous campaign's session into a campaign that does not offer it.
        const nextSessionId = honorExplicitUrl
          ? (explicitSessionId ?? defaultRecapSessionIdForCampaign(campaignRecords, fallbackSessionId))
          : (stillValid
            ? currentSessionId
            : defaultRecapSessionIdForCampaign(campaignRecords, fallbackSessionId));
        setSelectedSessionId(nextSessionId);
        syncRecapSurfaceUrl(selectedCampaignId, nextSessionId);
        setReadyRecapContext({ campaignId: selectedCampaignId, sessionId: nextSessionId });
      })
      .catch(() => {
        if (!cancelled) {
          setSessionRecords([]);
          const honorExplicitUrl = honorExplicitUrlSessionRef.current;
          const nextSessionId = honorExplicitUrl
            ? (requestedRecapSessionIdFromLocation() ?? fallbackSessionId)
            : fallbackSessionId;
          setSelectedSessionId(nextSessionId);
          syncRecapSurfaceUrl(selectedCampaignId, nextSessionId);
          setReadyRecapContext({ campaignId: selectedCampaignId, sessionId: nextSessionId });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fallbackSessionId, selectedCampaignId]);

  useEffect(() => {
    if (!readyRecapContext) {
      return;
    }
    if (readyRecapContext.campaignId !== selectedCampaignId) {
      return;
    }
    void loadRecapProjection(readyRecapContext.sessionId);
  }, [loadRecapProjection, readyRecapContext, selectedCampaignId]);

  const handleCampaignSelect = (campaignId: string) => {
    honorExplicitUrlSessionRef.current = false;
    setSelectedCampaignId(campaignId);
  };

  const handleSessionSelect = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setReadyRecapContext({ campaignId: selectedCampaignId, sessionId });
    syncRecapSurfaceUrl(selectedCampaignId, sessionId);
  };

  const reviewToolbar = (
    <div className="recap-reader-toolbar">
      <ReviewCampaignPicker selectedCampaignId={selectedCampaignId} onSelect={handleCampaignSelect} />
      <label className="graph-preview-run-picker">
        <span>Focus session</span>
        <select value={selectedSessionId} onChange={(event) => handleSessionSelect(event.target.value)}>
          {sessionOptions.map((sessionId) => (
            <option key={sessionId} value={sessionId}>
              {sessionId.replace("session-", "Session ")}
            </option>
          ))}
        </select>
      </label>
    </div>
  );

  if (status === "loading") {
    return (
      <div className="recap-reader-root">
        {reviewToolbar}
        <p className="plan-projection-empty">Loading published World Graph recap…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="recap-reader-root">
        {reviewToolbar}
        <p className="graph-preview-error" role="alert">
          {error ?? `Published World Graph recap is unavailable for ${selectedSessionId}.`}
        </p>
        <button type="button" onClick={() => void loadRecapProjection(selectedSessionId)}>
          Retry
        </button>
      </div>
    );
  }

  if (recapPayload) {
    return (
      <WorldGraphRecapProjectionView
        payload={recapPayload}
        selectedSessionId={selectedSessionId}
        onSelectSession={handleSessionSelect}
        sessionOptions={sessionOptions}
        selectedCampaignId={selectedCampaignId}
        onSelectCampaign={handleCampaignSelect}
      />
    );
  }

  return (
    <div className="recap-reader-root">
      {reviewToolbar}
      <p className="plan-projection-empty">No published World Graph recap loaded.</p>
    </div>
  );
}
