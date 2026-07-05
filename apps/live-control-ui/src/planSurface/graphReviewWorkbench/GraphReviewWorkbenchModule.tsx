import { useCallback, useEffect, useMemo, useState } from "react";

import { getGoldReviewCompare, getGoldReviewSessions, getManualReviewBed, getManualReviewBeds, LiveApiError } from "../../api/liveApi";
import type { GoldReviewCompareResponse, GoldReviewSessionSummary, ManualReviewBedDetail, ManualReviewBedSummary } from "../../api/types";
import type { GoldReviewSelection } from "../graphGoldReview/graphGoldReviewUtils";
import { requestedSessionFromLocation } from "../graphGoldReview/graphGoldReviewUtils";
import type { PlanContextDescriptor } from "../types";
import {
  resolveInitialReviewCampaignId,
  sessionsForReviewCampaign,
  syncReviewCampaignUrl,
} from "../sessionCampaignContext";
import { GraphReviewAuthoringWorkbenchModule } from "./GraphReviewAuthoringWorkbenchModule";
import { GraphReviewLaneCards } from "./GraphReviewLaneCards";
import { GraphReviewLanePicker } from "./GraphReviewLanePicker";
import { GraphReviewLiveProjectionPanel } from "./GraphReviewLiveProjectionPanel";
import { GraphReviewMetricPanel } from "./GraphReviewMetricPanel";
import {
  goldSessionToLane,
  graphIngestRunToLane,
  pickDefaultWorkbenchRun,
  pickDefaultWorkbenchSession,
} from "./graphReviewWorkbenchUtils";
import { manualVariantToLaneView } from "./graphReviewVariantReferenceUtils";

interface GraphReviewWorkbenchModuleProps {
  context: PlanContextDescriptor;
}

function syncGraphReviewUrl(sessionId: string, campaignId: string): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  params.set("session", sessionId);
  params.set("campaign", campaignId);
  const path = window.location.pathname.replace(/\/+$/, "") || "/plan";
  const surfacePath = path === "/ingest" ? "/ingest" : "/plan";
  if (surfacePath === "/plan") {
    params.set("tool", "graph-review");
  } else {
    params.delete("tool");
  }
  window.history.replaceState({}, "", `${surfacePath}?${params.toString()}`);
}

