import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import {
  getExtractionRun,
  getExtractionRunStatus,
  getGoldReviewCompare,
  getGoldReviewSessions,
  getHistoricalRecapWorldProjection,
  getManualReviewBed,
  getManualReviewBeds,
  LiveApiError,
} from "../../api/liveApi";
import type {
  ExtractionRunRecord,
  ExtractionRunStatusResponse,
  GoldReviewCompareResponse,
  GoldReviewSessionSummary,
  HistoricalRecapWorldProjectionResponse,
  ManualReviewBedDetail,
  ManualReviewBedSummary,
} from "../../api/types";
import {
  ExtractPromoteApiError,
  getExactRunReviewPackage,
  correctExactRunEvidence,
  correctRecapRunEvidence,
  prepareExtractPromote,
} from "../../api/extractPromoteApi";
import type { RecapEvidenceCorrectionResponse, ExactRunEvidenceQuoteCorrection, ExactRunReviewPackage, ExtractPromotePrepareResponse } from "../../api/types";
import type { GoldReviewSelection } from "../graphGoldReview/graphGoldReviewUtils";
import { requestedSessionFromLocation } from "../graphGoldReview/graphGoldReviewUtils";
import { createIngestSurfaceConfig } from "../config/ingestSurfaceConfig";
import { useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { buildIngestSurfaceIdentity } from "../../agentInteraction/projectionSurfacePublication";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";
import type { SelectedWorldState } from "../../selectedWorld/SelectedWorldContext";
import type { PlanContextDescriptor } from "../types";
import { resolveInitialReviewCampaignId } from "../sessionCampaignContext";
import type { SurfaceInformationChannel } from "../../surfaceInformation";
import type { ExtractionRunCatalogResponse } from "../../ingestSurface/ingestRunCatalogApi";
import { GraphReviewWorkbenchHeader } from "./GraphReviewWorkbenchHeader";
import { RecapGraphModule } from "../graphPreview/RecapGraphModule";
import { GraphReviewLiveStateProvider } from "./GraphReviewLiveStateContext";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";
import { GraphReviewCommittedProjectionPanel } from "./GraphReviewCommittedProjectionPanel";
import {
  exactRunBindingKey,
  type GraphReviewCommittedBinding,
} from "./graphReviewCommittedAuthority";
import { GraphReviewDiagnosticsProjectionBinding } from "./GraphReviewDiagnosticsProjectionBinding";
import { GraphReviewExactRunProjection } from "./GraphReviewExactRunProjection";
import { GraphReviewHistoricalRecapProjection } from "./GraphReviewHistoricalRecapProjection";
import { GraphReviewExtractPromoteSheet } from "./GraphReviewExtractPromoteSheet";
import { GraphReviewFirstWorldPublishSheet } from "./GraphReviewFirstWorldPublishSheet";
import {
  resolveGraphReviewWriteAuthority,
  resolvePublishedMemoryBrowseContext,
} from "./graphReviewAuthority";
import {
  type GraphReviewAppliedSelection,
  resolvePersistedAppliedSelection,
} from "./graphReviewAppliedSelection";
import {
  buildGraphReviewCatalog,
  catalogSessionsForReviewCampaign,
  type GraphReviewCatalogSession,
  isCatalogRunHistoricalRecapInspectable,
  isCatalogRunPromotedHistory,
  pickDefaultCatalogSession,
} from "./graphReviewWorkbenchUtils";
import { manualVariantToLaneView } from "./graphReviewVariantReferenceUtils";
import {
  assertExactRunHandoff,
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
  /** Opens exact recap evidence without granting writes against the selected target World. */
  sourceReviewOnly?: boolean;
  sourceReviewRunId?: string | null;
  /** Current page URL snapshot; keeps exact-run selection in sync on same-World navigation. */
  locationSearch?: string;
  onLocationSearchChange?: (search: string) => void;
}

const EMPTY_EXTRACTION_RUNS: ExtractionRunRecord[] = [];

function selectedWorldGuidance(selection: SelectedWorldState): string | null {
  switch (selection.kind) {
    case "managed":
      return null;
    case "loading":
      return "Wait for the selected World to finish verification before preparing this recap.";
    case "error":
      return `Selected World could not be verified: ${selection.message}`;
    case "legacy":
      return "Select a verified managed World before preparing this recap.";
  }
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
  return {
    campaignId,
    sessionId: session.sessionId,
    runId: null,
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
  if (!session) return { ...selection, runId: null };
  if (selection.runId) {
    const exact = session.availableRuns.find((entry) => entry.run.run_id === selection.runId);
    return {
      campaignId: selection.campaignId,
      sessionId: selection.sessionId,
      runId: exact ? exact.run.run_id : null,
    };
  }
  return {
    campaignId: selection.campaignId,
    sessionId: selection.sessionId,
    runId: null,
  };
}

type RecapQuoteRequest = { parentRunId: string; parentCandidateSha256: string; corrections: ExactRunEvidenceQuoteCorrection[] };
type RecapQuoteRecovery = {
  version: 1; key: string; id: string; request: RecapQuoteRequest;
  receipt?: RecapEvidenceCorrectionResponse;
};
const quoteDigest = (value: unknown): string | null => typeof value === "string"
  && /^(?:sha256:)?[a-f0-9]{64}$/.test(value) ? value.replace(/^sha256:/, "") : null;
function recapQuoteScope(run: ExtractionRunRecord | null, review: ExactRunReviewPackage | null, world: string | null): string | null {
  if (!run || !review || !world || run.status !== "reviewable" || run.source_domain !== "recap"
    || run.profile_id !== "recap_category_v1@1.0" || review.schema !== "dmb_extract_promote_exact_run_review_v1"
    || review.runId !== run.run_id || review.sourceDomain !== "recap" || review.sourceArtifactId !== run.source_artifact_id
    || review.campaignId !== run.campaign_id || review.sessionId !== run.session_id
    || review.inspectionStatus !== "invalid_evidence") return null;
  const hashes = ["candidate_graph", "source_artifact", "source_span_index"].map((key) => {
    const ref = run.components?.[key];
    return ref?.exists === true ? quoteDigest(ref.sha256) : null;
  });
  if (hashes.some((value) => !value) || quoteDigest(review.sourceRevisionId) !== hashes[1]) return null;
  return JSON.stringify([world, run.run_id, run.source_artifact_id, run.profile_id, run.campaign_id, run.session_id, ...hashes]);
}
function verifyRecapQuoteChild(parent: ExtractionRunRecord, parentReview: ExactRunReviewPackage,
  receipt: RecapEvidenceCorrectionResponse, child: ExtractionRunRecord, review: ExactRunReviewPackage): string {
  const disposition = child.lineage?.semantic_disposition as Record<string, unknown> | undefined;
  if (child.run_id !== receipt.runId || child.status !== "reviewable" || child.source_domain !== "recap"
    || child.profile_id !== parent.profile_id || child.source_artifact_id !== parent.source_artifact_id
    || child.campaign_id !== parent.campaign_id || child.session_id !== parent.session_id
    || child.lineage?.derivation !== "operator_recap_literal_evidence_correction_v1"
    || child.lineage?.parent_run_id !== parent.run_id
    || quoteDigest(child.lineage?.parent_candidate_sha256) !== quoteDigest(receipt.parentCandidateSha256)
    || child.components?.candidate_graph?.exists !== true
    || quoteDigest(child.lineage?.correction_digest) !== quoteDigest(receipt.correctionDigest)
    || quoteDigest(child.components?.candidate_graph?.sha256) !== quoteDigest(receipt.candidateSha256)
    || !disposition || !["held", "accepted", "rejected"].includes(String(disposition.state))
    || quoteDigest(disposition.basis_sha256) !== quoteDigest(receipt.semanticBasisSha256)
    || review.schema !== "dmb_extract_promote_exact_run_review_v1" || review.runId !== child.run_id
    || review.derivedFromRunId !== parent.run_id || review.sourceDomain !== "recap"
    || review.sourceArtifactId !== parent.source_artifact_id || review.sourceRevisionId !== parentReview.sourceRevisionId
    || review.campaignId !== parent.campaign_id || review.sessionId !== parent.session_id) {
    throw new Error("The exact corrected candidate could not be verified. The saved request remains available.");
  }
  for (const key of ["source_artifact", "source_span_index"]) {
    if (child.components?.[key]?.exists !== true
      || child.components[key].uri !== parent.components?.[key]?.uri
      || quoteDigest(child.components[key].sha256) !== quoteDigest(parent.components?.[key]?.sha256)) {
      throw new Error("The corrected candidate's frozen source does not match its parent.");
    }
  }
  return String(disposition.state);
}

export function GraphReviewWorkbenchModule({
  context,
  catalogChannel,
  onCatalogRefresh,
  sourceReviewOnly = false,
  sourceReviewRunId = null,
  locationSearch,
  onLocationSearchChange,
}: GraphReviewWorkbenchModuleProps) {
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const targetGuidance = selectedWorldGuidance(selectedWorld);
  const managedWorldIdRef = useRef<string | null>(managedWorldId);
  managedWorldIdRef.current = managedWorldId;
  const fallbackSessionId = `session-${context.ingestSession}`;
  const requestedSessionId = requestedSessionFromLocation();
  const browseContext = resolvePublishedMemoryBrowseContext({
    fallbackCampaignId: resolveInitialReviewCampaignId(context.campaignId),
    fallbackSessionId,
  });
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
  const [internalExactHandoff, setInternalExactHandoff] = useState<GraphReviewExactRunHandoff | null>(() =>
    parseGraphReviewRunHandoff(
      locationSearch ?? (typeof window !== "undefined" ? window.location.search : ""),
    ),
  );
  const exactHandoff = useMemo(
    () => locationSearch === undefined
      ? internalExactHandoff
      : parseGraphReviewRunHandoff(locationSearch),
    [internalExactHandoff, locationSearch],
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
  const catalogSettled =
    catalogState.status === "ready"
    || catalogState.status === "empty"
    || catalogState.status === "unavailable"
    || catalogState.status === "integrity_error";
  const canonicalRuns =
    catalogState.status === "ready" ? catalogState.value.runs : EMPTY_EXTRACTION_RUNS;
  const [goldSessions, setGoldSessions] = useState<GoldReviewSessionSummary[]>([]);

  // W14: structural Ingest surface stays mounted across catalog observation
  // transitions (including READY → LOADING → READY). Do not unbind on LOADING.
  useEffect(() => {
    return publishProjectionSurface(projectionPublicationRef.current);
  }, [projectionInstanceKey, publishProjectionSurface]);

  useEffect(() => {
    updateProjectionSurfaceConfig(projectionPublication);
  }, [projectionPublication, updateProjectionSurfaceConfig]);

  const catalogSessions = useMemo(
    () => buildGraphReviewCatalog(canonicalRuns, goldSessions),
    [canonicalRuns, goldSessions],
  );

  const [appliedSelection, setAppliedSelection] = useState<GraphReviewAppliedSelection | null>(
    null,
  );
  const [, setDraftCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
  const [, setDraftSessionId] = useState("");
  const [, setCompare] = useState<GoldReviewCompareResponse | null>(null);
  const [, setCompareStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [, setCompareError] = useState<string | null>(null);
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
  const [exactReview, setExactReview] = useState<ExactRunReviewPackage | null>(null);
  const [exactReviewStatus, setExactReviewStatus] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const [exactReviewError, setExactReviewError] = useState<string | null>(null);
  const [exactCorrecting, setExactCorrecting] = useState(false);
  const [exactCorrectionError, setExactCorrectionError] = useState<string | null>(null);
  const [historicalRecapProjection, setHistoricalRecapProjection] =
    useState<HistoricalRecapWorldProjectionResponse | null>(null);
  const [historicalRecapProjectionStatus, setHistoricalRecapProjectionStatus] = useState<
    "idle" | "loading" | "ready" | "error"
  >("idle");
  const [historicalRecapProjectionError, setHistoricalRecapProjectionError] = useState<
    string | null
  >(null);
  const exactRunMatchesHandoff = Boolean(
    exactHandoff
    && exactRun
    && exactRun.run_id === exactHandoff.extractionRunId,
  );
  const parentSourceReviewOnly = sourceReviewOnly;
  const awaitingCurrentExactRun = Boolean(
    exactHandoff?.extractionRunId
    && (!exactRunMatchesHandoff || exactRunStatus !== "ready"),
  );
  const sourceReviewOnlyForCurrentRun = parentSourceReviewOnly;
  const effectiveSourceReviewOnly = sourceReviewOnlyForCurrentRun || awaitingCurrentExactRun;
  const operationScopeKey = JSON.stringify([
    exactHandoff?.extractionRunId ?? null,
    context.campaignId,
    effectiveSourceReviewOnly,
    managedWorldId,
    sourceReviewRunId,
    exactRun?.components?.candidate_graph?.sha256,
    exactRun?.components?.source_artifact?.sha256,
    exactRun?.components?.source_span_index?.sha256,
    exactReview?.sourceRevisionId,
  ]);
  const operationScopeRef = useRef({ key: operationScopeKey, generation: 0 });
  if (operationScopeRef.current.key !== operationScopeKey) {
    operationScopeRef.current = {
      key: operationScopeKey,
      generation: operationScopeRef.current.generation + 1,
    };
  }
  const recapQuoteKey = exactRunMatchesHandoff && exactRunStatus === "ready"
    ? recapQuoteScope(exactRun, exactReview, managedWorldId) : null;
  const recapStorageKey = recapQuoteKey ? "dmb:recap-quote-correction:v1:" + recapQuoteKey : null;
  const recapFlight = useRef<{ key: string; token: symbol } | null>(null);
  const [, refreshRecapRecovery] = useState(0);
  let recapRecovery: RecapQuoteRecovery | null = null;
  let recapRecoveryAvailable = false;
  if (recapStorageKey) {
    try {
      const raw = window.sessionStorage.getItem(recapStorageKey);
      recapRecoveryAvailable = raw !== null;
      if (raw) {
        const parsed = JSON.parse(raw) as RecapQuoteRecovery;
        if (parsed.version === 1 && parsed.key === recapQuoteKey && typeof parsed.id === "string"
          && Array.isArray(parsed.request?.corrections)) recapRecovery = parsed;
      }
    } catch { /* Submit fails closed if durable recovery storage is unavailable. */ }
  }
  const recapCorrectionPending = Boolean(recapQuoteKey && recapFlight.current?.key === recapQuoteKey);
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

  useEffect(() => {
    if (!catalogSettled) return;
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
    }
  }, [
    catalogSettled,
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
        setHistoricalRecapProjection(null);
        setHistoricalRecapProjectionStatus("error");
        setHistoricalRecapProjectionError(exactHandoffErrors.join("; "));
      }
      return;
    }
    let cancelled = false;
    setExactRunStatus("loading");
    setExactRunError(null);
    setExactLineage(null);
    setHistoricalRecapProjection(null);
    setHistoricalRecapProjectionStatus("idle");
    setHistoricalRecapProjectionError(null);
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
      setExactReview(null);
      setExactReviewError(null);
      if (isCatalogRunHistoricalRecapInspectable(run)) {
        setExactReviewStatus("idle");
        setExactReview(null);
        setExactReviewError(null);
        setHistoricalRecapProjectionStatus("loading");
        try {
          const projection = await getHistoricalRecapWorldProjection(run.run_id);
          if (cancelled) return;
          if (
            projection.runId !== run.run_id
            || projection.sourceArtifactId !== run.source_artifact_id
            || projection.sourceDomain !== run.source_domain
            || projection.campaignId !== (run.campaign_id ?? "")
            || projection.sessionId !== (run.session_id ?? "")
          ) {
            throw new Error(
              "historical recap projection identity does not match the loaded ExtractionRun",
            );
          }
          if (
            sourceReviewOnlyForCurrentRun
            && projection.worldId.trim() !== context.campaignId.trim()
          ) {
            throw new Error(
              "historical recap projection World does not match the selected target World",
            );
          }
          setHistoricalRecapProjection(projection);
          setHistoricalRecapProjectionStatus("ready");
        } catch (error) {
          if (cancelled) return;
          setHistoricalRecapProjection(null);
          setHistoricalRecapProjectionStatus("error");
          setHistoricalRecapProjectionError(
            error instanceof LiveApiError || error instanceof Error
              ? error.message
              : "Failed to load historical recap projection.",
          );
        }
        return;
      }
      setExactReviewStatus("loading");
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
        if (
          sourceReviewOnlyForCurrentRun
          && packageResponse.worldId?.trim()
          && packageResponse.worldId.trim() !== context.campaignId.trim()
        ) {
          setExactReview(null);
          setExactReviewStatus("error");
          setExactReviewError(
            "exact-run review package declares a different World from the selected target",
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
  }, [context.campaignId, exactHandoff, exactHandoffErrors, sourceReviewOnlyForCurrentRun]);

  // Catalog recap is the published World Graph recap reader
  // (same RecapGraphModule as Plan → Recap). Extract-promote review-package
  // stays on exact-run handoff only.
  useEffect(() => {
    if (exactHandoff) return;
    setExactRun(null);
    setExactLineage(null);
    setExactRunStatus("idle");
    setExactRunError(null);
    setExactReview(null);
    setExactReviewStatus("idle");
    setExactReviewError(null);
    setHistoricalRecapProjection(null);
    setHistoricalRecapProjectionStatus("idle");
    setHistoricalRecapProjectionError(null);
    setExactPrepared(null);
    setExactPrepareError(null);
  }, [exactHandoff]);

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
    if (!catalogSettled) return;
    void loadCompare();
  }, [loadCompare, catalogSettled]);

  const invalidExactEvidence = exactReview?.inspectionStatus === "invalid_evidence";
  const exactRunFirstWorldEligible = exactReview?.firstWorldPublishEligible === true
    && !invalidExactEvidence;
  const exactRunReviewable = exactRun?.status === "reviewable";
  const exactRunPromotable =
    exactRunReviewable
    && !invalidExactEvidence
    && exactReview?.promotable !== false
    && (exactRun?.source_domain ?? "").trim() !== "worldbuilding";
  const exactRunNonPromotableReason =
    exactReview?.promotableReason?.trim()
    || (
      (exactRun?.source_domain ?? "").trim() === "worldbuilding"
        ? "Worldbuilding ExtractionRuns are inspect-only until an approved authority-elevation contract lands."
        : null
    );
  // Exact-run handoff wins presentation identity over a stale persisted catalog
  // selection. Catalog recap chrome uses appliedLiveRun when there is no exactRun.
  const loadedRun = exactRun ?? appliedLiveRun?.run ?? null;
  const loadedReviewable = loadedRun?.status === "reviewable";
  const loadedWorldbuilding = (loadedRun?.source_domain ?? "").trim() === "worldbuilding";
  const loadedPromotable =
    loadedReviewable
    && !invalidExactEvidence
    && exactReview?.promotable !== false
    && !loadedWorldbuilding;
  const loadedReadOnly =
    Boolean(loadedRun)
    && !loadedPromotable
    && !exactRunFirstWorldEligible;
  const loadedInspectOnlyReason =
    loadedRun
    && loadedReadOnly
    && !exactRunFirstWorldEligible
    && (loadedReviewable || isCatalogRunHistoricalRecapInspectable(loadedRun))
      ? (
        exactRunNonPromotableReason
        ?? (
          loadedWorldbuilding
            ? "Worldbuilding ExtractionRuns are inspect-only until an approved authority-elevation contract lands."
            : "This ExtractionRun is inspect-only and cannot be prepared for World Graph merge."
        )
      )
      : null;
  const loadedRunSummary =
    loadedRun
      ? {
          extractionRunId: loadedRun.run_id,
          sourceDomain: loadedRun.source_domain,
          status: loadedRun.status,
          sourceArtifactId: loadedRun.source_artifact_id,
          profileId: loadedRun.profile_id ?? null,
          campaignId: loadedRun.campaign_id ?? null,
          sessionId: loadedRun.session_id ?? null,
          documentId: exactLineage?.documentId ?? null,
          revision: exactLineage?.revision ?? null,
          reviewable: loadedReviewable,
          promotable: loadedPromotable,
          readOnly: loadedReadOnly,
          worldId: historicalRecapProjection?.worldId ?? null,
          graphId: historicalRecapProjection?.graphId ?? null,
          inspectOnlyReason: loadedInspectOnlyReason,
        }
      : null;

  const runRecapQuoteCorrection = useCallback(async (corrections: ExactRunEvidenceQuoteCorrection[], retry = false) => {
    const key = recapQuoteScope(exactRun, exactReview, managedWorldId);
    if (!key || !exactRun || !exactReview || !exactRunMatchesHandoff
      || exactRunStatus !== "ready" || recapFlight.current?.key === key) return;
    const storageKey = "dmb:recap-quote-correction:v1:" + key;
    const generation = operationScopeRef.current.generation;
    const token = Symbol("recap-quote-correction");
    const isCurrent = () => operationScopeRef.current.generation === generation
      && recapFlight.current?.token === token;
    let capsule: RecapQuoteRecovery;
    try {
      const saved = window.sessionStorage.getItem(storageKey);
      if (retry) {
        if (!saved) throw new Error("No saved correction request is available.");
        capsule = JSON.parse(saved) as RecapQuoteRecovery;
        if (capsule.version !== 1 || capsule.key !== key || typeof capsule.id !== "string") throw new Error("The saved correction request is invalid. Abandon it explicitly before starting again.");
      } else {
        if (saved) throw new Error("Verify or abandon the saved request before submitting different changes.");
        capsule = { version: 1, key, id: crypto.randomUUID(), request: {
          parentRunId: exactRun.run_id,
          parentCandidateSha256: quoteDigest(exactRun.components?.candidate_graph?.sha256)!,
          corrections: JSON.parse(JSON.stringify(corrections)) as ExactRunEvidenceQuoteCorrection[],
        } };
      }
      if (capsule.request.parentRunId !== exactRun.run_id
        || capsule.request.parentCandidateSha256 !== quoteDigest(exactRun.components?.candidate_graph?.sha256)
        || !Array.isArray(capsule.request.corrections) || capsule.request.corrections.length === 0) throw new Error("Saved quote changes do not match this exact candidate.");
      const targets = new Set<string>();
      for (const change of capsule.request.corrections) {
        if (!change || typeof change.originalQuote !== "string") throw new Error("The saved quote request is invalid.");
        const assertion = exactReview.assertions.find((item) => item.assertionId === change.assertionId);
        const evidence = assertion?.evidence[change.evidenceIndex];
        const target = JSON.stringify([change.assertionId, change.evidenceIndex, change.quoteIndex]);
        if (!Number.isInteger(change.evidenceIndex) || !Number.isInteger(change.quoteIndex)
          || change.evidenceIndex < 0 || change.quoteIndex < 0 || targets.has(target)
          || evidence?.sourceArtifactId !== exactRun.source_artifact_id
          || evidence?.sourceSpanRefId !== change.sourceSpanRefId
          || evidence?.anchorQuotes[change.quoteIndex] !== change.originalQuote
          || !evidence?.invalidAnchorQuotes?.includes(change.originalQuote)
          || typeof change.replacementQuote !== "string" || !change.replacementQuote.trim()
          || change.replacementQuote.trim() === change.originalQuote.trim()) throw new Error("Saved quote changes no longer match the frozen evidence.");
        targets.add(target);
      }
      const invalidCount = exactReview.assertions.reduce((count, assertion) => count
        + assertion.evidence.reduce((total, evidence) => total + evidence.anchorQuotes.filter((quote) => evidence.invalidAnchorQuotes?.includes(quote)).length, 0), 0);
      if (targets.size !== invalidCount) throw new Error("Every invalid quote needs an explicit replacement.");
      // Persist before POST. If this fails, do not create an unrecoverable child.
      window.sessionStorage.setItem(storageKey, JSON.stringify(capsule));
    } catch (error) {
      setExactCorrectionError(error instanceof Error ? error.message : "Could not preserve this correction request.");
      return;
    }
    recapFlight.current = { key, token };
    refreshRecapRecovery((value) => value + 1);
    setExactCorrectionError(null);
    try {
      const receipt = capsule.receipt ?? await correctRecapRunEvidence(capsule.request);
      // A retained receipt is untrusted until the same adapter identity checks
      // and exact child/source checks below have succeeded.
      if (receipt.schema !== "dmb_recap_evidence_correction_response_v1" || receipt.status !== "reviewable"
        || receipt.parentRunId !== capsule.request.parentRunId
        || receipt.parentCandidateSha256 !== capsule.request.parentCandidateSha256
        || typeof receipt.runId !== "string" || !receipt.runId.trim() || receipt.runId === exactRun.run_id
        || !["held", "accepted", "rejected"].includes(receipt.semanticState)
        || !quoteDigest(receipt.candidateSha256) || !quoteDigest(receipt.correctionDigest)
        || !quoteDigest(receipt.semanticBasisSha256)) throw new Error("The saved correction receipt does not match this request.");
      const currentSaved = JSON.parse(window.sessionStorage.getItem(storageKey) ?? "null") as RecapQuoteRecovery | null;
      if (currentSaved?.id === capsule.id) window.sessionStorage.setItem(storageKey, JSON.stringify({ ...capsule, receipt }));
      if (!isCurrent()) return;
      const [child, childReview] = await Promise.all([getExtractionRun(receipt.runId), getExactRunReviewPackage(receipt.runId)]);
      if (!isCurrent()) return;
      verifyRecapQuoteChild(exactRun, exactReview, receipt, child, childReview);
      window.sessionStorage.removeItem(storageKey);
      const url = new URL(window.location.href);
      url.searchParams.set("extractionRunId", child.run_id);
      window.history.replaceState(window.history.state, "", url);
      setExactPrepared(null);
      setInternalExactHandoff((current) => current ? { ...current, extractionRunId: child.run_id } : current);
      onLocationSearchChange?.(url.search);
    } catch (error) {
      if (isCurrent()) setExactCorrectionError(error instanceof Error ? error.message : "The correction outcome could not be verified. Retry the saved request deliberately.");
    } finally {
      if (recapFlight.current?.token === token) {
        recapFlight.current = null;
        refreshRecapRecovery((value) => value + 1);
      }
    }
  }, [exactRun, exactReview, exactRunMatchesHandoff, exactRunStatus, managedWorldId, onLocationSearchChange]);

  const onCorrectExactEvidence = useCallback(async (
    corrections: ExactRunEvidenceQuoteCorrection[],
  ) => {
    if (exactRun?.source_domain === "recap") { await runRecapQuoteCorrection(corrections); return; }
    if (effectiveSourceReviewOnly) return;
    const parentRunId = exactRun?.run_id;
    const parentCandidateSha256 = exactRun?.components?.candidate_graph?.sha256;
    if (!parentRunId || !parentCandidateSha256 || exactReview?.inspectionStatus !== "invalid_evidence") {
      setExactCorrectionError("Exact parent candidate identity is unavailable.");
      return;
    }
    const operationGeneration = operationScopeRef.current.generation;
    setExactCorrecting(true);
    setExactCorrectionError(null);
    try {
      const child = await correctExactRunEvidence({
        parentRunId,
        parentCandidateSha256,
        corrections,
      });
      if (child.parentRunId !== parentRunId || child.parentCandidateSha256 !== parentCandidateSha256) {
        throw new Error("Corrected child identity does not match the exact parent run.");
      }
      if (operationScopeRef.current.generation !== operationGeneration) return;
      const url = new URL(window.location.href);
      url.searchParams.set("extractionRunId", child.runId);
      window.history.replaceState(window.history.state, "", url);
      onLocationSearchChange?.(url.search);
      setExactPrepared(null);
      setInternalExactHandoff((current) => current ? { ...current, extractionRunId: child.runId } : current);
    } catch (error) {
      if (operationScopeRef.current.generation !== operationGeneration) return;
      setExactCorrectionError(
        error instanceof Error ? error.message : "Could not create a reviewed child candidate.",
      );
    } finally {
      if (operationScopeRef.current.generation === operationGeneration) {
        setExactCorrecting(false);
      }
    }
  }, [exactRun, exactReview, effectiveSourceReviewOnly, onLocationSearchChange, runRecapQuoteCorrection]);

  const onPrepareExactRun = useCallback(async () => {
    if (effectiveSourceReviewOnly) return;
    const runId = exactHandoff?.extractionRunId ?? exactRun?.run_id;
    if (!runId || !managedWorldId || !exactRunPromotable || exactPreparing || exactConfirmInFlight) return;
    const operationGeneration = operationScopeRef.current.generation;
    setExactPreparing(true);
    setExactPrepareError(null);
    try {
      const response = await prepareExtractPromote({ runId, managedWorldId });
      if (
        operationScopeRef.current.generation !== operationGeneration
        || managedWorldIdRef.current !== managedWorldId
      ) return;
      setExactPrepared(response);
    } catch (error) {
      if (
        operationScopeRef.current.generation !== operationGeneration
        || managedWorldIdRef.current !== managedWorldId
      ) return;
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
          runId,
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
      if (
        operationScopeRef.current.generation === operationGeneration
        && managedWorldIdRef.current === managedWorldId
      ) {
        setExactPreparing(false);
      }
    }
  }, [exactConfirmInFlight, exactHandoff?.extractionRunId, exactPreparing, exactRun?.run_id, exactRunPromotable, effectiveSourceReviewOnly, managedWorldId]);

  useEffect(() => {
    setExactPrepared(null);
    setExactPrepareError(null);
    setExactPreparing(false);
    setExactCorrecting(false);
    setExactCorrectionError(null);
  }, [operationScopeKey]);

  const hasExactRunLoad = Boolean(
    exactHandoff
    && exactRunStatus === "ready"
    && exactRun
    && exactRun.run_id === exactHandoff.extractionRunId
  );
  const writeAuthority = resolveGraphReviewWriteAuthority({
    exactHandoff,
    exactHandoffErrors,
    exactRun,
    exactRunStatus,
  });
  const effectiveWriteAuthority = effectiveSourceReviewOnly ? null : writeAuthority;
  // Keep live-state (and the Tools drawer) mounted even before a session is loaded so
  // Diagnostics remains reachable from the empty /ingest landing state.
  // Exact campaignless runs must not inherit applied/draft/context campaign lenses.
  const exactRunCampaignId = hasExactRunLoad
    ? (exactRun?.campaign_id ?? "").trim()
    : null;
  const reviewCampaignId =
    effectiveWriteAuthority?.kind === "exact_run"
      ? (effectiveWriteAuthority.campaignId ?? "")
      : browseContext.campaignId;
  // Exact worldbuilding runs keep session null — never invent a session lens.
  // A rejected or unresolved handoff must not degrade into browse while write
  // controls remain mounted.
  const reviewSessionId =
    effectiveWriteAuthority?.kind === "exact_run"
      ? effectiveWriteAuthority.sessionId ?? ""
      : browseContext.sessionId;

  const committedBinding = useMemo<GraphReviewCommittedBinding | null>(() => {
    if (effectiveWriteAuthority?.kind !== "exact_run" || !exactRun?.run_id) return null;
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
  }, [
    exactHandoff?.sourceArtifactId,
    exactRun?.campaign_id,
    exactRun?.run_id,
    exactRun?.session_id,
    exactRun?.source_artifact_id,
    exactRunCampaignId,
    effectiveWriteAuthority,
  ]);

  const showPublishedMemoryBrowse = !exactHandoff;

  return (
    <GraphReviewLiveStateProvider
        campaignId={reviewCampaignId}
        sessionId={reviewSessionId}
        liveRun={null}
        committedBinding={committedBinding}
        hasGold={false}
        compare={null}
        compareStatus="idle"
        compareError={null}
        goldLane={null}
        liveLane={null}
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
        <div
          className="graph-review-workbench-root"
          data-testid="graph-review-workbench"
          data-write-authority={effectiveWriteAuthority?.kind ?? "none"}
          data-browse-campaign={browseContext.campaignId}
          data-browse-session={browseContext.sessionId}
        >
          <GraphReviewWorkbenchHeader
            exactRun={hasExactRunLoad ? loadedRunSummary : null}
          />

          {exactRunError ? (
            <p className="graph-review-error" data-testid="graph-review-exact-run-error">
              {exactRunError}
            </p>
          ) : null}
          {exactRunStatus === "loading" ? (
            <p className="plan-projection-empty">Loading exact extraction run…</p>
          ) : null}

          {showPublishedMemoryBrowse ? (
            <RecapGraphModule context={context} />
          ) : hasExactRunLoad ? (
            <GraphReviewExactRunBranch
              exactRun={exactRun!}
              exactReview={exactReview}
              exactReviewStatus={exactReviewStatus}
              exactReviewError={exactReviewError}
              historicalRecapProjection={historicalRecapProjection}
              historicalRecapProjectionStatus={historicalRecapProjectionStatus}
              historicalRecapProjectionError={historicalRecapProjectionError}
              exactRunReviewable={exactRunReviewable}
              exactRunPromotable={exactRunPromotable}
              exactRunFirstWorldEligible={exactRunFirstWorldEligible}
              sourceReviewOnly={effectiveSourceReviewOnly}
              exactRunNonPromotableReason={exactRunNonPromotableReason}
              exactPreparing={exactPreparing}
              exactConfirmInFlight={exactConfirmInFlight}
              exactPrepareError={exactPrepareError}
              selectedWorldGuidance={targetGuidance}
              exactPrepared={effectiveSourceReviewOnly ? null : exactPrepared}
              exactCorrecting={exactCorrecting || recapCorrectionPending}
              recapCorrection={Boolean(recapQuoteKey)}
              recapRecoveryAvailable={recapRecoveryAvailable}
              recapRecoveryChanges={recapRecovery?.request.corrections}
              onRetryCorrection={() => { void runRecapQuoteCorrection([], true); }}
              onAbandonCorrection={() => {
                if (!recapStorageKey || recapCorrectionPending) return;
                try { window.sessionStorage.removeItem(recapStorageKey); setExactCorrectionError(null); refreshRecapRecovery((value) => value + 1); }
                catch { setExactCorrectionError("The saved request could not be cleared."); }
              }}
              exactCorrectionError={exactCorrectionError}
              onCorrectEvidence={(corrections) => { void onCorrectExactEvidence(corrections); }}
              onPrepare={() => {
                void onPrepareExactRun();
              }}
              onClosePrepared={() => setExactPrepared(null)}
              onConfirmInFlightChange={setExactConfirmInFlight}
              onCatalogRefresh={onCatalogRefresh}
            />
          ) : null}
        </div>
      </GraphReviewLiveStateProvider>
  );
}

function GraphReviewExactRunBranch(props: {
  exactRun: ExtractionRunRecord;
  exactReview: ExactRunReviewPackage | null;
  exactReviewStatus: "idle" | "loading" | "ready" | "error";
  exactReviewError: string | null;
  historicalRecapProjection: HistoricalRecapWorldProjectionResponse | null;
  historicalRecapProjectionStatus: "idle" | "loading" | "ready" | "error";
  historicalRecapProjectionError: string | null;
  exactRunReviewable: boolean;
  exactRunPromotable: boolean;
  exactRunFirstWorldEligible: boolean;
  sourceReviewOnly: boolean;
  exactRunNonPromotableReason: string | null;
  exactPreparing: boolean;
  exactConfirmInFlight: boolean;
  exactPrepareError: string | null;
  selectedWorldGuidance: string | null;
  exactPrepared: ExtractPromotePrepareResponse | null;
  exactCorrecting: boolean;
  recapCorrection: boolean;
  recapRecoveryAvailable: boolean;
  recapRecoveryChanges?: ExactRunEvidenceQuoteCorrection[];
  onRetryCorrection: () => void;
  onAbandonCorrection: () => void;
  exactCorrectionError: string | null;
  onCorrectEvidence: (corrections: ExactRunEvidenceQuoteCorrection[]) => void;
  onPrepare: () => void;
  onClosePrepared: () => void;
  onConfirmInFlightChange: (inFlight: boolean) => void;
  onCatalogRefresh: () => void | Promise<void>;
}) {
  const { committedPhase } = useGraphReviewLiveState();
  const historicalRecapInspectable = isCatalogRunHistoricalRecapInspectable(props.exactRun);

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
      {props.exactReviewStatus === "loading" ? (
        <p className="plan-projection-empty">Loading source evidence…</p>
      ) : null}
      {props.historicalRecapProjectionStatus === "loading" ? (
        <p className="plan-projection-empty">Loading historical World projection…</p>
      ) : null}
      {props.exactReviewError ? (
        <p className="graph-review-error" data-testid="graph-review-exact-run-review-error">
          {props.exactReviewError}
        </p>
      ) : null}
      {props.historicalRecapProjectionError ? (
        <p
          className="graph-review-error"
          data-testid="graph-review-historical-recap-error"
        >
          {props.historicalRecapProjectionError}
        </p>
      ) : null}
      {props.exactRun.source_domain === "recap" && props.exactRun.lineage?.derivation === "operator_recap_literal_evidence_correction_v1" ? (
        <p role="status">Quotes saved in a separate candidate. Semantic review state: {String((props.exactRun.lineage.semantic_disposition as Record<string, unknown> | undefined)?.state ?? "unverified")}. World acceptance remains separate.</p>
      ) : null}
      {props.exactReview ? (
        <GraphReviewExactRunProjection
          key={JSON.stringify([props.exactRun.run_id, props.exactRun.components])}
          review={props.exactReview}
          recapCorrection={props.recapCorrection}
          recoveryPending={props.recapRecoveryAvailable}
          correctionRecoveryAvailable={props.recapRecoveryAvailable}
          recoveryChanges={props.recapRecoveryChanges}
          onRetryCorrection={props.onRetryCorrection}
          onAbandonCorrection={props.onAbandonCorrection}
          correctionEnabled={props.recapCorrection || (props.exactRun.source_domain === "worldbuilding"
            && !props.sourceReviewOnly
            && props.exactRun.profile_id === "worldbuilding_shepherds_flock_v0@0.1"
            && Boolean(props.exactRun.components?.candidate_graph?.sha256)
            && props.exactReview.inspectionStatus === "invalid_evidence")}
          correctionPending={props.exactCorrecting}
          correctionError={props.exactCorrectionError}
          onCorrectEvidence={props.onCorrectEvidence}
        />
      ) : null}
      {historicalRecapInspectable && props.historicalRecapProjection
        ? (
          <GraphReviewHistoricalRecapProjection projection={props.historicalRecapProjection} />
        )
        : null}
      {historicalRecapInspectable
      && props.historicalRecapProjectionStatus === "error" ? (
        <p data-testid="graph-review-historical-recap-unavailable">
          Historical graph projection for this exact run is unavailable:{" "}
          {props.historicalRecapProjectionError ?? "the governed source or World authority is unavailable."}
        </p>
      ) : null}
      {!props.exactRunReviewable && !historicalRecapInspectable ? (
        <p data-testid="graph-review-exact-run-unreviewable">
          {isCatalogRunPromotedHistory(props.exactRun)
            ? (
              <>
                Run status is <code>promoted</code>: visible terminal history only. Exact
                review is unavailable through the current resolver (SI-5B stop/rebrief —
                requires a separate inspection seam).
              </>
            )
            : (
              <>
                Run status is <code>{props.exactRun.status}</code> and is not reviewable for
                promotion.
              </>
            )}
        </p>
      ) : !props.sourceReviewOnly && props.exactRunFirstWorldEligible && props.exactReview ? (
        props.exactReviewStatus === "error" ? null : (
          <GraphReviewFirstWorldPublishSheet
            review={props.exactReview}
            onConfirmInFlightChange={props.onConfirmInFlightChange}
            onCatalogRefresh={props.onCatalogRefresh}
          />
        )
      ) : props.sourceReviewOnly || !props.exactRunPromotable ? null : props.exactReviewStatus === "error" ? null : (
        <GraphReviewExactRunPromoteChrome
          exactPreparing={props.exactPreparing}
          exactConfirmInFlight={props.exactConfirmInFlight}
          exactReviewReady={props.exactReviewStatus === "ready" && Boolean(props.exactReview)}
          exactPrepareError={props.exactPrepareError}
          selectedWorldGuidance={props.selectedWorldGuidance}
          onPrepare={props.onPrepare}
        />
      )}
      {!props.sourceReviewOnly && props.exactPrepared ? (
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
  selectedWorldGuidance: string | null;
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
          !props.exactReviewReady ||
          Boolean(props.selectedWorldGuidance)
        }
        title={props.selectedWorldGuidance ?? undefined}
        onClick={props.onPrepare}
      >
        {props.exactPreparing ? "Preparing…" : "Review & merge"}
      </button>
      {props.selectedWorldGuidance ? (
        <p
          className="module-muted"
          data-testid="graph-review-selected-world-guidance"
          role="status"
        >
          {props.selectedWorldGuidance}
        </p>
      ) : null}
      {props.exactPrepareError ? (
        <p className="graph-review-error">{props.exactPrepareError}</p>
      ) : null}
    </div>
  );
}
