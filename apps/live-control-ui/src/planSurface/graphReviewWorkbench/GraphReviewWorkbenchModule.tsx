import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import {
  getExtractionRun,
  getExtractionRunStatus,
  getGoldReviewCompare,
  getGoldReviewSessions,
  getManualReviewBed,
  getManualReviewBeds,
  LiveApiError,
} from "../../api/liveApi";
import type {
  ExtractionRunRecord,
  ExtractionRunStatusResponse,
  GoldReviewCompareResponse,
  GoldReviewSessionSummary,
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
import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { buildIngestSurfaceIdentity } from "../../agentInteraction/projectionSurfacePublication";
import type { PlanContextDescriptor } from "../types";
import { resolveInitialReviewCampaignId } from "../sessionCampaignContext";
import type { SurfaceInformationChannel } from "../../surfaceInformation";
import type { ExtractionRunCatalogResponse } from "../../ingestSurface/ingestRunCatalogApi";
import { GraphReviewWorkbenchHeader } from "./GraphReviewWorkbenchHeader";
import { GraphReviewSessionToolbar } from "./GraphReviewSessionToolbar";
import { GraphReviewLoadSurface } from "./GraphReviewLoadSurface";
import { GraphReviewLiveProjectionPanel } from "./GraphReviewLiveProjectionPanel";
import { GraphReviewLiveStateProvider } from "./GraphReviewLiveStateContext";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";
import { GraphReviewCommittedProjectionPanel } from "./GraphReviewCommittedProjectionPanel";
import {
  catalogRunBindingKey,
  exactRunBindingKey,
  type GraphReviewCommittedBinding,
} from "./graphReviewCommittedAuthority";
import { GraphReviewDiagnosticsProjectionBinding } from "./GraphReviewDiagnosticsProjectionBinding";
import { GraphReviewAuthorNodeHost } from "./GraphReviewAuthorNodeHost";
import { GraphReviewExactRunProjection } from "./GraphReviewExactRunProjection";
import { GraphReviewExtractPromoteSheet } from "./GraphReviewExtractPromoteSheet";
import { GraphReviewFirstWorldPublishSheet } from "./GraphReviewFirstWorldPublishSheet";
import {
  type GraphReviewAppliedSelection,
  resolvePersistedAppliedSelection,
  writeAppliedSelectionToStorage,
  writeAppliedSelectionToUrl,
} from "./graphReviewAppliedSelection";
import {
  buildGraphReviewCatalog,
  catalogRunToLane,
  catalogSessionToGoldLane,
  catalogSessionsForReviewCampaign,
  type GraphReviewCatalogSession,
  formatCompactAppliedLoadLabel,
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
  catalogChannel: SurfaceInformationChannel<ExtractionRunCatalogResponse>;
  onCatalogRefresh: () => void;
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
  const run = pickDefaultWorkbenchRun(session.availableRuns);
  return {
    campaignId,
    sessionId: session.sessionId,
    runId: run?.run.run_id ?? null,
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
  if (!session) return { ...selection };
  if (selection.runId) {
    const exact = session.availableRuns.find((entry) => entry.run.run_id === selection.runId);
    return {
      campaignId: selection.campaignId,
      sessionId: selection.sessionId,
      runId: exact ? exact.run.run_id : selection.runId,
    };
  }
  return {
    campaignId: selection.campaignId,
    sessionId: selection.sessionId,
    runId: null,
  };
}

function persistAppliedSelection(selection: GraphReviewAppliedSelection): void {
  writeAppliedSelectionToUrl(selection);
  writeAppliedSelectionToStorage(selection);
}

export function GraphReviewWorkbenchModule({
  context,
  catalogChannel,
  onCatalogRefresh,
}: GraphReviewWorkbenchModuleProps) {
  const fallbackSessionId = `session-${context.ingestSession}`;
  const requestedSessionId = requestedSessionFromLocation();
  const toolboxConfig = useMemo(() => createIngestSurfaceConfig(context), [context]);
  const { publishProjectionSurface, updateProjectionSurfaceConfig } = useAgentInteraction();

  // Identity registration and same-identity config updates are separate
  // operations: a config-only change must not unbind the surface lease.
  const projectionPublication = useMemo(
    () => ({
      identity: buildIngestSurfaceIdentity({
        campaignId: context.campaignId,
        liveSession: context.liveSession,
        ingestSession: context.ingestSession,
      }),
      config: toolboxConfig,
    }),
    [context.campaignId, context.ingestSession, context.liveSession, toolboxConfig],
  );
  const projectionInstanceKey = projectionPublication.identity.instanceKey;
  const projectionPublicationRef = useRef(projectionPublication);
  projectionPublicationRef.current = projectionPublication;
  const [exactHandoff, setExactHandoff] = useState<GraphReviewExactRunHandoff | null>(() =>
    parseGraphReviewRunHandoff(
      typeof window !== "undefined" ? window.location.search : "",
    ),
  );
  const exactHandoffErrors = useMemo(
    () => (exactHandoff ? assertExactRunHandoff(exactHandoff) : []),
    [exactHandoff],
  );

  const catalogSnapshot = useSyncExternalStore(
    catalogChannel.subscribe,
    catalogChannel.getSnapshot,
    catalogChannel.getSnapshot,
  );
  const catalogState = catalogSnapshot.state;
  const catalogReady =
    catalogState.status === "ready"
    || catalogState.status === "empty"
    || catalogState.status === "unavailable"
    || catalogState.status === "integrity_error";
  const canonicalRuns =
    catalogState.status === "ready" ? catalogState.value.runs : [];
  const sessionsError =
    catalogState.status === "unavailable" || catalogState.status === "integrity_error"
      ? catalogState.reason
      : null;
  const [goldSessions, setGoldSessions] = useState<GoldReviewSessionSummary[]>([]);

  useEffect(() => {
    if (!catalogReady && !exactHandoff) {
      return publishProjectionSurface(null);
    }
    return publishProjectionSurface(projectionPublicationRef.current);
  }, [catalogReady, exactHandoff, projectionInstanceKey, publishProjectionSurface]);

  useEffect(() => {
    if (!catalogReady && !exactHandoff) return;
    updateProjectionSurfaceConfig(projectionPublication);
  }, [catalogReady, exactHandoff, projectionPublication, updateProjectionSurfaceConfig]);

  const catalogSessions = useMemo(
    () => buildGraphReviewCatalog(canonicalRuns, goldSessions),
    [canonicalRuns, goldSessions],
  );

  const [appliedSelection, setAppliedSelection] = useState<GraphReviewAppliedSelection | null>(
    null,
  );
  const [draftCampaignId, setDraftCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
  const [draftSessionId, setDraftSessionId] = useState("");
  const [draftRunId, setDraftRunId] = useState<string | null>(null);
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
  const [catalogConfirmInFlight, setCatalogConfirmInFlight] = useState(false);
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
    if (!appliedSession || !appliedSelection?.runId) return null;
    return (
      appliedSession.availableRuns.find(
        (entry) => entry.run.run_id === appliedSelection.runId,
      ) ?? null
    );
  }, [appliedSelection, appliedSession]);
  const selectedRunMissing =
    Boolean(appliedSelection?.runId) && Boolean(appliedSession) && !appliedLiveRun;

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
        (entry) => entry.run.run_id === draftRunId,
      ) ?? null
    );
  }, [draftRunId, draftSession]);

  const goldLane = useMemo(
    () => (appliedSession ? catalogSessionToGoldLane(appliedSession) : null),
    [appliedSession],
  );
  const liveLane = useMemo(
    () => (appliedLiveRun ? catalogRunToLane(appliedLiveRun) : null),
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

  useEffect(() => {
    if (!catalogReady) return;
    const persistedHint = resolvePersistedAppliedSelection();
    setAppliedSelection((current) => {
      const hint = persistedHint ?? current;
      if (!hint) return current;
      return resolveSelectionAgainstCatalog(hint, catalogSessions) ?? hint;
    });
    const draftSource =
      resolveSelectionAgainstCatalog(persistedHint, catalogSessions)
      ?? buildDefaultDraft(
        catalogSessions,
        resolveInitialReviewCampaignId(context.campaignId),
        requestedSessionId,
        fallbackSessionId,
      );
    if (draftSource) {
      setDraftCampaignId(draftSource.campaignId);
      setDraftSessionId(draftSource.sessionId);
      setDraftRunId(draftSource.runId);
    }
    if (persistedHint?.runId) {
      const restored = resolveSelectionAgainstCatalog(persistedHint, catalogSessions);
      if (restored?.runId) persistAppliedSelection(restored);
    }
  }, [
    catalogReady,
    catalogSessions,
    context.campaignId,
    fallbackSessionId,
    requestedSessionId,
  ]);

  useEffect(() => {
    let cancelled = false;
    setGoldSessions([]);
    void getGoldReviewSessions()
      .then((response) => {
        if (cancelled) return;
        setGoldSessions(response.sessions);
      })
      .catch(() => {
        if (cancelled) return;
        setGoldSessions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [catalogSnapshot.generation]);

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
    if (!appliedSession.hasGold || !appliedLiveRun.compatibilityManifestPath) {
      setCompare(null);
      setCompareStatus("idle");
      setCompareError(
        appliedSession.hasGold && !appliedLiveRun.compatibilityManifestPath
          ? "Gold compare is unavailable because no exact run_id compatibility locator exists."
          : null,
      );
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
        manifestPath: appliedLiveRun.compatibilityManifestPath,
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
    if (!catalogReady) return;
    void loadCompare();
  }, [loadCompare, catalogReady]);

  const loadBlockedByConfirm = catalogConfirmInFlight || exactConfirmInFlight;

  const openLoadDialog = () => {
    if (loadBlockedByConfirm) return;
    if (appliedSelection) {
      setDraftCampaignId(appliedSelection.campaignId);
      setDraftSessionId(appliedSelection.sessionId);
      setDraftRunId(appliedSelection.runId);
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
        setDraftRunId(defaultDraft.runId);
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
    setDraftRunId(pickDefaultWorkbenchRun(nextSession?.availableRuns ?? [])?.run.run_id ?? null);
  };

  const handleDraftSessionSelect = (sessionId: string) => {
    const session =
      draftCampaignSessions.find((item) => item.sessionId === sessionId) ?? null;
    setDraftSessionId(sessionId);
    setDraftRunId(pickDefaultWorkbenchRun(session?.availableRuns ?? [])?.run.run_id ?? null);
  };

  const handleApplyLoad = () => {
    if (loadBlockedByConfirm) return;
    if (!draftSession || !draftLiveRun) return;
    const nextApplied: GraphReviewAppliedSelection = {
      campaignId: draftCampaignId,
      sessionId: draftSession.sessionId,
      runId: draftLiveRun.run.run_id,
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

  const exactRunFirstWorldEligible = exactReview?.firstWorldPublishEligible === true;
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

  const committedBinding = useMemo<GraphReviewCommittedBinding | null>(() => {
    if (hasExactRunLoad && exactRun?.run_id) {
      const sourceArtifactId =
        exactRun.source_artifact_id?.trim()
        || exactHandoff?.sourceArtifactId?.trim()
        || "";
      if (!sourceArtifactId) return null;
      const campaignId =
        (exactRunCampaignId ?? exactRun.campaign_id ?? "").trim() || null;
      const sessionId = exactRun.session_id?.trim() || null;
      return {
        kind: "exact_run",
        key: exactRunBindingKey({
          runId: exactRun.run_id,
          sourceArtifactId,
          campaignId,
          sessionId,
        }),
        runId: exactRun.run_id,
        sourceArtifactId,
        campaignId,
        sessionId,
      };
    }
    if (hasAppliedLoad && appliedLiveRun?.run.run_id) {
      return {
        kind: "catalog_run",
        key: catalogRunBindingKey({
          runId: appliedLiveRun.run.run_id,
          campaignId: reviewCampaignId,
          sessionId: reviewSessionId,
        }),
        runId: appliedLiveRun.run.run_id,
        campaignId: reviewCampaignId,
        sessionId: reviewSessionId,
      };
    }
    return null;
  }, [
    appliedLiveRun?.run.run_id,
    exactHandoff?.sourceArtifactId,
    exactRun?.campaign_id,
    exactRun?.run_id,
    exactRun?.session_id,
    exactRun?.source_artifact_id,
    exactRunCampaignId,
    hasAppliedLoad,
    hasExactRunLoad,
    reviewCampaignId,
    reviewSessionId,
  ]);

  if (!catalogReady && !exactHandoff) {
    return (
      <div className="graph-review-workbench-root">
        <GraphReviewWorkbenchHeader loaded={false} sessionLabel={null} onOpenLoad={() => undefined} />
        <p className="plan-projection-empty">Loading graph review sessions…</p>
      </div>
    );
  }

  return (
    <GraphReviewLiveStateProvider
        campaignId={reviewCampaignId}
        sessionId={reviewSessionId}
        liveRun={hasAppliedLoad ? appliedLiveRun : null}
        committedBinding={committedBinding}
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
        <GraphReviewDiagnosticsProjectionBinding />
        <div className="graph-review-workbench-root">
          <GraphReviewWorkbenchHeader
            loaded={hasAppliedLoad || hasExactRunLoad}
            sessionLabel={loadBarSummary}
            onOpenLoad={openLoadDialog}
            loadDisabled={loadBlockedByConfirm}
            loadDisabledReason={
              loadBlockedByConfirm
                ? "Merge confirmation is in progress."
                : null
            }
            exactRun={exactRunSummary}
          />

          {sessionsError ? <p className="graph-review-error">{sessionsError}</p> : null}
          {catalogState.status === "empty" ? (
            <p className="plan-projection-empty">No canonical ExtractionRuns are stored yet.</p>
          ) : null}
          {selectedRunMissing ? (
            <p className="graph-review-error" data-testid="graph-review-selected-run-missing">
              Selected run {appliedSelection?.runId} is no longer in the canonical catalog.
            </p>
          ) : null}
          {exactRunError ? (
            <p className="graph-review-error" data-testid="graph-review-exact-run-error">
              {exactRunError}
            </p>
          ) : null}
          {exactRunStatus === "loading" ? (
            <p className="plan-projection-empty">Loading exact extraction run…</p>
          ) : null}

          {hasExactRunLoad ? (
            <GraphReviewExactRunBranch
              exactRun={exactRun!}
              exactReview={exactReview}
              exactReviewStatus={exactReviewStatus}
              exactReviewError={exactReviewError}
              exactRunReviewable={exactRunReviewable}
              exactRunPromotable={exactRunPromotable}
              exactRunFirstWorldEligible={exactRunFirstWorldEligible}
              exactRunNonPromotableReason={exactRunNonPromotableReason}
              exactPreparing={exactPreparing}
              exactConfirmInFlight={exactConfirmInFlight}
              exactPrepareError={exactPrepareError}
              exactPrepared={exactPrepared}
              onPrepare={() => {
                void onPrepareExactRun();
              }}
              onClosePrepared={() => setExactPrepared(null)}
              onConfirmInFlightChange={setExactConfirmInFlight}
              onCatalogRefresh={onCatalogRefresh}
            />
          ) : (
            <GraphReviewAuthorNodeHost
              onRequestLoad={openLoadDialog}
              chrome={
                !hasCatalogSessions && catalogState.status !== "empty" ? (
                  <p className="plan-projection-empty">
                    No canonical recap ExtractionRuns are available yet. Use Ingest Recap in the toolbox to
                    paste a recap, run extraction, and persist an APP-STATE run.
                  </p>
                ) : !hasAppliedLoad ? (
                  <p className="plan-projection-empty graph-review-load-empty">
                    Load an ingested session to review extracted objects in recap prose.
                  </p>
                ) : (
                  <GraphReviewSessionToolbar
                    onConfirmInFlightChange={setCatalogConfirmInFlight}
                  />
                )
              }
              projection={hasAppliedLoad ? <GraphReviewLiveProjectionPanel /> : null}
            />
          )}

          <GraphReviewLoadSurface
            open={loadDialogOpen}
            sessions={catalogSessions}
            draftCampaignId={draftCampaignId}
            draftSessionId={draftSessionId}
            draftRunId={draftRunId}
            draftSession={draftSession}
            draftLiveRun={draftLiveRun}
            onClose={() => setLoadDialogOpen(false)}
            onLoad={handleApplyLoad}
            onCampaignSelect={handleDraftCampaignSelect}
            onSessionSelect={handleDraftSessionSelect}
            onRunSelect={setDraftRunId}
          />
        </div>
      </GraphReviewLiveStateProvider>
  );
}

function GraphReviewExactRunBranch(props: {
  exactRun: ExtractionRunRecord;
  exactReview: ExactRunReviewPackage | null;
  exactReviewStatus: "idle" | "loading" | "ready" | "error";
  exactReviewError: string | null;
  exactRunReviewable: boolean;
  exactRunPromotable: boolean;
  exactRunFirstWorldEligible: boolean;
  exactRunNonPromotableReason: string | null;
  exactPreparing: boolean;
  exactConfirmInFlight: boolean;
  exactPrepareError: string | null;
  exactPrepared: ExtractPromotePrepareResponse | null;
  onPrepare: () => void;
  onClosePrepared: () => void;
  onConfirmInFlightChange: (inFlight: boolean) => void;
  onCatalogRefresh: () => void | Promise<void>;
}) {
  const { committedPhase } = useGraphReviewLiveState();

  // After terminal receipt for this binding, committed projection is the only
  // primary result — never exact-run candidate source/assertions.
  if (committedPhase !== "candidate") {
    return (
      <div
        className="graph-review-exact-run-panel"
        data-testid="graph-review-exact-run-panel"
        data-committed-primary="true"
      >
        <GraphReviewCommittedProjectionPanel />
      </div>
    );
  }

  return (
    <div
      className="graph-review-exact-run-panel"
      data-testid="graph-review-exact-run-panel"
    >
      <p>
        Bound to exact ExtractionRun <code>{props.exactRun.run_id}</code>. Prepare uses
        runId-only server resolution; no latest-run fallback.
      </p>
      {props.exactReviewStatus === "loading" ? (
        <p className="plan-projection-empty">Loading source evidence…</p>
      ) : null}
      {props.exactReviewError ? (
        <p className="graph-review-error" data-testid="graph-review-exact-run-review-error">
          {props.exactReviewError}
        </p>
      ) : null}
      {props.exactReview ? <GraphReviewExactRunProjection review={props.exactReview} /> : null}
      {!props.exactRunReviewable ? (
        <p data-testid="graph-review-exact-run-unreviewable">
          Run status is <code>{props.exactRun.status}</code> and is not reviewable for
          promotion.
        </p>
      ) : props.exactRunFirstWorldEligible && props.exactReview ? (
        props.exactReviewStatus === "error" ? null : (
          <GraphReviewFirstWorldPublishSheet
            review={props.exactReview}
            onConfirmInFlightChange={props.onConfirmInFlightChange}
            onCatalogRefresh={props.onCatalogRefresh}
          />
        )
      ) : !props.exactRunPromotable ? (
        <p data-testid="graph-review-exact-run-not-promotable">
          {props.exactRunNonPromotableReason
            ?? "This ExtractionRun is inspect-only and cannot be prepared for World Graph merge."}
        </p>
      ) : props.exactReviewStatus === "error" ? null : (
        <GraphReviewExactRunPromoteChrome
          exactPreparing={props.exactPreparing}
          exactConfirmInFlight={props.exactConfirmInFlight}
          exactReviewReady={props.exactReviewStatus === "ready" && Boolean(props.exactReview)}
          exactPrepareError={props.exactPrepareError}
          onPrepare={props.onPrepare}
        />
      )}
      {props.exactPrepared ? (
        <GraphReviewExtractPromoteSheet
          prepared={props.exactPrepared}
          onClose={props.onClosePrepared}
          onConfirmInFlightChange={props.onConfirmInFlightChange}
          onCatalogRefresh={props.onCatalogRefresh}
        />
      ) : null}
    </div>
  );
}

function GraphReviewExactRunPromoteChrome(props: {
  exactPreparing: boolean;
  exactConfirmInFlight: boolean;
  exactReviewReady: boolean;
  exactPrepareError: string | null;
  onPrepare: () => void;
}) {
  const { committedPhase, committedReceipt } = useGraphReviewLiveState();
  const hasTerminalCommittedReceipt =
    committedPhase !== "candidate" && committedReceipt != null;

  if (hasTerminalCommittedReceipt) {
    return (
      <p
        className="module-muted"
        data-testid="graph-review-exact-run-prepare-suppressed"
      >
        Prepare/confirm hidden while committed World Graph authority is active.
      </p>
    );
  }

  return (
    <div className="graph-review-extract-promote-actions">
      <button
        type="button"
        className="primary"
        data-testid="graph-review-exact-run-prepare"
        disabled={
          props.exactPreparing ||
          props.exactConfirmInFlight ||
          !props.exactReviewReady
        }
        onClick={props.onPrepare}
      >
        {props.exactPreparing ? "Preparing…" : "Review & merge"}
      </button>
      {props.exactPrepareError ? (
        <p className="graph-review-error">{props.exactPrepareError}</p>
      ) : null}
    </div>
  );
}
