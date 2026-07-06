import { useCallback, useEffect, useMemo, useState } from "react";

import { getGoldReviewCompare, getGoldReviewSessions, getManualReviewBed, getManualReviewBeds, LiveApiError } from "../../api/liveApi";
import type { GoldReviewCompareResponse, GoldReviewSessionSummary, ManualReviewBedDetail, ManualReviewBedSummary } from "../../api/types";
import type { GoldReviewSelection } from "../graphGoldReview/graphGoldReviewUtils";
import { requestedSessionFromLocation } from "../graphGoldReview/graphGoldReviewUtils";
import { createIngestSurfaceConfig } from "../config/ingestSurfaceConfig";
import { AdaptiveProjectionContainer } from "../projection/AdaptiveProjectionContainer";
import { ProjectionProvider } from "../projection/projectionContext";
import type { PlanContextDescriptor } from "../types";
import {
  goldReviewSessionLabel,
  resolveInitialReviewCampaignId,
  sessionsForReviewCampaign,
} from "../sessionCampaignContext";
import { GraphReviewLoadBar } from "./GraphReviewLoadBar";
import { GraphReviewLoadSurface } from "./GraphReviewLoadSurface";
import { GraphReviewLiveProjectionPanel } from "./GraphReviewLiveProjectionPanel";
import { GraphReviewLiveStateProvider } from "./GraphReviewLiveStateContext";
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

interface AppliedSelection {
  campaignId: string;
  sessionId: string;
  manifestPath: string | null;
}

function syncGraphReviewUrl(sessionId: string, campaignId: string): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  params.set("session", sessionId);
  params.set("campaign", campaignId);
  const path = window.location.pathname.replace(/\/+$/, "") || "/plan";
  const surfacePath = path === "/ingest" ? "/ingest" : "/plan";
  window.history.replaceState({}, "", `${surfacePath}?${params.toString()}`);
}

function buildDefaultDraft(
  sessions: GoldReviewSessionSummary[],
  campaignId: string,
  requestedSessionId: string | null,
  fallbackSessionId: string,
): AppliedSelection | null {
  const visibleSessions = sessionsForReviewCampaign(sessions, campaignId);
  const session = pickDefaultWorkbenchSession(
    visibleSessions,
    requestedSessionId,
    fallbackSessionId,
  );
  if (!session) return null;
  const run = pickDefaultWorkbenchRun(
    session.available_runs.filter((entry) => entry.preview_union_available),
  );
  return {
    campaignId,
    sessionId: session.session_id,
    manifestPath: run?.manifest_path ?? null,
  };
}

function formatAppliedLoadLabel(
  session: GoldReviewSessionSummary | null,
  liveRun: GoldReviewSessionSummary["available_runs"][number] | null,
): string | null {
  if (!session) return null;
  const sessionLabel = goldReviewSessionLabel(session);
  const runLabel = liveRun?.run_label?.trim() || liveRun?.run_id || null;
  return runLabel ? `${sessionLabel} · ${runLabel}` : sessionLabel;
}

