import type {
  ArtifactReadResponse,
  CapabilityReadResponse,
  LiveEventsResponse,
  LiveJobsResponse,
  PlanViewProjection,
  ProjectionCommand,
  ProjectionWriteResult,
  ProjectionTarget,
  CitationSourceRequest,
  CitationSourceResponse,
  CitationFreshnessRequest,
  CitationFreshnessResponse,
  LiveQueryResponse,
  LiveQueryBackend,
  LiveQueryOptions,
  LiveSurfaceResponse,
  AddGeneratedStatblockCombatRequest,
  AddGeneratedStatblockCombatResponse,
  CombatEncounterState,
  CombatEntityPatchRequest,
  CombatHpDeltaRequest,
  CombatMutationResponse,
  CombatSavesListResponse,
  CombatSaveSlotResponse,
  CombatSetActiveRequest,
  CombatTurnRequest,
  LoadCombatSaveRequest,
  NewCombatEncounterRequest,
  SaveCurrentCombatRequest,
  GeneratedStatblockDetailResponse,
  GeneratedStatblockListResponse,
  IngestionSourceBundle,
  ResolvedRollResponse,
  SurfaceLayout,
  ListStatblockDraftsResponse,
  ReadStatblockDraftResponse,
  StatblockCorpusPromotionPreviewRequest,
  StatblockCorpusPromotionPreviewResponse,
  StatblockCorpusWriteCommitRequest,
  StatblockCorpusWriteCommitResponse,
  StatblockCorpusWritePrepareRequest,
  StatblockCorpusWritePrepareResponse,
  StatblockRetrievalActivationResponse,
  StatblockRetrievalVerifyRequest,
  StatblockRetrievalVerifyResponse,
  StoreStatblockDraftRequest,
  StoreStatblockDraftResponse,
  StatblockWorkbenchCommandRequest,
  StatblockWorkbenchCommandResponse,
  StatblockWorkbenchSampleResponse,
  TiptapMarkdownWriteCommitRequest,
  TiptapMarkdownWriteCommitResponse,
  TiptapMarkdownWritePrepareRequest,
  TiptapMarkdownWritePrepareResponse,
  ExtractionRunLaunchRequest,
  ExtractionRunLaunchResponse,
  ExtractionRunRecord,
  ExtractionRunStatusResponse,
  WorkspaceDocumentRecord,
  WorkspaceDocumentsListResponse,
  WorkspaceDocumentSnapshot,
  CreateWorkspaceDocumentRequest,
  UpdateWorkspaceDocumentMetadataRequest,
  WorkspaceDocumentRevisionRequest,
  GraphPreviewSurfaceResponse,
  GraphPreviewRunsResponse,
  GraphIngestLatestRunResponse,
  GraphIngestRunsResponse,
  GoldGraphProjectionResponse,
  GraphReviewExistingObjectResolverRequest,
  GraphReviewExistingObjectResolverResponse,
  GraphGoldAuthoringPrepareRequest,
  GraphGoldAuthoringPrepareResponse,
  GraphGoldAuthoringCommitRequest,
  GraphGoldAuthoringCommitResponse,
  GraphGoldAuthoringVerifyCommitRequest,
  GraphGoldAuthoringVerifyCommitResponse,
  GraphObjectAuthoringCommitRequest,
  GraphObjectAuthoringCommitResponse,
  GraphMergeReconciliationApplyRequest,
  GraphMergeReconciliationApplyResponse,
  GraphMergeReconciliationPrepareRequest,
  GraphMergeReconciliationPrepareResponse,
  GraphObjectAuthoringPrepareRequest,
  GraphObjectAuthoringPrepareResponse,
  GoldReviewCompareResponse,
  GoldReviewEvidenceDiffResponse,
  GoldReviewSessionsResponse,
  VocabularyAblationDogfoodResponse,
  ManualReviewBedDetail,
  ManualReviewBedsResponse,
  RecapArtifactsListResponse,
  RecapGraphPresentationResponse,
  RecapGraphQuery,
  UnionSupergraphProjectionResponse,
  WorldGraphProjection,
  WorldGraphProjectionRequest,
  WorldGraphSourceAnchorReadRequest,
  WorldGraphSourceAnchorReadResponse,
  PartyRegistrySurfaceResponse,
  PartyRegistrySessionRosterWriteCommitRequest,
  PartyRegistrySessionRosterWriteCommitResponse,
  PartyRegistrySessionRosterWritePrepareRequest,
  PartyRegistrySessionRosterWritePrepareResponse,
  GenerateThreatDraftCandidateRequestV1,
  GenerateThreatDraftCandidateResponseV1,
  ReadStatblockCandidateResponseV1,
  ValidateDefinitionBuddyRequestV1,
  ValidateDefinitionBuddyResponseV1,
  StatblockIntegrationReadinessV1,
} from "./types";
import { normalizeHermesOutboundConversationHistory } from "../agentInteraction/hermesConversationHistory";