export function GraphReviewWorkbenchModule({ context }: GraphReviewWorkbenchModuleProps) {
  const fallbackSessionId = `session-${context.ingestSession}`;
  const requestedSessionId = requestedSessionFromLocation();

  const [sessions, setSessions] = useState<GoldReviewSessionSummary[]>([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [selectedCampaignId, setSelectedCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
  const [selectedSessionId, setSelectedSessionId] = useState(requestedSessionId ?? fallbackSessionId);
  const [selectedManifestPath, setSelectedManifestPath] = useState<string | null>(null);
  const [compare, setCompare] = useState<GoldReviewCompareResponse | null>(null);
  const [compareStatus, setCompareStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [compareError, setCompareError] = useState<string | null>(null);
  const [selection, setSelection] = useState<GoldReviewSelection | null>(null);
  const [manualBeds, setManualBeds] = useState<ManualReviewBedSummary[]>([]);
  const [manualBedsStatus, setManualBedsStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [manualBedsError, setManualBedsError] = useState<string | null>(null);
  const [selectedManualBedId, setSelectedManualBedId] = useState<string | null>(null);
  const [selectedManualBed, setSelectedManualBed] = useState<ManualReviewBedDetail | null>(null);
  const [selectedManualVariantName, setSelectedManualVariantName] = useState<string | null>(null);

  const campaignSessions = useMemo(
    () => sessionsForReviewCampaign(sessions, selectedCampaignId),
    [selectedCampaignId, sessions],
  );

  const selectedSession = useMemo(
    () => campaignSessions.find((session) => session.session_id === selectedSessionId) ?? null,
    [campaignSessions, selectedSessionId],
  );

  const selectedLiveRun = useMemo(() => {
    if (!selectedSession) return null;
    return selectedSession.available_runs.find((run) => run.manifest_path === selectedManifestPath) ?? null;
  }, [selectedManifestPath, selectedSession]);

  const goldLane = useMemo(() => (selectedSession ? goldSessionToLane(selectedSession) : null), [selectedSession]);
  const liveLane = useMemo(() => (selectedLiveRun ? graphIngestRunToLane(selectedLiveRun) : null), [selectedLiveRun]);
  const selectedVariantLaneView = useMemo(
    () => selectedManualBed && selectedManualVariantName ? manualVariantToLaneView({ bed: selectedManualBed, variantName: selectedManualVariantName }) : null,
    [selectedManualBed, selectedManualVariantName],
  );

  useEffect(() => {
    let cancelled = false;
    setSessionsLoaded(false);
    setSessionsError(null);
    void getGoldReviewSessions()
      .then((response) => {
        if (cancelled) return;
        const initialCampaignId = resolveInitialReviewCampaignId(context.campaignId);
        const visibleSessions = sessionsForReviewCampaign(response.sessions, initialCampaignId);
        const initialSession = pickDefaultWorkbenchSession(visibleSessions, requestedSessionId, fallbackSessionId);
        const initialRun = pickDefaultWorkbenchRun(initialSession?.available_runs ?? []);
        setSessions(response.sessions);
        setSelectedCampaignId(initialCampaignId);
        if (initialSession) {
          setSelectedSessionId(initialSession.session_id);
          setSelectedManifestPath(initialRun?.manifest_path ?? null);
        }
        setSessionsLoaded(true);
      })
      .catch((error) => {
        if (cancelled) return;
        setSessions([]);
        setSessionsError(error instanceof Error ? error.message : "Failed to load graph review sessions.");
        setSessionsLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [context.campaignId, fallbackSessionId, requestedSessionId]);

  useEffect(() => {
    let cancelled = false;
    setManualBedsStatus("loading");
    setManualBedsError(null);
    void getManualReviewBeds().then((response) => {
      if (cancelled) return;
      setManualBeds(response.beds);
      setManualBedsStatus("ready");
    }).catch((error) => {
      if (cancelled) return;
      setManualBeds([]);
      setManualBedsStatus("error");
      setManualBedsError(error instanceof Error ? error.message : "Failed to load manual review beds.");
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setSelectedManualBed(null);
    setSelectedManualVariantName(null);
    if (!selectedManualBedId) return () => { cancelled = true; };
    void getManualReviewBed(selectedManualBedId).then((bed) => {
      if (cancelled) return;
      setSelectedManualBed(bed);
    }).catch(() => {
      if (cancelled) return;
      setSelectedManualBed(null);
    });
    return () => { cancelled = true; };
  }, [selectedManualBedId]);

  const loadCompare = useCallback(async () => {
    if (!selectedSession || !selectedLiveRun) {
      setCompare(null);
      setCompareStatus("idle");
      setCompareError(null);
      setSelection(null);
      return;
    }
    setCompareStatus("loading");
    setCompareError(null);
    setSelection(null);
    try {
      const response = await getGoldReviewCompare({
        campaignId: selectedSession.campaign_id,
        sessionId: selectedSession.session_id,
        manifestPath: selectedLiveRun.manifest_path,
      });
      setCompare(response);
      setCompareStatus("ready");
    } catch (error) {
      setCompare(null);
      setCompareStatus("error");
      setCompareError(error instanceof LiveApiError || error instanceof Error ? error.message : "Failed to load comparison.");
    }
  }, [selectedLiveRun, selectedSession]);

  useEffect(() => {
    if (!sessionsLoaded) return;
    void loadCompare();
  }, [loadCompare, sessionsLoaded]);

  const handleCampaignSelect = (campaignId: string) => {
    setSelectedCampaignId(campaignId);
    syncReviewCampaignUrl(campaignId);
    const visibleSessions = sessionsForReviewCampaign(sessions, campaignId);
    const nextSession = visibleSessions.some((session) => session.session_id === selectedSessionId)
      ? visibleSessions.find((session) => session.session_id === selectedSessionId) ?? null
      : pickDefaultWorkbenchSession(visibleSessions, null, fallbackSessionId);
    setSelectedSessionId(nextSession?.session_id ?? "");
    setSelectedManifestPath(pickDefaultWorkbenchRun(nextSession?.available_runs ?? [])?.manifest_path ?? null);
    if (nextSession) syncGraphReviewUrl(nextSession.session_id, campaignId);
  };

  const handleSessionSelect = (sessionId: string) => {
    const session = campaignSessions.find((item) => item.session_id === sessionId) ?? null;
    setSelectedSessionId(sessionId);
    setSelectedManifestPath(pickDefaultWorkbenchRun(session?.available_runs ?? [])?.manifest_path ?? null);
    syncGraphReviewUrl(sessionId, selectedCampaignId);
  };

  if (!sessionsLoaded) {
    return <p className="plan-projection-empty">Loading graph review sessions…</p>;
  }

  if (!sessions.length && !sessionsError) {
    return (
      <p className="plan-projection-empty">
        No gold-review sessions are available yet. Add or generate gold fixtures before using the Workbench shell.
      </p>
    );
  }

  return (
    <div className="graph-review-workbench-root">
      <header className="graph-review-workbench-header">
        <div>
          <p className="plan-surface-kicker">Prose-first review tool</p>
          <h2>Graph Review Workbench</h2>
          <p className="graph-review-workbench-lede">
            Compare graph readings through recap prose first, with gold authoring state staged safely before backend write paths arrive.
          </p>
        </div>
      </header>

      <GraphReviewAuthoringWorkbenchModule />

      {sessionsError ? <p className="graph-review-error">{sessionsError}</p> : null}

      <GraphReviewLanePicker
        sessions={sessions}
        selectedCampaignId={selectedCampaignId}
        selectedSessionId={selectedSessionId}
        selectedManifestPath={selectedManifestPath}
        onCampaignSelect={handleCampaignSelect}
        onSessionSelect={handleSessionSelect}
        onManifestSelect={setSelectedManifestPath}
      />

      <GraphReviewLaneCards goldLane={goldLane} liveLane={liveLane} liveRun={selectedLiveRun} />

      <GraphReviewLiveProjectionPanel
        campaignId={selectedSession?.campaign_id ?? selectedCampaignId}
        sessionId={selectedSession?.session_id ?? selectedSessionId}
        liveRun={selectedLiveRun}
        selectedSession={selectedSession}
        compare={compare}
        compareStatus={compareStatus}
        goldLane={goldLane}
        liveLane={liveLane}
        manualBeds={manualBeds}
        manualBedsStatus={manualBedsStatus}
        manualBedsError={manualBedsError}
        selectedManualBed={selectedManualBed}
        selectedVariantLaneView={selectedVariantLaneView}
        selectedManualVariant={selectedManualBedId && selectedManualVariantName ? { bedId: selectedManualBedId, variantName: selectedManualVariantName } : null}
        onSelectManualBedId={setSelectedManualBedId}
        onSelectManualVariantName={setSelectedManualVariantName}
      />

      <GraphReviewMetricPanel
        compare={compare}
        compareStatus={compareStatus}
        compareError={compareError}
        selection={selection}
        onSelect={setSelection}
      />
    </div>
  );
}
