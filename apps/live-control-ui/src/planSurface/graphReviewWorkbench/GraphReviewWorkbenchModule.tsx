import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import {
  getExtractionRun,
  getExtractionRunStatus,
  getGoldReviewCompare,
  getGoldReviewSessions,
  getGraphIngestRuns,
  getManualReviewBed,
  getManualReviewBeds,
  LiveApiError,
  postWorldGraphRecapProjection,
} from "../../api/liveApi";
import type {
  ExtractionRunRecord,
  ExtractionRunStatusResponse,
  GoldReviewCompareResponse,
  ManualReviewBedDetail,
  ManualReviewBedSummary,
} from "../../api/types";
import {
  ExtractPromoteApiError,
  getExactRunReviewPackage,
  prepareExtractPromote,
} from "../../api/extractPromoteApi";
import type { ExactRunReviewPackage, ExtractPromotePrepareResponse } from "../../api/types";
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
import { GraphReviewExactRunProjection } from "./GraphReviewExactRunProjection";
import { GraphReviewExtractPromoteSheet } from "./GraphReviewExtractPromoteSheet";
import {
  type GraphReviewAppliedSelection,
  resolvePersistedAppliedSelection,
  writeAppliedSelectionToStorage,
  writeAppliedSelectionToUrl,
} from "./graphReviewAppliedSelection";
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
import {
  assertExactRunHandoff,
  clearExactRunHandoffFromLocation,
  parseGraphReviewRunHandoff,
} from "./graphReviewRunSelection";
import type {
  GraphReviewExactRunHandoff,
  GraphReviewExactRunLineage,
} from "./graphReviewRunSelection";

interface GraphReviewWorkbenchModuleProps {
  context: PlanContextDescriptor;
  onSurfaceChromeChange?: (chrome: ReactNode) => void;
}