const baseUrl = (import.meta.env.VITE_LIVE_API_BASE_URL as string | undefined) ?? "";
const defaultUnionSupergraphPreviewSource =
  (import.meta.env.VITE_UNION_SUPERGRAPH_PREVIEW_SOURCE as string | undefined)?.trim() ||
  "s22-anchor-quote-n3-s23-gold";

/** Repo-relative path passed to POST /api/live/query for context_lookup grounding. */
export const DEFAULT_PLANNING_MANIFEST_PATH =
  (import.meta.env.VITE_LIVE_PLANNING_MANIFEST_PATH as string | undefined)?.trim() ||
  "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json";

function htmlInsteadOfJsonHint(): string {
  return (
    "The API returned an HTML page instead of JSON. Usually the L3 server is not running, " +
    "or the UI is not proxying /api to it. Terminal 1 (repo root): " +
    "export DUNGEONMIND_LIVE_SESSION_DIR=evals/c2_live_prep/live/session_22 && " +
    "uv run uvicorn apps.live_control_server.main:app --reload. " +
    "Terminal 2: cd apps/live-control-ui && npm run dev (use dev, not preview)."
  );
}

async function parseJsonBody<T>(response: Response): Promise<T> {
  const text = await response.text();
  const trimmed = text.trimStart();
  if (trimmed.startsWith("<!") || trimmed.toLowerCase().startsWith("<html")) {
    throw new Error(htmlInsteadOfJsonHint());
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(
      `API response is not valid JSON (HTTP ${response.status}). ${htmlInsteadOfJsonHint()}`,
    );
  }
}

export interface LiveApiErrorDiagnostic {
  code: string;
  message: string;
  severity?: string;
}

export interface LiveApiErrorOptions {
  code?: string | null;
  diagnostics?: LiveApiErrorDiagnostic[] | null;
}

export class LiveApiError extends Error {
  public readonly code?: string | null;
  public readonly diagnostics?: LiveApiErrorDiagnostic[] | null;

  constructor(
    message: string,
    public readonly status: number,
    options?: LiveApiErrorOptions,
  ) {
    super(message);
    this.name = "LiveApiError";
    this.code = options?.code ?? null;
    this.diagnostics = options?.diagnostics ?? null;
  }
}

function parseWorldGraphErrorFields(body: {
  schema?: unknown;
  code?: unknown;
  message?: unknown;
  diagnostics?: unknown;
}): Pick<LiveApiErrorOptions, "code" | "diagnostics"> {
  const isWorldGraphError =
    body.schema === "dmb_world_graph_projection_error_v1"
    || (typeof body.code === "string" && typeof body.message === "string");

  if (!isWorldGraphError) {
    return { code: null, diagnostics: null };
  }

  const code = typeof body.code === "string" ? body.code : null;
  const diagnostics = Array.isArray(body.diagnostics)
    ? body.diagnostics
        .filter(
          (entry): entry is LiveApiErrorDiagnostic =>
            typeof entry === "object"
            && entry != null
            && typeof (entry as LiveApiErrorDiagnostic).code === "string"
            && typeof (entry as LiveApiErrorDiagnostic).message === "string",
        )
        .map((entry) => ({
          code: entry.code,
          message: entry.message,
          severity: typeof entry.severity === "string" ? entry.severity : undefined,
        }))
    : null;

  return { code, diagnostics };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    let errorOptions: LiveApiErrorOptions | undefined;
    try {
      const body = await parseJsonBody<{
        detail?: unknown;
        message?: unknown;
        schema?: unknown;
        code?: unknown;
        diagnostics?: unknown;
      }>(response);
      if (typeof body.message === "string") {
        detail = body.message;
      } else if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail != null) {
        detail = JSON.stringify(body.detail);
      }
      errorOptions = parseWorldGraphErrorFields(body);
    } catch (parseError) {
      if (parseError instanceof Error) {
        detail = parseError.message;
      }
    }
    throw new LiveApiError(detail, response.status, errorOptions);
  }
  return parseJsonBody<T>(response);
}

export async function getSurface(): Promise<LiveSurfaceResponse> {
  return apiFetch<LiveSurfaceResponse>("/api/live/surface");
}

export async function getEvents(since?: string): Promise<LiveEventsResponse> {
  const query = since ? `?since=${encodeURIComponent(since)}` : "";
  return apiFetch<LiveEventsResponse>(`/api/live/events${query}`);
}

export async function getJobs(): Promise<LiveJobsResponse> {
  return apiFetch<LiveJobsResponse>("/api/live/jobs");
}

