import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getExtractionRun,
  getExtractionRunStatus,
  getGoldReviewCompare,
  getGoldReviewSessions,
  getGraphIngestRuns,
  getManualReviewBed,
  getManualReviewBeds,
  LiveApiError,
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
  prepareExtractPromote,
} from "../../api/extractPromoteApi";
import type { ExtractPromotePrepareResponse } from "../../api/types";
import type { GoldReviewSelection } from "../graphGoldReview/graphGoldReviewUtils";
import { requestedSessionFromLocation } from "../graphGoldReview/graphGoldReviewUtils";
import { createIngestSurfaceConfig } from "../config/ingestSurfaceConfig";
import { AdaptiveProjectionContainer } from "../projection/AdaptiveProjectionContainer";
import { ProjectionProvider } from "../projection/projectionContext";
import type { PlanContextDescriptor } from "../types";
import { resolveInitialReviewCampaignId } from "../sessionCampaignContext";
import { GraphReviewWorkbenchHeader } from "./GraphReviewWorkbenchHeader";
import { GraphReviewSessionToolbar } from "./GraphReviewSessionToolbar";
import { GraphReviewLoadSurface } from "./GraphReviewLoadSurface";
import { GraphReviewLiveProjectionPanel } from "./GraphReviewLiveProjectionPanel";
import { GraphReviewLiveStateProvider } from "./GraphReviewLiveStateContext";
import { GraphReviewAuthorNodeHost } from "./GraphReviewAuthorNodeHost";
import { GraphReviewExtractPromoteSheet } from "./GraphReviewExtractPromoteSheet";
import {
  type GraphReviewAppliedSelection,
  resolvePersistedAppliedSelection,
  writeAppliedSelectionToStorage,
  writeAppliedSelectionToUrl,
} from "./graphReviewAppliedSelection";
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
  parseGraphReviewRunHandoff,
} from "./graphReviewRunSelection";
import type { GraphReviewExactRunLineage } from "./graphReviewRunSelection";

interface GraphReviewWorkbenchModuleProps {
  context: PlanContextDescriptor;
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

export function GraphReviewWorkbenchModule({ context }: GraphReviewWorkbenchModuleProps) {
  const fallbackSessionId = `session-${context.ingestSession}`;
  const requestedSessionId = requestedSessionFromLocation();
  const toolboxConfig = useMemo(() => createIngestSurfaceConfig(context), [context]);
  const exactHandoff = useMemo(
    () => parseGraphReviewRunHandoff(typeof window !== "undefined" ? window.location.search : ""),
    [],
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
    const nextApplied: GraphReviewAppliedSelection = {
      campaignId: draftCampaignId,
      sessionId: draftSession.sessionId,
      manifestPath: draftLiveRun.manifest_path,
    };
    setAppliedSelection(nextApplied);
    persistAppliedSelection(nextApplied);
    setLoadDialogOpen(false);
  };

  const exactRunReviewable = exactRun?.status === "reviewable";
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
        }
      : null;

  const onPrepareExactRun = useCallback(async () => {
    if (!exactHandoff || !exactRunReviewable || exactPreparing || exactConfirmInFlight) return;
    setExactPreparing(true);
    setExactPrepareError(null);
    try {
      const response = await prepareExtractPromote({ runId: exactHandoff.extractionRunId });
      setExactPrepared(response);
    } catch (error) {
      setExactPrepared(null);
      if (error instanceof ExtractPromoteApiError) {
        setExactPrepareError(error.message);
      } else if (error instanceof Error) {
        setExactPrepareError(error.message);
      } else {
        setExactPrepareError("Failed to prepare promotion for exact run.");
      }
    } finally {
      setExactPreparing(false);
    }
  }, [exactConfirmInFlight, exactHandoff, exactPreparing, exactRunReviewable]);

  if (!sessionsLoaded && !exactHandoff) {
    return (
      <div className="graph-review-workbench-root">
        <GraphReviewWorkbenchHeader loaded={false} sessionLabel={null} onOpenLoad={() => undefined} />
        <p className="plan-projection-empty">Loading graph review sessions…</p>
      </div>
    );
  }

  const hasAppliedLoad = Boolean(appliedSelection && appliedSession && appliedLiveRun);
  const hasExactRunLoad = Boolean(exactHandoff && exactRunStatus === "ready" && exactRun);
  const hasCatalogSessions = catalogSessions.length > 0 || Boolean(sessionsError);
  // Keep live-state (and the Tools drawer) mounted even before a session is loaded so
  // Ingest Recap remains reachable from the empty /ingest landing state.
  const reviewCampaignId =
    (hasExactRunLoad ? exactRun?.campaign_id : null) ??
    appliedSession?.campaignId ??
    draftCampaignId ??
    context.campaignId;
  // Exact worldbuilding runs keep session null — never invent a session lens.
  // A rejected or unresolved handoff must not degrade the recap lens either.
  const reviewSessionId = hasExactRunLoad
    ? exactRun?.session_id?.trim() || ""
    : appliedSession?.sessionId || draftSessionId || fallbackSessionId;

  return (
    <ProjectionProvider config={toolboxConfig}>
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
          <GraphReviewWorkbenchHeader
            loaded={hasAppliedLoad || hasExactRunLoad}
            sessionLabel={loadBarSummary}
            onOpenLoad={openLoadDialog}
            exactRun={exactRunSummary}
          />

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
              {!exactRunReviewable ? (
                <p data-testid="graph-review-exact-run-unreviewable">
                  Run status is <code>{exactRun!.status}</code> and is not reviewable for
                  promotion.
                </p>
              ) : (
                <div className="graph-review-extract-promote-actions">
                  <button
                    type="button"
                    className="primary"
                    data-testid="graph-review-exact-run-prepare"
                    disabled={exactPreparing || exactConfirmInFlight}
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
    </ProjectionProvider>
  );
}