export function GraphReviewWorkbenchModule({ context }: GraphReviewWorkbenchModuleProps) {
  const fallbackSessionId = `session-${context.ingestSession}`;
  const requestedSessionId = requestedSessionFromLocation();
  const toolboxConfig = useMemo(() => createIngestSurfaceConfig(context), [context]);

  const [sessions, setSessions] = useState<GoldReviewSessionSummary[]>([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [appliedSelection, setAppliedSelection] = useState<AppliedSelection | null>(null);
  const [draftCampaignId, setDraftCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
  const [draftSessionId, setDraftSessionId] = useState("");
  const [draftManifestPath, setDraftManifestPath] = useState<string | null>(null);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
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

  const appliedCampaignSessions = useMemo(
    () =>
      appliedSelection
        ? sessionsForReviewCampaign(sessions, appliedSelection.campaignId)
        : [],
    [appliedSelection, sessions],
  );

  const appliedSession = useMemo(
    () =>
      appliedSelection
        ? appliedCampaignSessions.find(
            (session) => session.session_id === appliedSelection.sessionId,
          ) ?? null
        : null,
    [appliedCampaignSessions, appliedSelection],
  );

  const appliedLiveRun = useMemo(() => {
    if (!appliedSession || !appliedSelection?.manifestPath) return null;
    return (
      appliedSession.available_runs.find(
        (run) => run.manifest_path === appliedSelection.manifestPath,
      ) ?? null
    );
  }, [appliedSelection, appliedSession]);

  const draftCampaignSessions = useMemo(
    () => sessionsForReviewCampaign(sessions, draftCampaignId),
    [draftCampaignId, sessions],
  );

  const draftSession = useMemo(
    () =>
      draftCampaignSessions.find((session) => session.session_id === draftSessionId) ??
      null,
    [draftCampaignSessions, draftSessionId],
  );

  const draftLiveRun = useMemo(() => {
    if (!draftSession) return null;
    return (
      draftSession.available_runs.find(
        (run) => run.manifest_path === draftManifestPath,
      ) ?? null
    );
  }, [draftManifestPath, draftSession]);

  const goldLane = useMemo(
    () => (appliedSession ? goldSessionToLane(appliedSession) : null),
    [appliedSession],
  );
  const liveLane = useMemo(
    () => (appliedLiveRun ? graphIngestRunToLane(appliedLiveRun) : null),
    [appliedLiveRun],
  );
  const selectedVariantLaneView = useMemo(
    () =>
      selectedManualBed && selectedManualVariantName
        ? manualVariantToLaneView({
            bed: selectedManualBed,
            variantName: selectedManualVariantName,
          })
        : null,
    [selectedManualBed, selectedManualVariantName],
  );

  const loadBarSummary = useMemo(
    () => formatAppliedLoadLabel(appliedSession, appliedLiveRun),
    [appliedLiveRun, appliedSession],
  );

  useEffect(() => {
    let cancelled = false;
    setSessionsLoaded(false);
    setSessionsError(null);
    void getGoldReviewSessions()
      .then((response) => {
        if (cancelled) return;
        const initialCampaignId = resolveInitialReviewCampaignId(context.campaignId);
        setSessions(response.sessions);
        const defaultDraft = buildDefaultDraft(
          response.sessions,
          initialCampaignId,
          requestedSessionId,
          fallbackSessionId,
        );
        if (defaultDraft) {
          setDraftCampaignId(defaultDraft.campaignId);
          setDraftSessionId(defaultDraft.sessionId);
          setDraftManifestPath(defaultDraft.manifestPath);
        }
        if (requestedSessionId && defaultDraft) {
          setAppliedSelection(defaultDraft);
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
    void getManualReviewBeds()
      .then((response) => {
        if (cancelled) return;
        setManualBeds(response.beds);
        setManualBedsStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setManualBeds([]);
        setManualBedsStatus("error");
        setManualBedsError(error instanceof Error ? error.message : "Failed to load manual review beds.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setSelectedManualBed(null);
    setSelectedManualVariantName(null);
    if (!selectedManualBedId) return () => { cancelled = true; };
    void getManualReviewBed(selectedManualBedId)
      .then((bed) => {
        if (cancelled) return;
        setSelectedManualBed(bed);
      })
      .catch(() => {
        if (cancelled) return;
        setSelectedManualBed(null);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedManualBedId]);

  const loadCompare = useCallback(async () => {
    if (!appliedSession || !appliedLiveRun) {
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
        campaignId: appliedSession.campaign_id,
        sessionId: appliedSession.session_id,
        manifestPath: appliedLiveRun.manifest_path,
      });
      setCompare(response);
      setCompareStatus("ready");
    } catch (error) {
      setCompare(null);
      setCompareStatus("error");
      setCompareError(
        error instanceof LiveApiError || error instanceof Error
          ? error.message
          : "Failed to load comparison.",
      );
    }
  }, [appliedLiveRun, appliedSession]);

  useEffect(() => {
    if (!sessionsLoaded) return;
    void loadCompare();
  }, [loadCompare, sessionsLoaded]);

  const openLoadDialog = () => {
    if (appliedSelection) {
      setDraftCampaignId(appliedSelection.campaignId);
      setDraftSessionId(appliedSelection.sessionId);
      setDraftManifestPath(appliedSelection.manifestPath);
    } else {
      const defaultDraft = buildDefaultDraft(
        sessions,
        resolveInitialReviewCampaignId(context.campaignId),
        requestedSessionId,
        fallbackSessionId,
      );
      if (defaultDraft) {
        setDraftCampaignId(defaultDraft.campaignId);
        setDraftSessionId(defaultDraft.sessionId);
        setDraftManifestPath(defaultDraft.manifestPath);
      }
    }
    setLoadDialogOpen(true);
  };

  const handleDraftCampaignSelect = (campaignId: string) => {
    const visibleSessions = sessionsForReviewCampaign(sessions, campaignId);
    const nextSession = pickDefaultWorkbenchSession(
      visibleSessions,
      null,
      fallbackSessionId,
    );
    setDraftCampaignId(campaignId);
    setDraftSessionId(nextSession?.session_id ?? "");
    setDraftManifestPath(
      pickDefaultWorkbenchRun(
        (nextSession?.available_runs ?? []).filter((run) => run.preview_union_available),
      )?.manifest_path ?? null,
    );
  };

  const handleDraftSessionSelect = (sessionId: string) => {
    const session =
      draftCampaignSessions.find((item) => item.session_id === sessionId) ?? null;
    setDraftSessionId(sessionId);
    setDraftManifestPath(
      pickDefaultWorkbenchRun(
        (session?.available_runs ?? []).filter((run) => run.preview_union_available),
      )?.manifest_path ?? null,
    );
  };

  const handleApplyLoad = () => {
    if (!draftSession || !draftLiveRun) return;
    const nextApplied: AppliedSelection = {
      campaignId: draftCampaignId,
      sessionId: draftSession.session_id,
      manifestPath: draftLiveRun.manifest_path,
    };
    setAppliedSelection(nextApplied);
    syncGraphReviewUrl(nextApplied.sessionId, nextApplied.campaignId);
    setLoadDialogOpen(false);
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

  const hasAppliedLoad = Boolean(appliedSelection && appliedSession && appliedLiveRun);

  return (
    <ProjectionProvider config={toolboxConfig}>
      <div className="graph-review-workbench-root">
        <header className="graph-review-workbench-header">
          <div>
            <p className="plan-surface-kicker">Prose-first review tool</p>
            <h2>Graph Review Workbench</h2>
          </div>
        </header>

        {sessionsError ? <p className="graph-review-error">{sessionsError}</p> : null}

        <GraphReviewLoadBar
          loaded={hasAppliedLoad}
          summaryLabel={loadBarSummary}
          onOpenLoad={openLoadDialog}
        />

        {!hasAppliedLoad ? (
          <p className="plan-projection-empty graph-review-load-empty">
            Load a session to compare gold and ingested recap prose side by side.
          </p>
        ) : (
          <GraphReviewLiveStateProvider
            campaignId={appliedSession!.campaign_id}
            sessionId={appliedSession!.session_id}
            liveRun={appliedLiveRun}
            selectedSession={appliedSession}
            compare={compare}
            compareStatus={compareStatus}
            compareError={compareError}
            goldLane={goldLane}
            liveLane={liveLane}
            manualBeds={manualBeds}
            manualBedsStatus={manualBedsStatus}
            manualBedsError={manualBedsError}
            selectedManualBed={selectedManualBed}
            selectedVariantLaneView={selectedVariantLaneView}
            selectedManualVariant={
              selectedManualBedId && selectedManualVariantName
                ? { bedId: selectedManualBedId, variantName: selectedManualVariantName }
                : null
            }
            onSelectManualBedId={setSelectedManualBedId}
            onSelectManualVariantName={setSelectedManualVariantName}
            selection={selection}
            onSelectSelection={setSelection}
          >
            <GraphReviewLiveProjectionPanel />
            <AdaptiveProjectionContainer config={toolboxConfig} />
          </GraphReviewLiveStateProvider>
        )}

        <GraphReviewLoadSurface
          open={loadDialogOpen}
          sessions={sessions}
          draftCampaignId={draftCampaignId}
          draftSessionId={draftSessionId}
          draftManifestPath={draftManifestPath}
          draftSession={draftSession}
          draftLiveRun={draftLiveRun}
          onClose={() => setLoadDialogOpen(false)}
          onLoad={handleApplyLoad}
          onCampaignSelect={handleDraftCampaignSelect}
          onSessionSelect={handleDraftSessionSelect}
          onManifestSelect={setDraftManifestPath}
        />
      </div>
    </ProjectionProvider>
  );
}