export async function getPlanView(): Promise<PlanViewProjection> {
  return apiFetch<PlanViewProjection>("/api/live/plan-view");
}

export async function getPartyRegistry(
  campaignId: string,
  session: number,
): Promise<PartyRegistrySurfaceResponse> {
  const params = new URLSearchParams({
    campaign_id: campaignId,
    session: String(session),
  });
  return apiFetch<PartyRegistrySurfaceResponse>(`/api/live/party-registry?${params.toString()}`);
}

export async function preparePartyRegistrySessionRosterWrite(
  body: PartyRegistrySessionRosterWritePrepareRequest,
): Promise<PartyRegistrySessionRosterWritePrepareResponse> {
  return apiFetch<PartyRegistrySessionRosterWritePrepareResponse>(
    "/api/live/party-registry/session-roster/prepare",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

export async function commitPartyRegistrySessionRosterWrite(
  body: PartyRegistrySessionRosterWriteCommitRequest,
): Promise<PartyRegistrySessionRosterWriteCommitResponse> {
  return apiFetch<PartyRegistrySessionRosterWriteCommitResponse>(
    "/api/live/party-registry/session-roster/commit",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

function recapGraphQueryString(query?: RecapGraphQuery): string {
  if (!query) {
    return "";
  }
  const params = new URLSearchParams();
  if (query.run_dir) params.set("run_dir", query.run_dir);
  if (query.artifact_id) params.set("artifact_id", query.artifact_id);
  if (query.campaign_id) params.set("campaign_id", query.campaign_id);
  if (query.session_id) params.set("session_id", query.session_id);
  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
}

export async function getRecapArtifacts(campaignId?: string): Promise<RecapArtifactsListResponse> {
  const query = campaignId ? `?campaign_id=${encodeURIComponent(campaignId)}` : "";
  return apiFetch<RecapArtifactsListResponse>(`/api/live/graph-preview/artifacts${query}`);
}

export async function getGraphPreviewLatest(
  runDir?: string,
  query?: Omit<RecapGraphQuery, "run_dir">,
): Promise<GraphPreviewSurfaceResponse> {
  const params = new URLSearchParams();
  if (runDir) params.set("run_dir", runDir);
  if (query?.artifact_id) params.set("artifact_id", query.artifact_id);
  if (query?.campaign_id) params.set("campaign_id", query.campaign_id);
  if (query?.session_id) params.set("session_id", query.session_id);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<GraphPreviewSurfaceResponse>(`/api/live/graph-preview/latest${suffix}`);
}

export async function getGraphPreviewRuns(query?: RecapGraphQuery): Promise<GraphPreviewRunsResponse> {
  return apiFetch<GraphPreviewRunsResponse>(`/api/live/graph-preview/runs${recapGraphQueryString(query)}`);
}

export async function getRecapGraphPresentation(
  query?: RecapGraphQuery,
): Promise<RecapGraphPresentationResponse> {
  return apiFetch<RecapGraphPresentationResponse>(
    `/api/live/graph-preview/recap${recapGraphQueryString(query)}`,
  );
}

export interface GraphIngestRunsQuery {
  campaignId?: string;
  sessionId?: string;
  sourceRecapPath?: string;
  sourceRecapSha256?: string;
  status?: string;
  requirePreviewUnionStore?: boolean;
}

export async function getGraphIngestRuns(query: GraphIngestRunsQuery = {}): Promise<GraphIngestRunsResponse> {
  const params = new URLSearchParams();
  if (query.campaignId) params.set("campaign_id", query.campaignId);
  if (query.sessionId) params.set("session_id", query.sessionId);
  if (query.sourceRecapPath) params.set("source_recap_path", query.sourceRecapPath);
  if (query.sourceRecapSha256) params.set("source_recap_sha256", query.sourceRecapSha256);
  if (query.status) params.set("status", query.status);
  if (query.requirePreviewUnionStore != null) {
    params.set("require_preview_union_store", String(query.requirePreviewUnionStore));
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<GraphIngestRunsResponse>(`/api/live/graph-preview/graph-ingest/runs${suffix}`);
}

export async function getLatestGraphIngestRun(
  campaignId: string,
  sessionId: string,
  sourceRecapPath?: string,
  sourceRecapSha256?: string,
): Promise<GraphIngestLatestRunResponse> {
  const params = new URLSearchParams({ campaign_id: campaignId, session_id: sessionId });
  if (sourceRecapPath) params.set("source_recap_path", sourceRecapPath);
  if (sourceRecapSha256) params.set("source_recap_sha256", sourceRecapSha256);
  return apiFetch<GraphIngestLatestRunResponse>(
    `/api/live/graph-preview/graph-ingest/latest?${params.toString()}`,
  );
}

export interface GoldReviewCompareQuery {
  campaignId: string;
  sessionId: string;
  manifestPath?: string;
}

export async function getGoldReviewSessions(): Promise<GoldReviewSessionsResponse> {
  return apiFetch<GoldReviewSessionsResponse>("/api/live/graph-preview/gold-review/sessions");
}

export async function getGoldReviewCompare(query: GoldReviewCompareQuery): Promise<GoldReviewCompareResponse> {
  const params = new URLSearchParams({
    campaign_id: query.campaignId,
    session_id: query.sessionId,
  });
  if (query.manifestPath) params.set("manifest_path", query.manifestPath);
  return apiFetch<GoldReviewCompareResponse>(
    `/api/live/graph-preview/gold-review/compare?${params.toString()}`,
  );
}

export interface GoldReviewEvidenceQuery extends GoldReviewCompareQuery {
  objectKind: string;
  objectId: string;
}

export async function getGoldReviewEvidence(
  query: GoldReviewEvidenceQuery,
): Promise<GoldReviewEvidenceDiffResponse> {
  const params = new URLSearchParams({
    campaign_id: query.campaignId,
    session_id: query.sessionId,
    object_kind: query.objectKind,
    object_id: query.objectId,
  });
  if (query.manifestPath) params.set("manifest_path", query.manifestPath);
  return apiFetch<GoldReviewEvidenceDiffResponse>(
    `/api/live/graph-preview/gold-review/evidence?${params.toString()}`,
  );
}

export interface GoldReviewVocabularyAblationQuery {
  campaignId: string;
  sessionId: string;
}

export async function getGoldReviewVocabularyAblation(
  query: GoldReviewVocabularyAblationQuery,
): Promise<VocabularyAblationDogfoodResponse> {
  const params = new URLSearchParams({
    campaign_id: query.campaignId,
    session_id: query.sessionId,
  });
  return apiFetch<VocabularyAblationDogfoodResponse>(
    `/api/live/graph-preview/gold-review/vocabulary-ablation?${params.toString()}`,
  );
}

export async function getManualReviewBeds(): Promise<ManualReviewBedsResponse> {
  return apiFetch<ManualReviewBedsResponse>("/api/live/graph-preview/manual-review/beds");
}

export async function getManualReviewBed(bedId: string): Promise<ManualReviewBedDetail> {
  return apiFetch<ManualReviewBedDetail>(
    `/api/live/graph-preview/manual-review/beds/${encodeURIComponent(bedId)}`,
  );
}

export interface UnionSupergraphProjectionQuery {
  sessionId: string;
  campaignId?: string;
  previewSource?: string | null;
  graphRunManifestPath?: string | null;
  previewUnionStorePath?: string | null;
  useLatestGraphIngest?: boolean;
  allowRecapOnly?: boolean;
  sourceRecapPath?: string | null;
  sourceRecapSha256?: string | null;
}

export async function getUnionSupergraphProjection(
  query: UnionSupergraphProjectionQuery,
): Promise<UnionSupergraphProjectionResponse>;
export async function getUnionSupergraphProjection(
  sessionId: string,
  previewSource?: string,
): Promise<UnionSupergraphProjectionResponse>;
export async function getUnionSupergraphProjection(
  queryOrSessionId: UnionSupergraphProjectionQuery | string,
  previewSource = defaultUnionSupergraphPreviewSource,
): Promise<UnionSupergraphProjectionResponse> {
  const query = typeof queryOrSessionId === "string"
    ? { sessionId: queryOrSessionId, previewSource }
    : queryOrSessionId;
  const params = new URLSearchParams({ session_id: query.sessionId });
  if (query.campaignId) params.set("campaign_id", query.campaignId);
  if (query.useLatestGraphIngest) params.set("use_latest_graph_ingest", "true");
  if (query.allowRecapOnly) params.set("allow_recap_only", "true");
  if (query.previewSource) params.set("preview_source", query.previewSource);
  if (query.graphRunManifestPath) params.set("graph_run_manifest_path", query.graphRunManifestPath);
  if (query.previewUnionStorePath) params.set("preview_union_store_path", query.previewUnionStorePath);
  if (query.sourceRecapPath) params.set("source_recap_path", query.sourceRecapPath);
  if (query.sourceRecapSha256) params.set("source_recap_sha256", query.sourceRecapSha256);
  return apiFetch<UnionSupergraphProjectionResponse>(
    `/api/live/graph-preview/union-supergraph/projection?${params.toString()}`,
  );
}

export async function postWorldGraphProjection(
  request: WorldGraphProjectionRequest,
): Promise<WorldGraphProjection> {
  return apiFetch<WorldGraphProjection>("/api/live/world-graph/projection", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getDefaultUnionSupergraphProjection(
  sessionId: string,
  previewSource = defaultUnionSupergraphPreviewSource,
): Promise<UnionSupergraphProjectionResponse> {
  return getUnionSupergraphProjection({ sessionId, previewSource });
}

export async function resolveGraphReviewExistingObjectCandidates(
  request: GraphReviewExistingObjectResolverRequest,
): Promise<GraphReviewExistingObjectResolverResponse> {
  return apiFetch<GraphReviewExistingObjectResolverResponse>(
    "/api/live/graph-preview/existing-object-resolver/candidates",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export interface GoldGraphProjectionQuery {
  campaignId: string;
  sessionId: string;
}

export async function prepareGraphGoldAuthoringPreview(
  request: GraphGoldAuthoringPrepareRequest,
): Promise<GraphGoldAuthoringPrepareResponse> {
  return apiFetch<GraphGoldAuthoringPrepareResponse>(
    "/api/live/graph-preview/gold-authoring/prepare",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function commitGraphGoldAuthoringPreview(
  request: GraphGoldAuthoringCommitRequest,
): Promise<GraphGoldAuthoringCommitResponse> {
  return apiFetch<GraphGoldAuthoringCommitResponse>(
    "/api/live/graph-preview/gold-authoring/commit",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function verifyGraphGoldAuthoringCommit(
  request: GraphGoldAuthoringVerifyCommitRequest,
): Promise<GraphGoldAuthoringVerifyCommitResponse> {
  return apiFetch<GraphGoldAuthoringVerifyCommitResponse>(
    "/api/live/graph-preview/gold-authoring/verify-commit",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function prepareGraphObjectAuthoringWrite(
  request: GraphObjectAuthoringPrepareRequest,
): Promise<GraphObjectAuthoringPrepareResponse> {
  return apiFetch<GraphObjectAuthoringPrepareResponse>(
    "/api/live/graph-authoring/prepare",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function commitGraphObjectAuthoringWrite(
  request: GraphObjectAuthoringCommitRequest,
): Promise<GraphObjectAuthoringCommitResponse> {
  return apiFetch<GraphObjectAuthoringCommitResponse>(
    "/api/live/graph-authoring/commit",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function prepareGraphMergeReconciliationMaterialization(
  request: GraphMergeReconciliationPrepareRequest,
): Promise<GraphMergeReconciliationPrepareResponse> {
  return apiFetch<GraphMergeReconciliationPrepareResponse>(
    "/api/live/graph-authoring/merge-reconciliation/prepare",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function applyGraphMergeReconciliationMaterialization(
  request: GraphMergeReconciliationApplyRequest,
): Promise<GraphMergeReconciliationApplyResponse> {
  return apiFetch<GraphMergeReconciliationApplyResponse>(
    "/api/live/graph-authoring/merge-reconciliation/apply",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function getGoldGraphProjection(
  query: GoldGraphProjectionQuery,
): Promise<GoldGraphProjectionResponse> {
  const params = new URLSearchParams({
    campaign_id: query.campaignId,
    session_id: query.sessionId,
  });
  return apiFetch<GoldGraphProjectionResponse>(
    `/api/live/graph-preview/gold-review/projection?${params.toString()}`,
  );
}

export async function getSourceBundle(
  scope = "campaign-ingested",
  campaignId?: string,
): Promise<IngestionSourceBundle> {
  const query = new URLSearchParams({ scope });
  if (campaignId) query.set("campaign_id", campaignId);
  return apiFetch<IngestionSourceBundle>(`/api/live/source-bundle?${query.toString()}`);
}

export async function getArtifact(
  target: Pick<ProjectionTarget, "target_type" | "target_id">,
): Promise<ArtifactReadResponse> {
  const query = new URLSearchParams({
    target_type: target.target_type,
    target_id: target.target_id,
  });
  return apiFetch<ArtifactReadResponse>(`/api/live/artifact?${query.toString()}`);
}

export async function getCapabilities(
  target: Pick<ProjectionTarget, "target_type" | "target_id">,
): Promise<CapabilityReadResponse> {
  const query = new URLSearchParams({
    target_type: target.target_type,
    target_id: target.target_id,
  });
  return apiFetch<CapabilityReadResponse>(`/api/live/capabilities?${query.toString()}`);
}

export async function postCommand(command: ProjectionCommand): Promise<ProjectionWriteResult> {
  return apiFetch<ProjectionWriteResult>("/api/live/commands", {
    method: "POST",
    body: JSON.stringify(command),
  });
}

export async function postCitationSource(
  request: CitationSourceRequest,
): Promise<CitationSourceResponse> {
  return apiFetch<CitationSourceResponse>("/api/live/citation-source", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function postCitationFreshness(
  request: CitationFreshnessRequest,
): Promise<CitationFreshnessResponse> {
  return apiFetch<CitationFreshnessResponse>("/api/live/citation-freshness", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function postWorldGraphSourceAnchorRead(
  request: WorldGraphSourceAnchorReadRequest,
): Promise<WorldGraphSourceAnchorReadResponse> {
  return apiFetch<WorldGraphSourceAnchorReadResponse>(
    "/api/live/world-graph/retrieval/source-anchor/read",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

export async function postLiveQuery(
  text: string,
  campaignId: string,
  session: number,
  queryBackend: LiveQueryBackend = "live",
  options: LiveQueryOptions = {},
): Promise<LiveQueryResponse> {
  if (queryBackend === "hermes") {
    const normalizedHistory = normalizeHermesOutboundConversationHistory(
      options.conversationHistory,
    );
    const body: Record<string, unknown> = {
      campaign_id: campaignId,
      session,
      mode: "live",
      query_backend: "hermes",
      text,
      agent_thread_id: options.agentThreadId ?? null,
      trace_requested: options.traceRequested ?? null,
      ...(options.hermesSessionPointer
        ? { hermes_session_pointer: options.hermesSessionPointer }
        : {}),
      ...(options.worldGraphContext != null
        ? { world_graph_context: options.worldGraphContext }
        : {}),
      ...(normalizedHistory.length > 0
        ? { conversation_history: normalizedHistory }
        : {}),
    };
    return apiFetch<LiveQueryResponse>("/api/live/query", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  const body = {
    campaign_id: campaignId,
    session,
    mode: "live",
    query_backend: queryBackend,
    text,
    manifest_path: DEFAULT_PLANNING_MANIFEST_PATH,
    agent_thread_id: options.agentThreadId ?? null,
    hermes_session_id: options.hermesSessionId ?? null,
    trace_requested: options.traceRequested ?? null,
    world_graph_context: options.worldGraphContext ?? undefined,
  };

  return apiFetch<LiveQueryResponse>("/api/live/query", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function putSurfaceLayout(
  layout: SurfaceLayout,
): Promise<{ layout: SurfaceLayout }> {
  return apiFetch<{ layout: SurfaceLayout }>("/api/live/surface/layout", {
    method: "PUT",
    body: JSON.stringify(layout),
  });
}

export async function resolveRoll(command: string): Promise<ResolvedRollResponse> {
  return apiFetch<ResolvedRollResponse>("/api/live/resolve-roll", {
    method: "POST",
    body: JSON.stringify({ command }),
  });
}

export async function completeJob(jobId: string): Promise<{ job: import("./types").LiveJob }> {
  return apiFetch(`/api/live/jobs/${encodeURIComponent(jobId)}/complete`, {
    method: "POST",
  });
}

export async function rebuildPacket(): Promise<{
  job_id: string;
  status: string;
  job: import("./types").LiveJob;
}> {
  return apiFetch("/api/live/rebuild-packet", { method: "POST" });
}

export async function getStatblockWorkbenchSample(): Promise<StatblockWorkbenchSampleResponse> {
  return apiFetch<StatblockWorkbenchSampleResponse>(
    "/api/live/statblocks/workbench/sample",
  );
}

export async function getStatblockIntegrationReadiness(): Promise<StatblockIntegrationReadinessV1> {
  return apiFetch<StatblockIntegrationReadinessV1>("/api/live/statblocks/v1/readiness");
}

export async function generateThreatDraftCandidate(
  draftId: string,
  request: GenerateThreatDraftCandidateRequestV1,
): Promise<GenerateThreatDraftCandidateResponseV1> {
  return apiFetch<GenerateThreatDraftCandidateResponseV1>(
    `/api/live/threat-drafts/${encodeURIComponent(draftId)}/candidates:generate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export async function getStatblockCandidate(
  candidateId: string,
): Promise<ReadStatblockCandidateResponseV1> {
  return apiFetch<ReadStatblockCandidateResponseV1>(
    `/api/live/statblock-candidates/${encodeURIComponent(candidateId)}`,
  );
}

export async function validateStatblockDefinition(
  request: ValidateDefinitionBuddyRequestV1,
): Promise<ValidateDefinitionBuddyResponseV1> {
  return apiFetch<ValidateDefinitionBuddyResponseV1>(
    "/api/live/statblock-definitions:validate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export async function postStatblockWorkbenchCommand(
  request: StatblockWorkbenchCommandRequest,
): Promise<StatblockWorkbenchCommandResponse> {
  return apiFetch<StatblockWorkbenchCommandResponse>(
    "/api/live/statblocks/workbench/command",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export async function storeStatblockWorkbenchDraft(
  request: StoreStatblockDraftRequest,
): Promise<StoreStatblockDraftResponse> {
  return apiFetch<StoreStatblockDraftResponse>(
    "/api/live/statblocks/workbench/drafts",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export async function listStatblockWorkbenchDrafts(): Promise<ListStatblockDraftsResponse> {
  return apiFetch<ListStatblockDraftsResponse>(
    "/api/live/statblocks/workbench/drafts",
  );
}

export async function getStatblockWorkbenchDraft(
  artifactId: string,
): Promise<ReadStatblockDraftResponse> {
  return apiFetch<ReadStatblockDraftResponse>(
    `/api/live/statblocks/workbench/drafts/${encodeURIComponent(artifactId)}`,
  );
}

export async function listGeneratedStatblocks(): Promise<GeneratedStatblockListResponse> {
  return apiFetch<GeneratedStatblockListResponse>(
    "/api/live/statblocks/view/generated",
  );
}

export async function getGeneratedStatblock(
  artifactId: string,
): Promise<GeneratedStatblockDetailResponse> {
  return apiFetch<GeneratedStatblockDetailResponse>(
    `/api/live/statblocks/view/generated/${encodeURIComponent(artifactId)}`,
  );
}

export async function getCurrentCombat(): Promise<CombatEncounterState> {
  return apiFetch<CombatEncounterState>("/api/live/combat/current");
}

export async function addGeneratedStatblockToCombat(
  artifactId: string,
  request: AddGeneratedStatblockCombatRequest,
): Promise<AddGeneratedStatblockCombatResponse> {
  return apiFetch<AddGeneratedStatblockCombatResponse>(
    `/api/live/statblocks/view/generated/${encodeURIComponent(artifactId)}/combat/add`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export async function previewStatblockCorpusPromotion(
  artifactId: string,
  request: StatblockCorpusPromotionPreviewRequest = {},
): Promise<StatblockCorpusPromotionPreviewResponse> {
  return apiFetch<StatblockCorpusPromotionPreviewResponse>(
    `/api/live/statblocks/workbench/drafts/${encodeURIComponent(artifactId)}/corpus-preview`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export async function prepareStatblockCorpusWrite(
  artifactId: string,
  request: StatblockCorpusWritePrepareRequest = {},
): Promise<StatblockCorpusWritePrepareResponse> {
  return apiFetch<StatblockCorpusWritePrepareResponse>(
    `/api/live/statblocks/workbench/drafts/${encodeURIComponent(artifactId)}/corpus-write/prepare`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export async function commitStatblockCorpusWrite(
  artifactId: string,
  request: StatblockCorpusWriteCommitRequest,
): Promise<StatblockCorpusWriteCommitResponse> {
  return apiFetch<StatblockCorpusWriteCommitResponse>(
    `/api/live/statblocks/workbench/drafts/${encodeURIComponent(artifactId)}/corpus-write/commit`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export async function listWorkspaceDocuments(args: {
  campaign_id?: string;
  kind?: "plan" | "runbook" | "worldbuilding_source";
  status?: "active" | "discarded";
} = {}): Promise<WorkspaceDocumentsListResponse> {
  const params = new URLSearchParams();
  if (args.campaign_id) params.set("campaign_id", args.campaign_id);
  if (args.kind) params.set("kind", args.kind);
  if (args.status) params.set("status", args.status);
  const query = params.toString();
  return apiFetch<WorkspaceDocumentsListResponse>(
    `/api/live/workspace-documents${query ? `?${query}` : ""}`,
  );
}

export async function getWorkspaceDocument(documentId: string): Promise<WorkspaceDocumentRecord> {
  return apiFetch<WorkspaceDocumentRecord>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}`,
  );
}

export async function getWorkspaceDocumentSnapshot(documentId: string): Promise<WorkspaceDocumentSnapshot> {
  return apiFetch<WorkspaceDocumentSnapshot>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}/snapshot`,
  );
}

export async function createWorkspaceDocument(
  request: CreateWorkspaceDocumentRequest,
): Promise<WorkspaceDocumentRecord> {
  return apiFetch<WorkspaceDocumentRecord>(
    "/api/live/workspace-documents",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function updateWorkspaceDocumentMetadata(
  documentId: string,
  request: UpdateWorkspaceDocumentMetadataRequest,
): Promise<WorkspaceDocumentRecord> {
  return apiFetch<WorkspaceDocumentRecord>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}`,
    { method: "PATCH", body: JSON.stringify(request) },
  );
}

export async function discardWorkspaceDocument(
  documentId: string,
  request: WorkspaceDocumentRevisionRequest = {},
): Promise<WorkspaceDocumentRecord> {
  return apiFetch<WorkspaceDocumentRecord>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}/discard`,
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function restoreWorkspaceDocument(
  documentId: string,
  request: WorkspaceDocumentRevisionRequest = {},
): Promise<WorkspaceDocumentRecord> {
  return apiFetch<WorkspaceDocumentRecord>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}/restore`,
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function prepareTiptapMarkdownWrite(
  request: TiptapMarkdownWritePrepareRequest,
): Promise<TiptapMarkdownWritePrepareResponse> {
  return apiFetch<TiptapMarkdownWritePrepareResponse>(
    "/api/live/tiptap/markdown-write/prepare",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function commitTiptapMarkdownWrite(
  request: TiptapMarkdownWriteCommitRequest,
): Promise<TiptapMarkdownWriteCommitResponse> {
  return apiFetch<TiptapMarkdownWriteCommitResponse>(
    "/api/live/tiptap/markdown-write/commit",
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function launchExtractionRun(
  request: ExtractionRunLaunchRequest,
): Promise<ExtractionRunLaunchResponse> {
  return apiFetch<ExtractionRunLaunchResponse>(
    "/api/live/graph-preview/extraction-runs",
    { method: "POST", body: JSON.stringify(request) },
  );
}

/** Generic exact ExtractionRun reload (recap + worldbuilding). Never substitutes latest. */
export async function getExtractionRun(runId: string): Promise<ExtractionRunRecord> {
  return apiFetch<ExtractionRunRecord>(
    `/api/live/graph-preview/extraction-runs/${encodeURIComponent(runId)}`,
  );
}

/** Build-only workspace lineage envelope for an exact extraction run. */
export async function getExtractionRunStatus(runId: string): Promise<ExtractionRunStatusResponse> {
  return apiFetch<ExtractionRunStatusResponse>(
    `/api/live/graph-preview/extraction-runs/${encodeURIComponent(runId)}/build-context`,
  );
}

export async function activateStatblockRetrieval(
  artifactId: string,
): Promise<StatblockRetrievalActivationResponse> {
  return apiFetch<StatblockRetrievalActivationResponse>(
    `/api/live/statblocks/workbench/drafts/${encodeURIComponent(artifactId)}/retrieval/activate`,
    { method: "POST", body: JSON.stringify({}) },
  );
}

export async function verifyStatblockRetrieval(
  artifactId: string,
  request: StatblockRetrievalVerifyRequest = {},
): Promise<StatblockRetrievalVerifyResponse> {
  return apiFetch<StatblockRetrievalVerifyResponse>(
    `/api/live/statblocks/workbench/drafts/${encodeURIComponent(artifactId)}/retrieval/verify`,
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function patchCombatEntity(
  entityId: string,
  request: CombatEntityPatchRequest,
): Promise<CombatMutationResponse> {
  return apiFetch<CombatMutationResponse>(
    `/api/live/combat/current/entities/${encodeURIComponent(entityId)}`,
    { method: "PATCH", body: JSON.stringify(request) },
  );
}

export async function applyCombatHpDelta(
  entityId: string,
  request: CombatHpDeltaRequest,
): Promise<CombatMutationResponse> {
  return apiFetch<CombatMutationResponse>(
    `/api/live/combat/current/entities/${encodeURIComponent(entityId)}/hp-delta`,
    { method: "POST", body: JSON.stringify(request) },
  );
}

export async function sortCombatInitiative(): Promise<CombatMutationResponse> {
  return apiFetch<CombatMutationResponse>("/api/live/combat/current/sort-initiative", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function setCombatActiveTurn(
  request: CombatSetActiveRequest,
): Promise<CombatMutationResponse> {
  return apiFetch<CombatMutationResponse>("/api/live/combat/current/active-turn", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function advanceCombatTurn(
  request: CombatTurnRequest = { direction: "next" },
): Promise<CombatMutationResponse> {
  return apiFetch<CombatMutationResponse>("/api/live/combat/current/turn", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function listCombatSaves(): Promise<CombatSavesListResponse> {
  return apiFetch<CombatSavesListResponse>("/api/live/combat/saves");
}

export async function loadCombatSave(
  request: LoadCombatSaveRequest,
): Promise<CombatSaveSlotResponse> {
  return apiFetch<CombatSaveSlotResponse>("/api/live/combat/current/load", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function unloadCurrentCombat(): Promise<CombatSaveSlotResponse> {
  return apiFetch<CombatSaveSlotResponse>("/api/live/combat/current/unload", {
    method: "POST",
  });
}

export async function newCombatEncounter(
  request: NewCombatEncounterRequest = {},
): Promise<CombatSaveSlotResponse> {
  return apiFetch<CombatSaveSlotResponse>("/api/live/combat/current/new", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function saveCurrentCombatAs(
  request: SaveCurrentCombatRequest,
): Promise<CombatSaveSlotResponse> {
  return apiFetch<CombatSaveSlotResponse>("/api/live/combat/saves", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
