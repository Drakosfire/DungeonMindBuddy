import { useEffect, useMemo, useState } from "react";

import { getRecapArtifacts } from "../../api/liveApi";
import type { RecapArtifactRecord } from "../../api/types";
import { appHref } from "../../chrome/appBasePath";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import type { PlanContextDescriptor } from "../types";
import {
  resolveInitialReviewCampaignId,
  resolveSessionRecapContext,
  syncReviewCampaignUrl,
} from "../sessionCampaignContext";
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
  return new URLSearchParams(window.location.search).get("session")?.trim() || null;
}

export function GraphPreviewModule({ context }: GraphPreviewModuleProps) {
  const requestedSessionId = requestedSessionFromLocation();
  const fallbackSessionId = `session-${context.ingestSession}`;
  const [sessionRecords, setSessionRecords] = useState<RecapArtifactRecord[]>([]);
  const [artifactsLoaded, setArtifactsLoaded] = useState(false);
  const [selectedCampaignId, setSelectedCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
  const [selectedSessionId, setSelectedSessionId] = useState(requestedSessionId ?? fallbackSessionId);

  const campaignSessionRecords = useMemo(
    () => sessionRecords.filter((record) => record.campaign_id === selectedCampaignId),
    [selectedCampaignId, sessionRecords],
  );

  const selectedRecord = resolveSessionRecapContext(
    selectedSessionId,
    selectedCampaignId,
    sessionRecords,
  ).record;

  const sessionOptions = useMemo(() => {
    const options = campaignSessionRecords.map((record) => record.session_id);
    if (options.length === 0) {
      options.push(selectedSessionId);
    }
    return options.sort((left, right) => {
      const leftNum = Number.parseInt(left.replace("session-", ""), 10);
      const rightNum = Number.parseInt(right.replace("session-", ""), 10);
      return leftNum - rightNum;
    });
  }, [campaignSessionRecords, selectedSessionId]);

  useEffect(() => {
    let cancelled = false;
    setArtifactsLoaded(false);

    void getRecapArtifacts(selectedCampaignId)
      .then((response) => {
        if (cancelled) return;
        const records = sortRecapArtifactRecords(filterNumericRecapArtifactRecords(response.records));
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
          setSelectedSessionId(requestedSessionId ?? fallbackSessionId);
          setArtifactsLoaded(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fallbackSessionId, requestedSessionId, selectedCampaignId]);

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
      window.history.replaceState({}, "", appHref(`/plan?${params.toString()}`));
    }
  };

  if (!artifactsLoaded) {
    return <p className="plan-projection-empty">Loading graph-ingest projection…</p>;
  }

  return (
    <div className="graph-preview-root">
      <div className="recap-reader-toolbar graph-preview-toolbar">
        <ReviewCampaignPicker selectedCampaignId={selectedCampaignId} onSelect={handleCampaignSelect} />
        <label className="graph-preview-run-picker">
          <span>Session</span>
          <select value={selectedSessionId} onChange={(event) => handleSessionSelect(event.target.value)}>
            {sessionOptions.map((sessionId) => (
              <option key={sessionId} value={sessionId}>
                {sessionId.replace("session-", "Session ")}
              </option>
            ))}
          </select>
        </label>
      </div>
      <GraphIngestProjectionPanel
        context={{ ...context, campaignId: selectedCampaignId }}
        sessionId={selectedSessionId}
        sourceRecapPath={selectedRecord?.source_recap_path}
        sourceRecapSha256={selectedRecord?.source_sha256 ?? undefined}
      />
    </div>
  );
}
