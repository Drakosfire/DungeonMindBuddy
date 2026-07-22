import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getGoldReviewCompare,
  getGoldReviewSessions,
  getGraphIngestRuns,
  getManualReviewBed,
  getManualReviewBeds,
  LiveApiError,
  postWorldGraphRecapProjection,
} from "../../api/liveApi";
import type { GoldReviewCompareResponse, ManualReviewBedDetail, ManualReviewBedSummary } from "../../api/types";
import type { GoldReviewSelection } from "../graphGoldReview/graphGoldReviewUtils";
import { requestedSessionFromLocation } from "../graphGoldReview/graphGoldReviewUtils";
import { createIngestSurfaceConfig } from "../config/ingestSurfaceConfig";
import { AdaptiveProjectionContainer } from "../projection/AdaptiveProjectionContainer";
import { ProjectionProvider } from "../projection/projectionContext";
import { buildPlanWorldGraphProjectionRequest } from "../reference/planGraphContextRequest";
import { buildRecapWorldGraphContext } from "../reference/recapWorldGraphContext";
import { PlanGraphReferenceResolverProvider } from "../reference/usePlanGraphReferenceResolver";
import type { PlanContextDescriptor } from "../types";
import { resolveInitialReviewCampaignId } from "../sessionCampaignContext";
import { GraphReviewWorkbenchHeader } from "./GraphReviewWorkbenchHeader";
import { GraphReviewWorkbenchHeaderWithActivity } from "./GraphReviewWorkbenchHeaderWithActivity";
import { GraphReviewSessionToolbar } from "./GraphReviewSessionToolbar";
import { GraphReviewLoadSurface } from "./GraphReviewLoadSurface";
import { GraphReviewLiveProjectionPanel } from "./GraphReviewLiveProjectionPanel";
import { GraphReviewLiveStateProvider } from "./GraphReviewLiveStateContext";
import { GraphReviewAuthorNodeHost } from "./GraphReviewAuthorNodeHost";
import {
  type WarmupStatus,
} from "./graphReviewActivity";
import {
  buildGraphReviewCatalog,
  catalogSessionToGoldLane,
  catalogSessionsForReviewCampaign,
  type GraphReviewCatalogSession,
  formatCompactAppliedLoadLabel,
  graphIngestRunToLane,
  GRAPH_REVIEW_RUNS_CHANGED_EVENT,
  pickDefaultCatalogSession,
  pickDefaultWorkbenchRun,
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
  sessions: GraphReviewCatalogSession[],
  campaignId: string,
  requestedSessionId: string | null,
  fallbackSessionId: string,
): AppliedSelection | null {
  const visibleSessions = catalogSessionsForReviewCampaign(sessions, campaignId);
  const session = pickDefaultCatalogSession(
    visibleSessions,
    requestedSessionId,
    fallbackSessionId,
  );
  if (!session) return null;
  const run = pickDefaultWorkbenchRun(
    session.availableRuns.filter((entry) => entry.preview_union_available),
  );
  return {
    campaignId,
    sessionId: session.sessionId,
    manifestPath: run?.manifest_path ?? null,
  };
}

async function loadGraphReviewCatalog(): Promise<GraphReviewCatalogSession[]> {
  const [runsResponse, goldResponse] = await Promise.all([
    getGraphIngestRuns({ requirePreviewUnionStore: true }),
    getGoldReviewSessions(),
  ]);
  return buildGraphReviewCatalog(runsResponse.runs, goldResponse.sessions);
}

function sessionNumberFromId(sessionId: string | null | undefined): number | null {
  if (!sessionId) return null;
  const match = sessionId.match(/^(?:session-)?(\d+)$/i);
  if (!match) return null;
  const session = Number.parseInt(match[1], 10);
  return Number.isFinite(session) && session > 0 ? session : null;
}

