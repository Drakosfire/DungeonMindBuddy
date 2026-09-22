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
  params.delete("scopeMode");
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
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [recapPayload, setRecapPayload] = useState<WorldGraphRecapProjection | null>(null);
  const [sessionRecords, setSessionRecords] = useState<RecapArtifactRecord[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState(defaultSessionId);
  const [selectedCampaignId, setSelectedCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
  const [draftSessionId, setDraftSessionId] = useState(defaultSessionId);
  const [draftCampaignId, setDraftCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
  const [readyRecapContext, setReadyRecapContext] = useState<{
    campaignId: string;
    sessionId: string;
  } | null>(null);
  const honorExplicitUrlSessionRef = useRef(requestedSessionId != null);
  const draftSessionIdRef = useRef(draftSessionId);
  draftSessionIdRef.current = draftSessionId;
  const initialLoadStartedRef = useRef(false);
  const loadGenerationRef = useRef(0);
  const [loadedScope, setLoadedScope] = useState<{
    campaignId: string;
    sessionId: string;
  } | null>(null);

  const campaignSessionRecords = useMemo(
    () => sessionRecords.filter((record) => record.campaign_id === draftCampaignId),
    [draftCampaignId, sessionRecords],
  );

  const selectedRecapRecord = useMemo(
    () =>
      loadedScope
        ? sessionRecords.find(
            (record) =>
              record.campaign_id === loadedScope.campaignId
              && record.session_id === loadedScope.sessionId,
          ) ?? null
        : null,
    [loadedScope, sessionRecords],
  );

  const sessionOptions = useMemo(() => {
    const options = new Set(campaignSessionRecords.length > 0 ? [] : DOGFOOD_SESSION_OPTIONS);
    options.add(`session-${context.ingestSession}`);
    options.add(draftSessionId);
    if (honorExplicitUrlSessionRef.current && requestedSessionId) {
      options.add(requestedSessionId);
    }
    campaignSessionRecords.forEach((record) => options.add(record.session_id));
    return [...options].sort((left, right) => {
      const leftNum = Number.parseInt(left.replace("session-", ""), 10);
      const rightNum = Number.parseInt(right.replace("session-", ""), 10);
      return leftNum - rightNum;
    });
  }, [campaignSessionRecords, context.ingestSession, draftSessionId, requestedSessionId]);

  const loadRecapProjection = useCallback(async (
    campaignId: string,
    sessionId: string,
  ) => {
    const generation = ++loadGenerationRef.current;
    setStatus("loading");
    setError(null);
    setRecapPayload(null);
    setLoadedScope(null);
    const { campaignId: resolvedCampaignId } = resolveSessionRecapContext(
      sessionId,
      campaignId,
      sessionRecords,
    );
    const request = buildWorldGraphRecapProjectionRequest({
      campaignId: resolvedCampaignId,
      sessionId,
    });
    if (!request) {
      if (generation !== loadGenerationRef.current) {
        return;
      }
      setRecapPayload(null);
      setLoadedScope(null);
      setError(`World Graph mapping is unavailable for campaign ${resolvedCampaignId}.`);
      setStatus("error");
      return;
    }

    try {
      const projection = await postWorldGraphRecapProjection(request);
      if (generation !== loadGenerationRef.current) {
        return;
      }
      setRecapPayload(projection);
      setLoadedScope({ campaignId: resolvedCampaignId, sessionId });
      setStatus("ready");
    } catch (loadError) {
      if (generation !== loadGenerationRef.current) {
        return;
      }
      setRecapPayload(null);
      setLoadedScope(null);
      setError(recapUnavailableMessage(loadError, sessionId, resolvedCampaignId));
      setStatus("error");
    }
  }, [sessionRecords]);

  useEffect(() => {
    let cancelled = false;
    setCatalogLoading(true);

    void getRecapArtifacts(draftCampaignId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        setCatalogLoading(false);
        const records = sortRecapArtifactRecords(
          filterNumericRecapArtifactRecords(response.records),
        );
        setSessionRecords(records);
        const campaignRecords = records.filter((record) => record.campaign_id === draftCampaignId);
        const honorExplicitUrl = honorExplicitUrlSessionRef.current;
        const explicitSessionId = honorExplicitUrl ? requestedRecapSessionIdFromLocation() : null;
        const currentSessionId = draftSessionIdRef.current;
        const stillValid = campaignRecords.some((record) => record.session_id === currentSessionId);
        // Explicit hard-load ?session= reaches the recap endpoint unchanged, even when
        // the artifact listing is stale. Interactive campaign switch must not carry a
        // previous campaign's session into a campaign that does not offer it.
        const nextSessionId = honorExplicitUrl
          ? (explicitSessionId ?? defaultRecapSessionIdForCampaign(campaignRecords, fallbackSessionId))
          : (stillValid
            ? currentSessionId
            : defaultRecapSessionIdForCampaign(campaignRecords, fallbackSessionId));
        draftSessionIdRef.current = nextSessionId;
        setDraftSessionId(nextSessionId);
        if (!initialLoadStartedRef.current) {
          initialLoadStartedRef.current = true;
          setSelectedCampaignId(draftCampaignId);
          setSelectedSessionId(nextSessionId);
          syncRecapSurfaceUrl(draftCampaignId, nextSessionId);
          setReadyRecapContext({ campaignId: draftCampaignId, sessionId: nextSessionId });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCatalogLoading(false);
          setSessionRecords([]);
          const honorExplicitUrl = honorExplicitUrlSessionRef.current;
          const nextSessionId = honorExplicitUrl
            ? (requestedRecapSessionIdFromLocation() ?? fallbackSessionId)
            : fallbackSessionId;
          draftSessionIdRef.current = nextSessionId;
          setDraftSessionId(nextSessionId);
          if (!initialLoadStartedRef.current) {
            initialLoadStartedRef.current = true;
            setSelectedCampaignId(draftCampaignId);
            setSelectedSessionId(nextSessionId);
            syncRecapSurfaceUrl(draftCampaignId, nextSessionId);
            setReadyRecapContext({ campaignId: draftCampaignId, sessionId: nextSessionId });
          }
        }
      });

    return () => {
      cancelled = true;
    };
  }, [draftCampaignId, fallbackSessionId]);

  useEffect(() => {
    if (!readyRecapContext) {
      return;
    }
    if (readyRecapContext.campaignId !== selectedCampaignId) {
      return;
    }
    void loadRecapProjection(readyRecapContext.campaignId, readyRecapContext.sessionId);
  }, [loadRecapProjection, readyRecapContext, selectedCampaignId]);

  const handleCampaignSelect = (campaignId: string) => {
    honorExplicitUrlSessionRef.current = false;
    setDraftCampaignId(campaignId);
  };

  const handleSessionSelect = (sessionId: string) => {
    draftSessionIdRef.current = sessionId;
    setDraftSessionId(sessionId);
  };

  const handleLoad = () => {
    if (catalogLoading || !draftCampaignId || !draftSessionId) return;
    setSelectedCampaignId(draftCampaignId);
    setSelectedSessionId(draftSessionId);
    setReadyRecapContext({ campaignId: draftCampaignId, sessionId: draftSessionId });
    syncRecapSurfaceUrl(draftCampaignId, draftSessionId);
  };

  const authorableRecap =
    status === "ready" &&
    recapPayload &&
    loadedScope
      ? recapPayload
      : null;

  const reviewToolbar = (
    <div className="recap-reader-toolbar">
      <ReviewCampaignPicker selectedCampaignId={draftCampaignId} onSelect={handleCampaignSelect} />
      <label className="graph-preview-run-picker">
        <span>Focus session</span>
        <select value={draftSessionId} onChange={(event) => handleSessionSelect(event.target.value)}>
          {sessionOptions.map((sessionId) => (
            <option key={sessionId} value={sessionId}>
              {sessionId.replace("session-", "Session ")}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        className="primary recap-reader-load-button"
        onClick={handleLoad}
        disabled={catalogLoading || !draftCampaignId || !draftSessionId || status === "loading"}
      >
        {status === "loading" ? "Loading…" : "Load"}
      </button>
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
        <button type="button" onClick={handleLoad}>
          Load
        </button>
      </div>
    );
  }

  if (authorableRecap) {
    return (
      <WorldGraphRecapProjectionView
        payload={authorableRecap}
        selectedSessionId={selectedSessionId}
        onSelectSession={handleSessionSelect}
        sessionOptions={sessionOptions}
        selectedCampaignId={selectedCampaignId}
        onSelectCampaign={handleCampaignSelect}
        draftCampaignId={draftCampaignId}
        draftSessionId={draftSessionId}
        onLoad={handleLoad}
        canLoad={!catalogLoading}
        recapRecord={selectedRecapRecord}
        onRefreshProjection={() => loadRecapProjection(selectedCampaignId, selectedSessionId)}
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