function buildDefaultDraft(
  sessions: GraphReviewCatalogSession[],
  campaignId: string,
  requestedSessionId: string | null,
  fallbackSessionId: string,
): GraphReviewAppliedSelection | null {
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

function resolveSelectionAgainstCatalog(
  selection: GraphReviewAppliedSelection | null,
  sessions: GraphReviewCatalogSession[],
): GraphReviewAppliedSelection | null {
  if (!selection) return null;
  const campaignSessions = catalogSessionsForReviewCampaign(sessions, selection.campaignId);
  const session =
    campaignSessions.find((entry) => entry.sessionId === selection.sessionId) ?? null;
  if (!session) return null;
  const previewRuns = session.availableRuns.filter((run) => run.preview_union_available);
  if (selection.manifestPath) {
    const exact =
      previewRuns.find((run) => run.manifest_path === selection.manifestPath) ??
      session.availableRuns.find((run) => run.manifest_path === selection.manifestPath);
    if (exact) {
      return {
        campaignId: selection.campaignId,
        sessionId: selection.sessionId,
        manifestPath: exact.manifest_path,
      };
    }
  }
  const fallbackRun = pickDefaultWorkbenchRun(previewRuns);
  if (!fallbackRun) return null;
  return {
    campaignId: selection.campaignId,
    sessionId: selection.sessionId,
    manifestPath: fallbackRun.manifest_path,
  };
}

function persistAppliedSelection(selection: GraphReviewAppliedSelection): void {
  writeAppliedSelectionToUrl(selection);
  writeAppliedSelectionToStorage(selection);
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

function GraphReviewWorkbenchLoadingChrome({
  onSurfaceChromeChange,
}: {
  onSurfaceChromeChange?: (chrome: ReactNode) => void;
}) {
  const onSurfaceChromeChangeRef = useRef(onSurfaceChromeChange);
  onSurfaceChromeChangeRef.current = onSurfaceChromeChange;

  useEffect(() => {
    const publish = onSurfaceChromeChangeRef.current;
    if (!publish) return;
    publish(
      <GraphReviewWorkbenchHeader
        loaded={false}
        sessionLabel={null}
        onOpenLoad={() => undefined}
        activity={{
          phase: "catalog",
          message: "Loading sessions…",
          busy: true,
        }}
      />,
    );
    return () => {
      onSurfaceChromeChangeRef.current?.(null);
    };
  }, []);

  return (
    <div className="graph-review-workbench-root">
      {!onSurfaceChromeChange ? (
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
      ) : null}
      <p className="plan-projection-empty">Loading graph review sessions…</p>
    </div>
  );
}

export function GraphReviewWorkbenchModule({
  context,
  onSurfaceChromeChange,
}: GraphReviewWorkbenchModuleProps) {
  const fallbackSessionId = `session-${context.ingestSession}`;
  const requestedSessionId = requestedSessionFromLocation();
  const [exactHandoff, setExactHandoff] = useState<GraphReviewExactRunHandoff | null>(() =>
    parseGraphReviewRunHandoff(
      typeof window !== "undefined" ? window.location.search : "",
    ),
  );
  const exactHandoffErrors = useMemo(
    () => (exactHandoff ? assertExactRunHandoff(exactHandoff) : []),
    [exactHandoff],
  );

  const [catalogSessions, setCatalogSessions] = useState<GraphReviewCatalogSession[]>([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [catalogRefreshToken, setCatalogRefreshToken] = useState(0);
  const [appliedSelection, setAppliedSelection] = useState<GraphReviewAppliedSelection | null>(
    null,
  );
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
  const [exactRun, setExactRun] = useState<ExtractionRunRecord | null>(null);
  const [exactLineage, setExactLineage] = useState<GraphReviewExactRunLineage | null>(null);
  const [exactRunStatus, setExactRunStatus] = useState<"idle" | "loading" | "ready" | "error">(
    exactHandoff ? "loading" : "idle",
  );
  const [exactRunError, setExactRunError] = useState<string | null>(null);
  const [exactPrepared, setExactPrepared] = useState<ExtractPromotePrepareResponse | null>(null);
  const [exactPreparing, setExactPreparing] = useState(false);
  const [exactPrepareError, setExactPrepareError] = useState<string | null>(null);
  const [exactConfirmInFlight, setExactConfirmInFlight] = useState(false);
  const [exactReview, setExactReview] = useState<ExactRunReviewPackage | null>(null);
  const [exactReviewStatus, setExactReviewStatus] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const [exactReviewError, setExactReviewError] = useState<string | null>(null);
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
    // Keep the current projection mounted while refreshing the catalog so a
    // Load → URL update → dep change cycle cannot flash the empty state.
    setSessionsError(null);
    try {
      const catalog = await loadGraphReviewCatalog();
      const initialCampaignId = resolveInitialReviewCampaignId(context.campaignId);
      setCatalogSessions(catalog);

      const persistedHint = resolvePersistedAppliedSelection();
      setAppliedSelection((current) => {
        const restored = resolveSelectionAgainstCatalog(
          persistedHint ?? current,
          catalog,
        );
        if (restored) {
          return restored;
        }
        if (!requestedSessionId) {
          return current;
        }
        return (
          buildDefaultDraft(
            catalog,
            initialCampaignId,
            requestedSessionId,
            fallbackSessionId,
          ) ?? current
        );
      });

      const draftSource =
        resolveSelectionAgainstCatalog(persistedHint, catalog) ??
        buildDefaultDraft(
          catalog,
          initialCampaignId,
          requestedSessionId,
          fallbackSessionId,
        );
      if (draftSource) {
        setDraftCampaignId(draftSource.campaignId);
        setDraftSessionId(draftSource.sessionId);
        setDraftManifestPath(draftSource.manifestPath);
      }

      const toPersist =
        resolveSelectionAgainstCatalog(persistedHint, catalog) ??
        (requestedSessionId
          ? buildDefaultDraft(
              catalog,
              initialCampaignId,
              requestedSessionId,
              fallbackSessionId,
            )
          : null);
      if (toPersist) {
        persistAppliedSelection(toPersist);
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
    // Re-fetch only on mount and when ingest emits a runs-changed signal.
    // Do not depend on refreshCatalog identity — that used to remount the
    // projection whenever Load updated the session query param.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional
  }, [catalogRefreshToken]);

  useEffect(() => {
    if (!exactHandoff || exactHandoffErrors.length > 0) {
      if (exactHandoffErrors.length > 0) {
        setExactRun(null);
        setExactRunStatus("error");
        setExactRunError(exactHandoffErrors.join("; "));
      }
      return;
    }
    let cancelled = false;
    setExactRunStatus("loading");
    setExactRunError(null);
    setExactLineage(null);
    const fail = (message: string) => {
      if (cancelled) return;
      setExactRun(null);
      setExactLineage(null);
      setExactRunStatus("error");
      setExactRunError(message);
      setExactReview(null);
      setExactReviewStatus("idle");
      setExactReviewError(null);
    };
    void (async () => {
      let run: ExtractionRunRecord;
      try {
        run = await getExtractionRun(exactHandoff.extractionRunId);
      } catch (error) {
        fail(
          error instanceof LiveApiError || error instanceof Error
            ? error.message
            : "Failed to load exact extraction run.",
        );
        return;
      }
      if (cancelled) return;
      if (run.run_id !== exactHandoff.extractionRunId) {
        fail("handoff extractionRunId does not match the loaded run");
        return;
      }
      if (
        exactHandoff.sourceArtifactId &&
        run.source_artifact_id !== exactHandoff.sourceArtifactId
      ) {
        fail("handoff sourceArtifactId does not match the exact run");
        return;
      }

      // A handoff that claims workspace lineage must be confirmed by the
      // server's own SourceArtifact resolution. URL-supplied document identity
      // is never displayed or trusted on its own.
      let lineage: GraphReviewExactRunLineage | null = null;
      if (exactHandoff.documentId !== null && exactHandoff.revision !== null) {
        let context: ExtractionRunStatusResponse;
        try {
          context = await getExtractionRunStatus(exactHandoff.extractionRunId);
        } catch (error) {
          fail(
            `handoff document lineage could not be verified: ${
              error instanceof LiveApiError || error instanceof Error
                ? error.message
                : "unknown error"
            }`,
          );
          return;
        }
        if (cancelled) return;
        if (
          context.run.run_id !== exactHandoff.extractionRunId ||
          context.source_artifact_id !== run.source_artifact_id ||
          context.document_id !== exactHandoff.documentId ||
          context.document_revision !== exactHandoff.revision
        ) {
          fail("handoff document lineage does not match the server-resolved run");
          return;
        }
        lineage = {
          documentId: context.document_id,
          revision: context.document_revision,
        };
      }
      if (cancelled) return;
      setExactRun(run);
      setExactLineage(lineage);
      setExactRunStatus("ready");
      setExactReviewStatus("loading");
      setExactReviewError(null);
      setExactReview(null);
      try {
        const packageResponse = await getExactRunReviewPackage(run.run_id);
        if (cancelled) return;
        const packageCampaign = (packageResponse.campaignId ?? "").trim();
        const runCampaign = (run.campaign_id ?? "").trim();
        const packageSession = (packageResponse.sessionId ?? "").trim();
        const runSession = (run.session_id ?? "").trim();
        if (
          packageResponse.runId !== run.run_id ||
          packageResponse.sourceArtifactId !== run.source_artifact_id ||
          packageResponse.sourceDomain !== run.source_domain ||
          packageCampaign !== runCampaign ||
          packageSession !== runSession
        ) {
          setExactReview(null);
          setExactReviewStatus("error");
          setExactReviewError(
            "exact-run review package identity does not match the loaded ExtractionRun",
          );
          return;
        }
        setExactReview(packageResponse);
        setExactReviewStatus("ready");
      } catch (error) {
        if (cancelled) return;
        // Interim dogfood inspect: full error body in the browser console until
        // inspectable review-package lands (Backlog: false_anchor / run_not_promotable).
        if (error instanceof ExtractPromoteApiError) {
          console.error("[graph-review] exact-run review-package failed", {
            runId: run.run_id,
            status: error.status,
            code: error.code,
            message: error.message,
            diagnostics: error.body?.diagnostics ?? null,
            body: error.body,
          });
        } else {
          console.error("[graph-review] exact-run review-package failed", {
            runId: run.run_id,
            error,
          });
        }
        setExactReview(null);
        setExactReviewStatus("error");
        setExactReviewError(
          error instanceof ExtractPromoteApiError || error instanceof Error
            ? error.message
            : "Failed to load exact-run source evidence.",
        );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [exactHandoff, exactHandoffErrors]);

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

  const openLoadDialog = useCallback(() => {
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
  }, [
    appliedSelection,
    catalogSessions,
    context.campaignId,
    fallbackSessionId,
    requestedSessionId,
  ]);

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
    const nextApplied: GraphReviewAppliedSelection = {
      campaignId: draftCampaignId,
      sessionId: draftSession.sessionId,
      manifestPath: draftLiveRun.manifest_path,
    };
    // Loading a recap supersedes exact-run mode: clear handoff identity from
    // state and the URL so the module renders the selected recap immediately.
    clearExactRunHandoffFromLocation();
    setExactHandoff(null);
    setExactRun(null);
    setExactLineage(null);
    setExactRunStatus("idle");
    setExactRunError(null);
    setExactReview(null);
    setExactReviewStatus("idle");
    setExactReviewError(null);
    setExactPrepared(null);
    setExactPrepareError(null);
    setAppliedSelection(nextApplied);
    persistAppliedSelection(nextApplied);
    setLoadDialogOpen(false);
  };

  const exactRunReviewable = exactRun?.status === "reviewable";
  const exactRunPromotable =
    exactRunReviewable
    && exactReview?.promotable !== false
    && (exactRun?.source_domain ?? "").trim() !== "worldbuilding";
  const exactRunNonPromotableReason =
    exactReview?.promotableReason?.trim()
    || (
      (exactRun?.source_domain ?? "").trim() === "worldbuilding"
        ? "Worldbuilding ExtractionRuns are inspect-only until an approved authority-elevation contract lands."
        : null
    );
  const exactRunSummary =
    exactHandoff && exactRun
      ? {
          extractionRunId: exactRun.run_id,
          sourceDomain: exactRun.source_domain,
          status: exactRun.status,
          sourceArtifactId: exactRun.source_artifact_id,
          profileId: exactRun.profile_id ?? null,
          campaignId: exactRun.campaign_id ?? null,
          sessionId: exactRun.session_id ?? null,
          documentId: exactLineage?.documentId ?? null,
          revision: exactLineage?.revision ?? null,
          reviewable: exactRunReviewable,
          promotable: exactRunPromotable,
        }
      : null;

  const onPrepareExactRun = useCallback(async () => {
    if (!exactHandoff || !exactRunPromotable || exactPreparing || exactConfirmInFlight) return;
    setExactPreparing(true);
    setExactPrepareError(null);
    try {
      const response = await prepareExtractPromote({ runId: exactHandoff.extractionRunId });
      setExactPrepared(response);
    } catch (error) {
      setExactPrepared(null);
      if (error instanceof ExtractPromoteApiError) {
        const diagnosticTail = (error.body?.diagnostics ?? [])
          .map((item) => item.message)
          .filter((message): message is string => Boolean(message?.trim()))
          .join(" · ");
        setExactPrepareError(
          diagnosticTail ? `${error.message} (${diagnosticTail})` : error.message,
        );
        console.error("[graph-review] exact-run prepare failed", {
          runId: exactHandoff.extractionRunId,
          status: error.status,
          code: error.code,
          message: error.message,
          diagnostics: error.body?.diagnostics ?? null,
          body: error.body,
        });
      } else if (error instanceof Error) {
        setExactPrepareError(error.message);
        console.error("[graph-review] exact-run prepare failed", error);
      } else {
        setExactPrepareError("Failed to prepare promotion for exact run.");
      }
    } finally {
      setExactPreparing(false);
    }
  }, [exactConfirmInFlight, exactHandoff, exactPreparing, exactRunPromotable]);

  if (!sessionsLoaded && !exactHandoff) {
    return (
      <GraphReviewWorkbenchLoadingChrome
        onSurfaceChromeChange={onSurfaceChromeChange}
      />
    );
  }

  const hasAppliedLoad = Boolean(appliedSelection && appliedSession && appliedLiveRun);
  const hasExactRunLoad = Boolean(exactHandoff && exactRunStatus === "ready" && exactRun);
  const hasCatalogSessions = catalogSessions.length > 0 || Boolean(sessionsError);
  // Keep live-state (and the Tools drawer) mounted even before a session is loaded so
  // Ingest Recap remains reachable from the empty /ingest landing state.
  // Exact campaignless runs must not inherit applied/draft/context campaign lenses.
  const exactRunCampaignId = hasExactRunLoad
    ? (exactRun?.campaign_id ?? "").trim()
    : null;
  const reviewCampaignId =
    hasExactRunLoad
      ? (exactRunCampaignId ?? "")
      : appliedSession?.campaignId ?? draftCampaignId ?? context.campaignId;
  // Exact worldbuilding runs keep session null — never invent a session lens.
  // A rejected or unresolved handoff must not degrade the recap lens either.
  const reviewSessionId = hasExactRunLoad
    ? exactRun?.session_id?.trim() || ""
    : appliedSession?.sessionId || draftSessionId || fallbackSessionId;
  const toolboxConfig = useMemo(() => {
    const sessionNumber = sessionNumberFromId(reviewSessionId) ?? context.ingestSession;
    return createIngestSurfaceConfig({
      ...context,
      campaignId: reviewCampaignId,
      ingestSession: sessionNumber,
    });
  }, [context, reviewCampaignId, reviewSessionId]);

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
          {exactHandoff ? (
            <GraphReviewWorkbenchHeader
              loaded={hasAppliedLoad || hasExactRunLoad}
              sessionLabel={loadBarSummary}
              onOpenLoad={openLoadDialog}
              exactRun={exactRunSummary}
            />
          ) : (
            <GraphReviewWorkbenchHeaderWithActivity
              loaded={hasAppliedLoad}
              sessionLabel={loadBarSummary}
              onOpenLoad={openLoadDialog}
              sessionsLoaded={sessionsLoaded}
              hasAppliedLoad={hasAppliedLoad}
              warmupStatus={warmupStatus}
              draftCampaignId={draftCampaignId}
              draftSessionId={draftSessionId}
              onSurfaceChromeChange={onSurfaceChromeChange}
            />
          )}

          {sessionsError ? <p className="graph-review-error">{sessionsError}</p> : null}
          {exactRunError ? (
            <p className="graph-review-error" data-testid="graph-review-exact-run-error">
              {exactRunError}
            </p>
          ) : null}
          {exactRunStatus === "loading" ? (
            <p className="plan-projection-empty">Loading exact extraction run…</p>
          ) : null}

          {hasExactRunLoad ? (
            <div
              className="graph-review-exact-run-panel"
              data-testid="graph-review-exact-run-panel"
            >
              <p>
                Bound to exact ExtractionRun <code>{exactRun!.run_id}</code>. Prepare uses
                runId-only server resolution; no latest-run fallback.
              </p>
              {exactReviewStatus === "loading" ? (
                <p className="plan-projection-empty">Loading source evidence…</p>
              ) : null}
              {exactReviewError ? (
                <p className="graph-review-error" data-testid="graph-review-exact-run-review-error">
                  {exactReviewError}
                </p>
              ) : null}
              {exactReview ? <GraphReviewExactRunProjection review={exactReview} /> : null}
              {!exactRunReviewable ? (
                <p data-testid="graph-review-exact-run-unreviewable">
                  Run status is <code>{exactRun!.status}</code> and is not reviewable for
                  promotion.
                </p>
              ) : !exactRunPromotable ? (
                <p data-testid="graph-review-exact-run-not-promotable">
                  {exactRunNonPromotableReason
                    ?? "This ExtractionRun is inspect-only and cannot be prepared for World Graph merge."}
                </p>
              ) : exactReviewStatus === "error" ? null : (
                <div className="graph-review-extract-promote-actions">
                  <button
                    type="button"
                    className="primary"
                    data-testid="graph-review-exact-run-prepare"
                    disabled={
                      exactPreparing ||
                      exactConfirmInFlight ||
                      exactReviewStatus !== "ready" ||
                      !exactReview
                    }
                    onClick={() => {
                      void onPrepareExactRun();
                    }}
                  >
                    {exactPreparing ? "Preparing…" : "Review & merge"}
                  </button>
                  {exactPrepareError ? (
                    <p className="graph-review-error">{exactPrepareError}</p>
                  ) : null}
                </div>
              )}
              {exactPrepared ? (
                <GraphReviewExtractPromoteSheet
                  prepared={exactPrepared}
                  onClose={() => setExactPrepared(null)}
                  onConfirmInFlightChange={setExactConfirmInFlight}
                  onCatalogRefresh={refreshCatalog}
                />
              ) : null}
            </div>
          ) : (
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
          )}

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