export function GraphReviewWorkbenchModule({ context }: GraphReviewWorkbenchModuleProps) {
  const fallbackSessionId = `session-${context.ingestSession}`;
  const requestedSessionId = requestedSessionFromLocation();

  const [catalogSessions, setCatalogSessions] = useState<GraphReviewCatalogSession[]>([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [catalogRefreshToken, setCatalogRefreshToken] = useState(0);
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
  const [warmupStatus, setWarmupStatus] = useState<WarmupStatus>("idle");
  const appliedCampaignSessions = useMemo(
    () =>
      appliedSelection
        ? catalogSessionsForReviewCampaign(catalogSessions, appliedSelection.campaignId)
        : [],
    [appliedSelection, catalogSessions],
  );

  const appliedSession = useMemo(
    () =>
      appliedSelection
        ? appliedCampaignSessions.find(
            (session) => session.sessionId === appliedSelection.sessionId,
          ) ?? null
        : null,
    [appliedCampaignSessions, appliedSelection],
  );

  const appliedLiveRun = useMemo(() => {
    if (!appliedSession || !appliedSelection?.manifestPath) return null;
    return (
      appliedSession.availableRuns.find(
        (run) => run.manifest_path === appliedSelection.manifestPath,
      ) ?? null
    );
  }, [appliedSelection, appliedSession]);

  const draftCampaignSessions = useMemo(
    () => catalogSessionsForReviewCampaign(catalogSessions, draftCampaignId),
    [draftCampaignId, catalogSessions],
  );

  const draftSession = useMemo(
    () =>
      draftCampaignSessions.find((session) => session.sessionId === draftSessionId) ??
      null,
    [draftCampaignSessions, draftSessionId],
  );

  const draftLiveRun = useMemo(() => {
    if (!draftSession) return null;
    return (
      draftSession.availableRuns.find(
        (run) => run.manifest_path === draftManifestPath,
      ) ?? null
    );
  }, [draftManifestPath, draftSession]);

  const goldLane = useMemo(
    () => (appliedSession ? catalogSessionToGoldLane(appliedSession) : null),
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
    () => formatCompactAppliedLoadLabel(appliedSession),
    [appliedSession],
  );

  const refreshCatalog = useCallback(async () => {
    setSessionsLoaded(false);
    setSessionsError(null);
    try {
      const catalog = await loadGraphReviewCatalog();
      const initialCampaignId = resolveInitialReviewCampaignId(context.campaignId);
      setCatalogSessions(catalog);
      const defaultDraft = buildDefaultDraft(
        catalog,
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
    } catch (error) {
      setCatalogSessions([]);
      setSessionsError(
        error instanceof Error ? error.message : "Failed to load graph review sessions.",
      );
      setSessionsLoaded(true);
    }
  }, [context.campaignId, fallbackSessionId, requestedSessionId]);

  useEffect(() => {
    let cancelled = false;
    void refreshCatalog().then(() => {
      if (cancelled) return;
    });
    return () => {
      cancelled = true;
    };
  }, [refreshCatalog, catalogRefreshToken]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onRunsChanged = () => setCatalogRefreshToken((value) => value + 1);
    window.addEventListener(GRAPH_REVIEW_RUNS_CHANGED_EVENT, onRunsChanged);
    return () => window.removeEventListener(GRAPH_REVIEW_RUNS_CHANGED_EVENT, onRunsChanged);
  }, []);

  // Background warm-up: prefetch draft-session recap so Load / remounts hit cache.
  useEffect(() => {
    if (!sessionsLoaded || !draftCampaignId || !draftSessionId) {
      setWarmupStatus("idle");
      return;
    }
    const worldContext = buildRecapWorldGraphContext(draftCampaignId, draftSessionId);
    if (!worldContext) {
      setWarmupStatus("idle");
      return;
    }
    let cancelled = false;
    setWarmupStatus("warming");
    void postWorldGraphRecapProjection(buildPlanWorldGraphProjectionRequest(worldContext))
      .then(() => {
        if (!cancelled) setWarmupStatus("ready");
      })
      .catch(() => {
        // Warm-up is best-effort; Load still fetches on demand.
        if (!cancelled) setWarmupStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionsLoaded, draftCampaignId, draftSessionId]);

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
    if (!appliedSession.hasGold) {
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
        campaignId: appliedSession.campaignId,
        sessionId: appliedSession.sessionId,
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
        catalogSessions,
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
    const visibleSessions = catalogSessionsForReviewCampaign(catalogSessions, campaignId);
    const nextSession = pickDefaultCatalogSession(
      visibleSessions,
      null,
      fallbackSessionId,
    );
    setDraftCampaignId(campaignId);
    setDraftSessionId(nextSession?.sessionId ?? "");
    setDraftManifestPath(
      pickDefaultWorkbenchRun(
        (nextSession?.availableRuns ?? []).filter((run) => run.preview_union_available),
      )?.manifest_path ?? null,
    );
  };

  const handleDraftSessionSelect = (sessionId: string) => {
    const session =
      draftCampaignSessions.find((item) => item.sessionId === sessionId) ?? null;
    setDraftSessionId(sessionId);
    setDraftManifestPath(
      pickDefaultWorkbenchRun(
        (session?.availableRuns ?? []).filter((run) => run.preview_union_available),
      )?.manifest_path ?? null,
    );
  };

  const handleApplyLoad = () => {
    if (!draftSession || !draftLiveRun) return;
    const nextApplied: AppliedSelection = {
      campaignId: draftCampaignId,
      sessionId: draftSession.sessionId,
      manifestPath: draftLiveRun.manifest_path,
    };
    setAppliedSelection(nextApplied);
    syncGraphReviewUrl(nextApplied.sessionId, nextApplied.campaignId);
    setLoadDialogOpen(false);
  };

  const reviewCampaignId =
    appliedSession?.campaignId ?? draftCampaignId ?? context.campaignId;
  const reviewSessionId =
    appliedSession?.sessionId || draftSessionId || fallbackSessionId;
  const toolboxConfig = useMemo(() => {
    const sessionNumber = sessionNumberFromId(reviewSessionId) ?? context.ingestSession;
    return createIngestSurfaceConfig({
      ...context,
      campaignId: reviewCampaignId,
      ingestSession: sessionNumber,
    });
  }, [context, reviewCampaignId, reviewSessionId]);

  if (!sessionsLoaded) {
    return (
      <div className="graph-review-workbench-root">
        <GraphReviewWorkbenchHeader
          loaded={false}
          sessionLabel={null}
          onOpenLoad={() => undefined}
          activity={{
            phase: "catalog",
            message: "Loading sessions…",
            busy: true,
          }}
        />
        <p className="plan-projection-empty">Loading graph review sessions…</p>
      </div>
    );
  }

  const hasAppliedLoad = Boolean(appliedSelection && appliedSession && appliedLiveRun);
  const hasCatalogSessions = catalogSessions.length > 0 || Boolean(sessionsError);
  // Keep live-state (and the Tools drawer) mounted even before a session is loaded so
  // Ingest Recap remains reachable from the empty /ingest landing state.

  return (
    <ProjectionProvider config={toolboxConfig}>
      <PlanGraphReferenceResolverProvider
        sessionDescriptor={hasAppliedLoad ? toolboxConfig.sessionDescriptor : null}
        scopeMode="world"
      >
      <GraphReviewLiveStateProvider
        campaignId={reviewCampaignId}
        sessionId={reviewSessionId}
        liveRun={hasAppliedLoad ? appliedLiveRun : null}
        hasGold={hasAppliedLoad ? Boolean(appliedSession?.hasGold) : false}
        compare={hasAppliedLoad ? compare : null}
        compareStatus={hasAppliedLoad ? compareStatus : "idle"}
        compareError={hasAppliedLoad ? compareError : null}
        goldLane={hasAppliedLoad ? goldLane : null}
        liveLane={hasAppliedLoad ? liveLane : null}
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
        <div className="graph-review-workbench-root">
          <GraphReviewWorkbenchHeaderWithActivity
            loaded={hasAppliedLoad}
            sessionLabel={loadBarSummary}
            onOpenLoad={openLoadDialog}
            sessionsLoaded={sessionsLoaded}
            hasAppliedLoad={hasAppliedLoad}
            warmupStatus={warmupStatus}
            draftCampaignId={draftCampaignId}
            draftSessionId={draftSessionId}
          />

          {sessionsError ? <p className="graph-review-error">{sessionsError}</p> : null}

          <GraphReviewAuthorNodeHost
            onRequestLoad={openLoadDialog}
            chrome={
              !hasCatalogSessions ? (
                <p className="plan-projection-empty">
                  No preview-ready graph runs are available yet. Use Ingest Recap in the toolbox to
                  paste a recap, run extraction, and materialize a preview graph.
                </p>
              ) : !hasAppliedLoad ? (
                <p className="plan-projection-empty graph-review-load-empty">
                  Load an ingested session to review extracted objects in recap prose.
                </p>
              ) : (
                <GraphReviewSessionToolbar />
              )
            }
            projection={hasAppliedLoad ? <GraphReviewLiveProjectionPanel /> : null}
          />

          <AdaptiveProjectionContainer config={toolboxConfig} />

          <GraphReviewLoadSurface
            open={loadDialogOpen}
            sessions={catalogSessions}
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
      </GraphReviewLiveStateProvider>
      </PlanGraphReferenceResolverProvider>
    </ProjectionProvider>
  );
}
