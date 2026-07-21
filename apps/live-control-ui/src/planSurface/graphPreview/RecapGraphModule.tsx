import { useCallback, useEffect, useMemo, useState } from "react";

import {
  LiveApiError,
  getRecapArtifacts,
  postWorldGraphRecapProjection,
} from "../../api/liveApi";
import type {
  RecapArtifactRecord,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import type { PlanContextDescriptor } from "../types";
import {
  resolveInitialReviewCampaignId,
  resolveSessionRecapContext,
  syncReviewCampaignUrl,
} from "../sessionCampaignContext";
import {
  buildPlanWorldGraphProjectionRequest,
  type PlanWorldGraphContext,
} from "../reference/planGraphContextRequest";
import { UnionSupergraphRecapProjection } from "./UnionSupergraphRecapProjection";
import {
  filterNumericRecapArtifactRecords,
  sortRecapArtifactRecords,
} from "./recapSessionLabels";

type LoadStatus = "loading" | "ready" | "error";
export type RecapProjectionSource =
  | "world-graph"
  | "recap-only"
  | "default-preview-source"
  | "legacy"
  | "unavailable";

interface RecapGraphModuleProps {
  context: PlanContextDescriptor;
}

const DOGFOOD_SESSION_OPTIONS = ["session-1", "session-21", "session-22", "session-23"];

const WORLD_ID_BY_CAMPAIGN: Record<string, string> = {
  "longmont-c1": "eldyrwild",
  "longmont-c2": "eldyrwild",
};

function requestedSessionFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  const session = new URLSearchParams(window.location.search).get("session")?.trim();
  return session || null;
}

function buildRecapWorldGraphContext(
  campaignId: string,
  sessionId: string,
): PlanWorldGraphContext | null {
  const worldId = WORLD_ID_BY_CAMPAIGN[campaignId];
  if (!worldId) return null;
  return {
    worldId,
    campaignId,
    scopeMode: "campaign",
    focus: {
      kind: "session",
      sessionId,
      focusCampaignId: campaignId,
    },
  };
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
  const [selectedCampaignId, setSelectedCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );

  const campaignSessionRecords = useMemo(
    () => sessionRecords.filter((record) => record.campaign_id === selectedCampaignId),
    [selectedCampaignId, sessionRecords],
  );

  const sessionOptions = useMemo(() => {
    const options = new Set(campaignSessionRecords.length > 0 ? [] : DOGFOOD_SESSION_OPTIONS);
    options.add(`session-${context.ingestSession}`);
    options.add(defaultSessionId);
    campaignSessionRecords.forEach((record) => options.add(record.session_id));
    return [...options].sort((left, right) => {
      const leftNum = Number.parseInt(left.replace("session-", ""), 10);
      const rightNum = Number.parseInt(right.replace("session-", ""), 10);
      return leftNum - rightNum;
    });
  }, [campaignSessionRecords, context.ingestSession, defaultSessionId]);

  const loadWorldRecapProjection = useCallback(async (sessionId = selectedSessionId) => {
    setStatus("loading");
    setError(null);
    const { campaignId, record: selectedRecord } = resolveSessionRecapContext(
      sessionId,
      selectedCampaignId,
      sessionRecords,
    );
    const worldContext = buildRecapWorldGraphContext(campaignId, sessionId);
    if (!worldContext) {
      setUnionPayload(null);
      setProjectionSource("unavailable");
      setError(`No World Graph mapping for campaign ${campaignId}.`);
      setStatus("error");
      return;
    }

    try {
      const projection = await postWorldGraphRecapProjection(
        buildPlanWorldGraphProjectionRequest(worldContext),
      );
      setUnionPayload(projection);
      setProjectionSource("world-graph");
      setStatus("ready");
    } catch (loadError) {
      setUnionPayload(null);
      setProjectionSource("unavailable");
      const message =
        loadError instanceof LiveApiError
          ? loadError.message
          : loadError instanceof Error
            ? loadError.message
            : "Failed to load World Graph recap projection";
      if (selectedRecord) {
        setError(
          `World Graph recap projection is unavailable for ${sessionId} in ${campaignId}. ${message}`,
        );
      } else {
        setError(
          `No World Graph recap projection is available for ${sessionId} in ${selectedCampaignId}. ${message}`,
        );
      }
      setStatus("error");
    }
  }, [selectedCampaignId, selectedSessionId, sessionRecords]);

  useEffect(() => {
    let cancelled = false;
    setArtifactsLoaded(false);

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
        const nextSessionId =
          requestedSessionId && campaignRecords.some((record) => record.session_id === requestedSessionId)
            ? requestedSessionId
            : (campaignRecords.at(-1)?.session_id ?? fallbackSessionId);
        setSelectedSessionId(nextSessionId);
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
  }, [defaultSessionId, fallbackSessionId, requestedSessionId, selectedCampaignId]);

  useEffect(() => {
    if (!artifactsLoaded) {
      return;
    }
    void loadWorldRecapProjection(selectedSessionId);
  }, [artifactsLoaded, loadWorldRecapProjection, selectedSessionId]);

  const handleCampaignSelect = (campaignId: string) => {
    setSelectedCampaignId(campaignId);
    syncReviewCampaignUrl(campaignId);
  };

  const handleSessionSelect = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      params.set("session", sessionId);
      params.set("campaign", selectedCampaignId);
      window.history.replaceState({}, "", `/plan?${params.toString()}`);
    }
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
    return <p className="plan-projection-empty">Loading World Graph recap projection…</p>;
  }

  if (status === "error") {
    return (
      <div className="recap-reader-root">
        {reviewToolbar}
        <p className="graph-preview-error" role="alert">
          {error ?? `No World Graph recap projection is available for ${selectedSessionId}.`}
        </p>
        <button type="button" onClick={() => void loadWorldRecapProjection(selectedSessionId)}>
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
        onSelectSession={handleSessionSelect}
        sessionOptions={sessionOptions}
        projectionSource={projectionSource}
        selectedCampaignId={selectedCampaignId}
        onSelectCampaign={handleCampaignSelect}
      />
    );
  }

  return <p className="plan-projection-empty">No World Graph recap projection loaded.</p>;
}
