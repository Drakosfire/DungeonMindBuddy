import type {
  ArtifactReadResponse,
  CapabilityReadResponse,
  LiveEventsResponse,
  LiveJobsResponse,
  PlanViewProjection,
  ManagedWorldPlanContextV2,
  ProjectionCommand,
  ProjectionWriteResult,
  ProjectionTarget,
  CitationSourceRequest,
  CitationSourceResponse,
  CitationFreshnessRequest,
  CitationFreshnessResponse,
  LiveQueryResponse,
  IndexAgentTurnRequestV1,
  IndexAgentTurnResponseV1,
  WorldPlanAgentTurnRequestV1,
  WorldPlanAgentTurnResponse,
  WorldPlanGraphContextFailureV1,
  WorldAgentConversationHistoryResponse,
  WorldAgentNewConversationRequestV1,
  WorldAgentNewConversationResponseV1,
  WorldAgentNewConversationStatusV1,
  LiveQueryBackend,
  LiveQueryOptions,
  PlanDocumentEditProposalRequest,
  PlanDocumentEditProposalResponse,
  WorldPlanDocumentEditProposalRequest,
  WorldPlanDocumentEditProposalResponse,
  WorldPlanActionProjectionPage,
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
  HistoricalRecapInspectionResponse,
  HistoricalRecapWorldProjectionResponse,
  WorkspaceDocumentRecord,
  WorkspaceDocumentsListResponse,
  WorkspaceDocumentSnapshot,
  NativeWorldSourceAdmissionStatus,
  WorkspaceCommittedRevision,
  WorldOwnedCommittedRevisionV2,
  WorldOwnedRunbookCommittedRevisionV2,
  PlayActiveRunState,
  WorldPlayActiveRunStateV2,
  PlayRunRecord,
  WorldPlayRunRecordV2,
  WorldPlayRunsListResponseV2,
  PlayRunsListResponse,
  PlayRunReferenceManifest,
  CreatePlayRunRequest,
  ReplacePlayRunProgressRequest,
  RebasePlayRunRequest,
  CreateWorkspaceDocumentRequest,
  UpdateWorkspaceDocumentMetadataRequest,
  WorkspaceDocumentRevisionRequest,
  WorldContainerRecord,
  WorldContainersListResponse,
  CreateWorldContainerRequest,
  WorldOwnedPlansResponseV2,
  WorldOwnedPlanRecordV2,
  WorldOwnedPlanSnapshotV2,
  WorldOwnedPlanMarkdownWriteCommitResponseV2,
  WorldOwnedRunbookRecordV2,
  WorldOwnedRunbooksResponseV2,
  WorldOwnedRunbookSnapshotV2,
  WorldOwnedRunbookMarkdownWriteCommitResponseV2,
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
  ManagedWorldGraphProjectionRequest,
  ManagedWorldGraphProjectionResponse,
  WorldGraphObjectProjectionRequest,
  WorldGraphObjectProjectionResult,
  WorldGraphRecapProjection,
  WorldGraphSourceAnchorReadRequest,
  WorldGraphSourceAnchorReadResponse,
  PartyRegistrySurfaceResponse,
  PartyRegistrySessionRosterWriteCommitRequest,
  PartyRegistrySessionRosterWriteCommitResponse,
  PartyRegistrySessionRosterWritePrepareRequest,
  PartyRegistrySessionRosterWritePrepareResponse,
  CreateThreatDraftRequest,
  GenerateThreatDraftCandidateRequestV1,
  GenerateThreatDraftCandidateResponseV1,
  ThreatDraft,
  ReviseCandidateFromEditedDefinitionRequestV1,
  ReviseCandidateFromEditedDefinitionResponseV1,
  WorldGraphBootstrapStatusV1,
  ReadStatblockCandidateResponseV1,
  ValidateDefinitionBuddyRequestV1,
  ValidateDefinitionBuddyResponseV1,
  AcceptThreatDraftMechanicsRequestV1,
  AcceptThreatDraftMechanicsResponseV1,
  BuildSourceNavigationResponse,
  BeginThreatPublicationOperationRequestV1,
  CancelThreatPublicationOperationRequestV1,
  ConfirmThreatPublicationRequestV1,
  CreateThreatIdentityResolutionRequestV1,
  PrepareThreatIdentityCandidatesRequestV1,
  PrepareThreatPublicationProposalRequestV1,
  ReadAcceptanceOperationResponseV1,
  RetryThreatPublicationOperationRequestV1,
  ThreatPublicationCommitResponseV1,
  ThreatPublicationIdentityResponseV1,
  ThreatPublicationOperationResponseV1,
  ThreatPublicationProposalResponseV1,
  StatblockIntegrationReadinessV1,
  ThreatQueryHydrationRequestV1,
  ThreatQueryHydrationResponseV1,
} from "./types";
import { normalizeHermesOutboundConversationHistory } from "../agentInteraction/hermesConversationHistory";
import { withProjectionRequestCache } from "../planSurface/reference/projectionRequestCache";

const baseUrl = (import.meta.env.VITE_LIVE_API_BASE_URL as string | undefined) ?? "";
let nativeGraphAccessToken: string | null = null;
let nativeGraphCsrf: string | null = null;
let nativeGraphSessionRequest: Promise<string> | null = null;
let nativeGraphRevocationRequest: Promise<void> | null = null;
let nativeGraphSessionRevoked = false;
let nativeGraphSessionEpoch = 0;
let nativeGraphSessionRecovery: {
  fromEpoch: number;
  connectedEpoch: number | null;
  request: Promise<string>;
} | null = null;
export const NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT = "dmb:native-graph-access-token-changed";

function localGraphSessionTarget(): string {
  if (baseUrl) throw new LiveApiError("Local Graph sessions require the same-origin /api proxy.", 0);
  if (!isLoopbackApiDestination("/api/live/agent/local-session")) {
    throw new LiveApiError("Local Graph sessions require a loopback UI origin.", 0);
  }
  return "/api/live/agent/local-session";
}

async function graphSessionFetch(method: "GET" | "POST" | "DELETE", csrf?: string): Promise<Response> {
  return fetch(localGraphSessionTarget(), {
    method, credentials: "same-origin", redirect: "error", cache: "no-store",
    headers: csrf ? { "X-DMB-Graph-CSRF": csrf } : undefined,
  });
}

export async function ensureNativeGraphSession(): Promise<string> {
  if (nativeGraphSessionRevoked) throw new LiveApiError("Local Graph session was revoked. Reconnect explicitly.", 401);
  if (nativeGraphCsrf) return nativeGraphCsrf;
  if (!nativeGraphSessionRequest) {
    const epoch = nativeGraphSessionEpoch;
    const request = (async () => {
      let response = await graphSessionFetch("GET");
      if (response.status === 401) {
        if (epoch !== nativeGraphSessionEpoch || nativeGraphSessionRevoked) {
          throw new LiveApiError("Local Graph session changed. Reconnect explicitly.", 401);
        }
        response = await graphSessionFetch("POST");
      }
      if (!response.ok) throw new LiveApiError("Local Graph session is unavailable.", response.status);
      const body = await response.json() as { status?: unknown; csrf_token?: unknown };
      if (body.status !== "active" || typeof body.csrf_token !== "string" || !body.csrf_token) {
        throw new LiveApiError("Local Graph session response is invalid.", response.status);
      }
      if (epoch !== nativeGraphSessionEpoch || nativeGraphSessionRevoked) {
        throw new LiveApiError("Local Graph session changed. Reconnect explicitly.", 401);
      }
      nativeGraphCsrf = body.csrf_token;
      if (typeof window !== "undefined") window.dispatchEvent(new Event(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT));
      return body.csrf_token;
    })();
    nativeGraphSessionRequest = request;
    void request.then(
      () => { if (nativeGraphSessionRequest === request) nativeGraphSessionRequest = null; },
      () => { if (nativeGraphSessionRequest === request) nativeGraphSessionRequest = null; },
    );
  }
  return nativeGraphSessionRequest;
}

export async function connectNativeGraphSession(): Promise<string> {
  if (nativeGraphRevocationRequest) await nativeGraphRevocationRequest.catch(() => undefined);
  if (nativeGraphSessionRequest) await nativeGraphSessionRequest.catch(() => undefined);
  nativeGraphSessionEpoch += 1;
  nativeGraphCsrf = null;
  nativeGraphSessionRevoked = false;
  return ensureNativeGraphSession();
}

export function revokeNativeGraphSession(): Promise<void> {
  if (!nativeGraphRevocationRequest) {
    const cachedCsrf = nativeGraphCsrf;
    nativeGraphSessionEpoch += 1;
    nativeGraphSessionRevoked = true;
    nativeGraphCsrf = null;
    const request = (async () => {
      if (nativeGraphSessionRequest) await nativeGraphSessionRequest.catch(() => undefined);
      let csrf = cachedCsrf;
      if (!csrf) {
        const status = await graphSessionFetch("GET");
        if (!status.ok) throw new LiveApiError("Local Graph session could not be revoked.", status.status);
        const body = await status.json() as { csrf_token?: unknown };
        if (typeof body.csrf_token !== "string" || !body.csrf_token) {
          throw new LiveApiError("Local Graph session response is invalid.", status.status);
        }
        csrf = body.csrf_token;
      }
      const response = await graphSessionFetch("DELETE", csrf);
      if (!response.ok) throw new LiveApiError("Local Graph session could not be revoked.", response.status);
      if (typeof window !== "undefined") window.dispatchEvent(new Event(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT));
    })();
    nativeGraphRevocationRequest = request;
    void request.then(
      () => { if (nativeGraphRevocationRequest === request) nativeGraphRevocationRequest = null; },
      () => { if (nativeGraphRevocationRequest === request) nativeGraphRevocationRequest = null; },
    );
  }
  return nativeGraphRevocationRequest;
}

function blockStaleNativeGraphSession(status: number, usedCsrf: string | null, requestEpoch: number): void {
  if (!usedCsrf || requestEpoch !== nativeGraphSessionEpoch || (status !== 401 && status !== 403)) return;
  nativeGraphSessionEpoch += 1;
  nativeGraphCsrf = null;
  nativeGraphSessionRevoked = true;
  if (typeof window !== "undefined") window.dispatchEvent(new Event(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT));
}

/** Keep the local operator credential in this module's memory only. */
export function setNativeGraphAccessToken(token: string | null): void {
  const normalized = token?.trim() ?? "";
  const changed = normalized !== (nativeGraphAccessToken ?? "");
  nativeGraphAccessToken = normalized || null;
  if (!nativeGraphAccessToken) nativeGraphCsrf = null;
  if (changed && typeof window !== "undefined") {
    window.dispatchEvent(new Event(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT));
  }
}

function requestBodyRecord(body: BodyInit | null | undefined): Record<string, unknown> | null {
  if (typeof body !== "string") return null;
  try {
    const parsed: unknown = JSON.parse(body);
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
      ? parsed as Record<string, unknown>
      : null;
  } catch {
    return null;
  }
}

function requiresNativeGraphAuthorization(path: string, body: BodyInit | null | undefined): boolean {
  const pathname = path.split("?", 1)[0];
  if (/^\/api\/live\/threat-drafts\/[^/]+\/publication-operations\/[^/]+\/identity-candidates\/prepare$/.test(pathname)) {
    return true;
  }
  if (/^\/api\/live\/agent\/worlds\/[^/]+\/conversation(?:\/new|\/commands\/[^/]+)?$/.test(pathname)
    || pathname === "/api/live/agent/turn"
    || pathname === "/api/live/world-graph/projection"
    || pathname === "/api/live/world-graph/managed-projection"
    || pathname === "/api/live/world-graph/recap-projection"
    || pathname.startsWith("/api/live/world-graph/retrieval/")
    || pathname === "/api/live/threats/query-hydration") return true;

  const payload = requestBodyRecord(body);
  return pathname === "/api/live/query" && payload?.world_graph_context != null;
}

function isLoopbackApiDestination(requestUrl: string): boolean {
  let destination: URL;
  try {
    const pageUrl = typeof window === "undefined" ? undefined : window.location.href;
    destination = pageUrl ? new URL(requestUrl, pageUrl) : new URL(requestUrl);
  } catch {
    return false;
  }

  if (destination.protocol !== "http:" && destination.protocol !== "https:") return false;
  const hostname = destination.hostname.replace(/^\[|\]$/g, "").toLowerCase();
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

function apiRequestTarget(
  path: string,
  body: BodyInit | null | undefined,
): { url: string; localGraphRequest: boolean } {
  const url = `${baseUrl}${path}`;
  const localGraphRequest = requiresNativeGraphAuthorization(path, body);
  if (localGraphRequest && !isLoopbackApiDestination(url)) {
    throw new LiveApiError(
      "Local operator Agent/Graph requests are blocked unless the configured API destination is loopback.",
      0,
    );
  }
  return { url, localGraphRequest };
}

function headerRecord(headers: HeadersInit | undefined): Record<string, string> {
  if (!headers) return {};
  if (headers instanceof Headers) return Object.fromEntries(headers.entries());
  if (Array.isArray(headers)) return Object.fromEntries(headers);
  return { ...headers };
}

function nativeGraphHeaders(
  path: string,
  body: BodyInit | null | undefined,
  headers: Record<string, string>,
): Record<string, string> {
  if (!requiresNativeGraphAuthorization(path, body)) return headers;
  for (const key of Object.keys(headers)) {
    if (key.toLowerCase() === "authorization") delete headers[key];
  }
  if (nativeGraphAccessToken) {
    headers.Authorization = `Bearer ${nativeGraphAccessToken}`;
  }
  return headers;
}
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
  planContextFailure?: WorldPlanGraphContextFailureV1 | null;
}

export class LiveApiError extends Error {
  public readonly code?: string | null;
  public readonly diagnostics?: LiveApiErrorDiagnostic[] | null;
  public readonly planContextFailure?: WorldPlanGraphContextFailureV1 | null;

  constructor(
    message: string,
    public readonly status: number,
    options?: LiveApiErrorOptions,
  ) {
    super(message);
    this.name = "LiveApiError";
    this.code = options?.code ?? null;
    this.diagnostics = options?.diagnostics ?? null;
    this.planContextFailure = options?.planContextFailure ?? null;
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

const PLAN_GRAPH_PREDISPATCH_FAILURE_HTTP_STATUS: Readonly<Record<string, number>> = Object.freeze({
  managed_world_unresolved: 404,
  native_binding_invalid: 409,
  graph_revision_unavailable: 409,
  graph_read_failed: 503,
  graph_evidence_invalid: 502,
  provider_envelope_over_budget: 413,
  receipt_freeze_failed: 503,
});

export function isValidWorldPlanGraphContextFailure(
  value: unknown,
  responseCode: unknown,
  responseStatus: number,
): value is WorldPlanGraphContextFailureV1 {
  if (!isRecord(value)) return false;
  const expectedKeys = [
    "schema", "status", "failure_code", "provider_dispatched", "automatic_downgrade",
  ].sort();
  const actualKeys = Object.keys(value).sort();
  if (actualKeys.length !== expectedKeys.length
    || actualKeys.some((key, index) => key !== expectedKeys[index])
    || value.schema !== "dmb_plan_world_graph_context_failure_v1"
    || value.status !== "pre_dispatch_failed"
    || typeof value.failure_code !== "string" || !value.failure_code.trim()
    || value.provider_dispatched !== false
    || value.automatic_downgrade !== false) return false;

  const expectedStatus = PLAN_GRAPH_PREDISPATCH_FAILURE_HTTP_STATUS[value.failure_code];
  return typeof expectedStatus === "number"
    && responseCode === value.failure_code
    && responseStatus === expectedStatus;
}

function parsePlanWorldGraphContextFailure(
  body: unknown,
  responseStatus: number,
): WorldPlanGraphContextFailureV1 | null {
  if (!isRecord(body)) return null;
  const detail = isRecord(body.detail) ? body.detail : body;
  const failure = detail.plan_context_failure;
  return isValidWorldPlanGraphContextFailure(failure, detail.code, responseStatus)
    ? failure
    : null;
}


function canRetryLocalSessionRequest(path: string, init?: RequestInit): boolean {
  const method = (init?.method ?? "GET").toUpperCase();
  if (method === "GET" || method === "HEAD") return true;
  if (method !== "POST" || typeof init?.body !== "string") return false;
  const pathname = path.split("?", 1)[0];
  const body = requestBodyRecord(init.body);
  if (/^\/api\/live\/agent\/worlds\/[^/]+\/conversation\/new$/.test(pathname)) {
    return typeof body?.command_id === "string" && Boolean(body.command_id)
      && Number.isSafeInteger(body.expected_pointer_revision)
      && (body.expected_active_conversation_id === null || typeof body.expected_active_conversation_id === "string");
  }
  if (pathname === "/api/live/agent/turn") {
    return typeof body?.client_thread_id === "string" && Boolean(body.client_thread_id)
      && typeof body.turn_id === "string" && Boolean(body.turn_id);
  }
  return pathname === "/api/live/world-graph/projection"
    || pathname === "/api/live/world-graph/managed-projection"
    || pathname === "/api/live/world-graph/recap-projection"
    || ["search", "object", "complete-object", "neighborhood", "evidence", "source-anchor/read"]
      .some((read) => pathname === `/api/live/world-graph/retrieval/${read}`)
    || pathname === "/api/live/threats/query-hydration"
    || /^\/api\/live\/threat-drafts\/[^/]+\/publication-operations\/[^/]+\/identity-candidates\/prepare$/.test(pathname);
}

async function trustedLocalSessionRejection(response: Response): Promise<boolean> {
  if (response.status !== 401 && response.status !== 403) return false;
  try {
    const body: unknown = await response.clone().json();
    if (!isRecord(body) || !isRecord(body.detail)) return false;
    return (response.status === 401 && body.detail.code === "graph_auth_required")
      || (response.status === 403 && body.detail.code === "graph_auth_csrf_rejected");
  } catch {
    return false;
  }
}

/** @internal Shared transport for API wrappers and transport-boundary verification. */
export async function authenticatedApiFetch(path: string, init?: RequestInit): Promise<{
  response: Response; csrf: string | null; requestEpoch: number;
}> {
  const target = apiRequestTarget(path, init?.body);
  // Keep immutable request bytes/CAS/correlation for the sole permitted retry.
  const frozenInit = { ...init, headers: headerRecord(init?.headers) };
  const dispatch = async (expectedEpoch?: number) => {
    const csrf = target.localGraphRequest && !nativeGraphAccessToken
      ? await ensureNativeGraphSession() : null;
    if (expectedEpoch !== undefined && (nativeGraphSessionEpoch !== expectedEpoch
      || nativeGraphSessionRevoked || nativeGraphAccessToken)) {
      throw new LiveApiError("Local session changed during recovery. Retry deliberately.", 401,
        { code: "local_graph_session_changed" });
    }
    const requestEpoch = nativeGraphSessionEpoch;
    const usedBearer = Boolean(nativeGraphAccessToken);
    const response = await fetch(target.url, {
      ...frozenInit,
      ...(target.localGraphRequest ? { redirect: "error" as const, credentials: "same-origin" as const } : {}),
      headers: nativeGraphHeaders(path, frozenInit.body, {
        "Content-Type": "application/json", ...frozenInit.headers,
        ...(csrf && (frozenInit.method ?? "GET").toUpperCase() !== "GET" ? { "X-DMB-Graph-CSRF": csrf } : {}),
      }),
    });
    return { response, csrf, requestEpoch, usedBearer };
  };
  const first = await dispatch();
  if (!target.localGraphRequest || baseUrl || !first.csrf || first.usedBearer
    || nativeGraphAccessToken || nativeGraphSessionRevoked || frozenInit.signal?.aborted
    || !await trustedLocalSessionRejection(first.response)) return first;

  let recovery = nativeGraphSessionRecovery;
  if (!recovery || recovery.fromEpoch !== first.requestEpoch
    || (recovery.connectedEpoch === null
      ? first.requestEpoch !== nativeGraphSessionEpoch
      : recovery.connectedEpoch !== nativeGraphSessionEpoch)) {
    if (first.requestEpoch !== nativeGraphSessionEpoch) return first;
    recovery = { fromEpoch: first.requestEpoch, connectedEpoch: null, request: Promise.resolve("") };
    const owned = recovery;
    owned.request = (async () => {
      if (nativeGraphSessionRequest) await nativeGraphSessionRequest.catch(() => undefined);
      if (nativeGraphSessionRevoked || nativeGraphAccessToken || nativeGraphSessionEpoch !== owned.fromEpoch) {
        throw new LiveApiError("Local session changed during recovery.", 401, { code: "local_graph_session_changed" });
      }
      nativeGraphSessionEpoch += 1;
      nativeGraphCsrf = null;
      owned.connectedEpoch = nativeGraphSessionEpoch;
      // Reuse the existing GET → bootstrap POST. Never clear explicit revocation.
      return ensureNativeGraphSession();
    })();
    nativeGraphSessionRecovery = owned;
  }
  try {
    await recovery.request;
  } catch (reason) {
    throw new LiveApiError("Local session recovery failed. Reconnect in Settings.",
      reason instanceof LiveApiError ? reason.status : 0, { code: "local_graph_session_recovery_failed" });
  }
  if (!canRetryLocalSessionRequest(path, frozenInit) || nativeGraphSessionRevoked || nativeGraphAccessToken
    || recovery.connectedEpoch !== nativeGraphSessionEpoch || frozenInit.signal?.aborted) return first;
  return dispatch(recovery.connectedEpoch ?? undefined);
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const { response, csrf, requestEpoch } = await authenticatedApiFetch(path, init);
  if (!response.ok) {
    blockStaleNativeGraphSession(response.status, csrf, requestEpoch);
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
        errorOptions = {
          ...parseWorldGraphErrorFields(body),
          planContextFailure: parsePlanWorldGraphContextFailure(body, response.status),
        };
      } else if (typeof body.detail === "string") {
        detail = body.detail;
        errorOptions = {
          ...parseWorldGraphErrorFields(body),
          planContextFailure: parsePlanWorldGraphContextFailure(body, response.status),
        };
      } else if (body.detail != null && typeof body.detail === "object") {
        const detailObj = body.detail as {
          code?: unknown;
          message?: unknown;
          schema?: unknown;
          diagnostics?: unknown;
        };
        if (typeof detailObj.message === "string") {
          detail = detailObj.message;
        } else {
          detail = JSON.stringify(body.detail);
        }
        errorOptions = {
          ...parseWorldGraphErrorFields({
            ...body,
            ...detailObj,
          }),
          planContextFailure: parsePlanWorldGraphContextFailure(body, response.status),
        };
        if (!errorOptions.code && typeof detailObj.code === "string") {
          errorOptions = { ...errorOptions, code: detailObj.code, diagnostics: null };
        }
      } else if (body.detail != null) {
        detail = JSON.stringify(body.detail);
        errorOptions = {
          ...parseWorldGraphErrorFields(body),
          planContextFailure: parsePlanWorldGraphContextFailure(body, response.status),
        };
      }
    } catch (parseError) {
      if (parseError instanceof Error) {
        detail = parseError.message;
      }
    }
    throw new LiveApiError(detail, response.status, errorOptions);
  }
  return parseJsonBody<T>(response);
}

/** Lifecycle statuses that may carry a typed publication envelope, including integrity (500). */
const PUBLICATION_TYPED_STATUSES = new Set([200, 201, 404, 409, 500, 503]);

const OPERATION_RESPONSE_SCHEMA = "dmb_threat_publication_operation_response_v1";
const IDENTITY_RESPONSE_SCHEMA = "dmb_threat_publication_identity_response_v1";
const PROPOSAL_RESPONSE_SCHEMA = "dmb_threat_publication_proposal_response_v1";
const COMMIT_RESPONSE_SCHEMA = "dmb_threat_publication_commit_response_v1";
const OPERATION_RECORD_SCHEMA = "dmb_threat_publication_operation_v1";
const RESOLUTION_RECORD_SCHEMA = "dmb_threat_publication_identity_resolution_v1";
const CANDIDATE_SET_SCHEMA = "dmb_threat_identity_candidate_set_v1";
const PROPOSAL_RECORD_SCHEMA = "dmb_threat_publication_proposal_v1";
const COMMIT_RECORD_SCHEMA = "dmb_threat_publication_commit_v1";

const OPERATION_RESULT_LABELS = new Set<string>([
  "publication_ready",
  "publication_stale",
  "publication_cancelled",
  "publication_superseded",
  "publication_busy",
  "publication_input_conflict",
  "publication_parent_mismatch",
  "publication_source_mismatch",
  "publication_history_full",
  "publication_not_found",
  "publication_draft_unavailable",
  "publication_graph_unavailable",
  "publication_storage_unavailable",
  "publication_integrity_failure",
  "publication_invalid_state",
]);

const IDENTITY_RESULT_LABELS = new Set<string>([
  "publication_identity_candidates_ready",
  "publication_identity_created_new",
  "publication_identity_connected_existing",
  "publication_identity_refused",
  "publication_identity_superseded",
  "publication_identity_operation_not_ready",
  "publication_identity_candidate_overflow",
  "publication_identity_candidate_set_changed",
  "publication_identity_review_required",
  "publication_identity_target_not_found",
  "publication_identity_target_invalid",
  "publication_identity_new_id_collision",
  "publication_identity_busy",
  "publication_identity_input_conflict",
  "publication_identity_history_full",
  "publication_identity_not_found",
  "publication_identity_graph_unavailable",
  "publication_identity_storage_unavailable",
  "publication_identity_integrity_failure",
]);

const PROPOSAL_RESULT_LABELS = new Set<string>([
  "publication_proposal_ready",
  "publication_proposal_superseded",
  "publication_proposal_identity_refused",
  "publication_proposal_operation_not_ready",
  "publication_proposal_resolution_not_active",
  "publication_proposal_predecessor_mismatch",
  "publication_proposal_parent_mismatch",
  "publication_proposal_typed_collision",
  "publication_proposal_busy",
  "publication_proposal_input_conflict",
  "publication_proposal_history_full",
  "publication_proposal_not_found",
  "publication_proposal_graph_unavailable",
  "publication_proposal_storage_unavailable",
  "publication_proposal_integrity_failure",
]);

const COMMIT_RESULT_LABELS = new Set<string>([
  "publication_commit_verified",
  "publication_commit_committed_unverified",
  "publication_commit_recovery_pending",
  "publication_commit_uncommitted",
  "publication_commit_outcome_ambiguous",
  "publication_commit_proposal_not_active",
  "publication_commit_proposal_incompatible",
  "publication_commit_operation_not_ready",
  "publication_commit_resolution_not_active",
  "publication_commit_predecessor_mismatch",
  "publication_commit_parent_mismatch",
  "publication_commit_busy",
  "publication_commit_input_conflict",
  "publication_commit_not_found",
  "publication_commit_graph_unavailable",
  "publication_commit_storage_unavailable",
  "publication_commit_integrity_failure",
]);

/** Labels that must carry their durable record (mirrors route success classes). */
const OPERATION_LABELS_REQUIRING_RECORD = new Set<string>([
  "publication_ready",
  "publication_stale",
  "publication_cancelled",
  "publication_superseded",
]);

const IDENTITY_LABELS_REQUIRING_RESOLUTION = new Set<string>([
  "publication_identity_created_new",
  "publication_identity_connected_existing",
  "publication_identity_refused",
  "publication_identity_superseded",
]);

const PROPOSAL_LABELS_REQUIRING_PROPOSAL = new Set<string>([
  "publication_proposal_ready",
  "publication_proposal_superseded",
]);

const COMMIT_LABELS_REQUIRING_COMMITTED_REVISION = new Set<string>([
  "publication_commit_verified",
  "publication_commit_committed_unverified",
]);

const COMMIT_LABELS_REQUIRING_COMMIT_RECORD = new Set<string>([
  "publication_commit_verified",
  "publication_commit_committed_unverified",
  "publication_commit_recovery_pending",
  "publication_commit_uncommitted",
  "publication_commit_outcome_ambiguous",
]);

const OPERATION_STATUS_BY_LABEL: Record<string, ReadonlySet<number>> = {
  publication_ready: new Set([200, 201]),
  publication_stale: new Set([200]),
  publication_cancelled: new Set([200]),
  publication_superseded: new Set([200]),
  publication_busy: new Set([409]),
  publication_input_conflict: new Set([409]),
  publication_parent_mismatch: new Set([409]),
  publication_source_mismatch: new Set([409]),
  publication_history_full: new Set([409]),
  publication_invalid_state: new Set([409]),
  publication_not_found: new Set([404]),
  publication_draft_unavailable: new Set([503]),
  publication_graph_unavailable: new Set([503]),
  publication_storage_unavailable: new Set([503]),
  publication_integrity_failure: new Set([500]),
};

const IDENTITY_STATUS_BY_LABEL: Record<string, ReadonlySet<number>> = {
  publication_identity_candidates_ready: new Set([200]),
  publication_identity_created_new: new Set([200, 201]),
  publication_identity_connected_existing: new Set([200, 201]),
  publication_identity_refused: new Set([200, 201]),
  publication_identity_superseded: new Set([200, 201]),
  publication_identity_operation_not_ready: new Set([409]),
  publication_identity_candidate_overflow: new Set([409]),
  publication_identity_candidate_set_changed: new Set([409]),
  publication_identity_review_required: new Set([409]),
  publication_identity_target_invalid: new Set([409]),
  publication_identity_new_id_collision: new Set([409]),
  publication_identity_busy: new Set([409]),
  publication_identity_input_conflict: new Set([409]),
  publication_identity_history_full: new Set([409]),
  publication_identity_not_found: new Set([404]),
  publication_identity_target_not_found: new Set([404]),
  publication_identity_graph_unavailable: new Set([503]),
  publication_identity_storage_unavailable: new Set([503]),
  publication_identity_integrity_failure: new Set([500]),
};

const PROPOSAL_STATUS_BY_LABEL: Record<string, ReadonlySet<number>> = {
  publication_proposal_ready: new Set([200, 201]),
  publication_proposal_superseded: new Set([200]),
  publication_proposal_identity_refused: new Set([409]),
  publication_proposal_operation_not_ready: new Set([409]),
  publication_proposal_resolution_not_active: new Set([409]),
  publication_proposal_predecessor_mismatch: new Set([409]),
  publication_proposal_parent_mismatch: new Set([409]),
  publication_proposal_typed_collision: new Set([409]),
  publication_proposal_busy: new Set([409]),
  publication_proposal_input_conflict: new Set([409]),
  publication_proposal_history_full: new Set([409]),
  publication_proposal_not_found: new Set([404]),
  publication_proposal_graph_unavailable: new Set([503]),
  publication_proposal_storage_unavailable: new Set([503]),
  publication_proposal_integrity_failure: new Set([500]),
};

const COMMIT_STATUS_BY_LABEL: Record<string, ReadonlySet<number>> = {
  publication_commit_verified: new Set([200, 201]),
  publication_commit_committed_unverified: new Set([200, 201]),
  publication_commit_recovery_pending: new Set([503]),
  publication_commit_uncommitted: new Set([409]),
  publication_commit_outcome_ambiguous: new Set([409]),
  publication_commit_proposal_not_active: new Set([409]),
  publication_commit_proposal_incompatible: new Set([409]),
  publication_commit_operation_not_ready: new Set([409]),
  publication_commit_resolution_not_active: new Set([409]),
  publication_commit_predecessor_mismatch: new Set([409]),
  publication_commit_parent_mismatch: new Set([409]),
  publication_commit_busy: new Set([409]),
  publication_commit_input_conflict: new Set([409]),
  publication_commit_not_found: new Set([404]),
  publication_commit_graph_unavailable: new Set([503]),
  publication_commit_storage_unavailable: new Set([503]),
  publication_commit_integrity_failure: new Set([500]),
};

function isRecord(body: unknown): body is Record<string, unknown> {
  return typeof body === "object" && body !== null && !Array.isArray(body);
}

function statusAllowsLabel(
  status: number,
  label: string,
  table: Record<string, ReadonlySet<number>>,
): boolean {
  const allowed = table[label];
  return allowed != null && allowed.has(status);
}

function isNonBlankString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isOperationRecord(value: unknown, draftId: string): boolean {
  if (!isRecord(value)) return false;
  if (value.schema !== OPERATION_RECORD_SCHEMA) return false;
  if (!isNonBlankString(value.operation_id)) return false;
  if (!isRecord(value.source_snapshot)) return false;
  if (value.source_snapshot.draft_id !== draftId) return false;
  if (!isNonBlankString(value.source_snapshot.draft_id)) return false;
  if (!isRecord(value.source_snapshot.accepted_mechanics_ref)) return false;
  const mechanics = value.source_snapshot.accepted_mechanics_ref;
  if (!isNonBlankString(mechanics.statblock_id) || !isNonBlankString(mechanics.revision_id)) {
    return false;
  }
  if (!isNonBlankString(mechanics.definition_digest)) return false;
  if (typeof mechanics.accepted_from_draft_version !== "number") return false;
  return true;
}

function isCandidateSetRecord(value: unknown, draftId: string, operationId: string): boolean {
  if (!isRecord(value)) return false;
  if (value.schema !== CANDIDATE_SET_SCHEMA) return false;
  if (value.draft_id !== draftId || value.operation_id !== operationId) return false;
  if (!Array.isArray(value.candidates)) return false;
  if (!isNonBlankString(value.candidate_set_digest)) return false;
  return true;
}

function isResolutionRecord(value: unknown, draftId: string, operationId: string): boolean {
  if (!isRecord(value)) return false;
  if (value.schema !== RESOLUTION_RECORD_SCHEMA) return false;
  if (!isNonBlankString(value.resolution_id)) return false;
  if (value.draft_id !== draftId || value.operation_id !== operationId) return false;
  if (!isCandidateSetRecord(value.candidate_set, draftId, operationId)) return false;
  return true;
}

function isProposalRecord(value: unknown, draftId: string, operationId: string): boolean {
  if (!isRecord(value)) return false;
  if (value.schema !== PROPOSAL_RECORD_SCHEMA) return false;
  if (!isNonBlankString(value.proposal_id)) return false;
  if (value.draft_id !== draftId || value.operation_id !== operationId) return false;
  if (!isNonBlankString(value.sealed_proposal_digest)) return false;
  if (!isNonBlankString(value.expected_parent_revision_id)) return false;
  if (!isRecord(value.effect_summary)) return false;
  return true;
}

function isCommitRecord(
  value: unknown,
  draftId: string,
  operationId: string,
  commitId: string,
  requireCommittedRevision: boolean,
): boolean {
  if (!isRecord(value)) return false;
  if (value.schema !== COMMIT_RECORD_SCHEMA) return false;
  if (value.commit_id !== commitId) return false;
  if (value.draft_id !== draftId || value.operation_id !== operationId) return false;
  if (!isNonBlankString(value.sealed_proposal_digest)) return false;
  if (requireCommittedRevision && !isNonBlankString(value.committed_revision_id)) return false;
  return true;
}

function validateOperationPublicationEnvelope(
  body: unknown,
  status: number,
): ThreatPublicationOperationResponseV1 | null {
  if (!isRecord(body)) return null;
  if (body.schema !== OPERATION_RESPONSE_SCHEMA) return null;
  if (typeof body.result_label !== "string" || !OPERATION_RESULT_LABELS.has(body.result_label)) {
    return null;
  }
  if (!statusAllowsLabel(status, body.result_label, OPERATION_STATUS_BY_LABEL)) return null;
  if (typeof body.draft_id !== "string") return null;

  const operation = body.operation;
  if (OPERATION_LABELS_REQUIRING_RECORD.has(body.result_label)) {
    if (!isOperationRecord(operation, body.draft_id)) return null;
  } else if (operation != null && operation !== undefined) {
    if (!isOperationRecord(operation, body.draft_id)) return null;
  }
  return body as unknown as ThreatPublicationOperationResponseV1;
}

function validateIdentityPublicationEnvelope(
  body: unknown,
  status: number,
): ThreatPublicationIdentityResponseV1 | null {
  if (!isRecord(body)) return null;
  if (body.schema !== IDENTITY_RESPONSE_SCHEMA) return null;
  if (typeof body.result_label !== "string" || !IDENTITY_RESULT_LABELS.has(body.result_label)) {
    return null;
  }
  if (!statusAllowsLabel(status, body.result_label, IDENTITY_STATUS_BY_LABEL)) return null;
  if (typeof body.draft_id !== "string" || typeof body.operation_id !== "string") return null;
  if (!("predecessor_usable" in body)) return null;

  if (body.result_label === "publication_identity_candidates_ready") {
    if (!isCandidateSetRecord(body.candidate_set, body.draft_id, body.operation_id)) return null;
  }
  if (IDENTITY_LABELS_REQUIRING_RESOLUTION.has(body.result_label)) {
    if (!isResolutionRecord(body.resolution, body.draft_id, body.operation_id)) return null;
  } else if (body.resolution != null && body.resolution !== undefined) {
    if (!isResolutionRecord(body.resolution, body.draft_id, body.operation_id)) return null;
  }
  if (body.candidate_set != null && body.candidate_set !== undefined) {
    if (!isCandidateSetRecord(body.candidate_set, body.draft_id, body.operation_id)) return null;
  }
  return body as unknown as ThreatPublicationIdentityResponseV1;
}

function validateProposalPublicationEnvelope(
  body: unknown,
  status: number,
): ThreatPublicationProposalResponseV1 | null {
  if (!isRecord(body)) return null;
  if (body.schema !== PROPOSAL_RESPONSE_SCHEMA) return null;
  if (typeof body.result_label !== "string" || !PROPOSAL_RESULT_LABELS.has(body.result_label)) {
    return null;
  }
  if (!statusAllowsLabel(status, body.result_label, PROPOSAL_STATUS_BY_LABEL)) return null;
  if (typeof body.draft_id !== "string" || typeof body.operation_id !== "string") return null;
  if (!("resolution_id" in body)) return null;

  if (PROPOSAL_LABELS_REQUIRING_PROPOSAL.has(body.result_label)) {
    if (!isProposalRecord(body.proposal, body.draft_id, body.operation_id)) return null;
  } else if (body.proposal != null && body.proposal !== undefined) {
    if (!isProposalRecord(body.proposal, body.draft_id, body.operation_id)) return null;
  }
  return body as unknown as ThreatPublicationProposalResponseV1;
}

function validateCommitPublicationEnvelope(
  body: unknown,
  status: number,
): ThreatPublicationCommitResponseV1 | null {
  if (!isRecord(body)) return null;
  if (body.schema !== COMMIT_RESPONSE_SCHEMA) return null;
  if (typeof body.result_label !== "string" || !COMMIT_RESULT_LABELS.has(body.result_label)) {
    return null;
  }
  if (!statusAllowsLabel(status, body.result_label, COMMIT_STATUS_BY_LABEL)) return null;
  if (
    typeof body.draft_id !== "string"
    || typeof body.operation_id !== "string"
    || typeof body.commit_id !== "string"
  ) {
    return null;
  }
  if (body.commit_admitted !== null && typeof body.commit_admitted !== "boolean") return null;
  if (typeof body.retry_allowed !== "boolean") return null;
  if (!("proposal_id" in body)) return null;
  if (
    body.commit_admitted !== null
    && body.commit_admitted !== (body.commit != null)
  ) {
    return null;
  }

  const requireRevision = COMMIT_LABELS_REQUIRING_COMMITTED_REVISION.has(body.result_label);
  if (COMMIT_LABELS_REQUIRING_COMMIT_RECORD.has(body.result_label) || requireRevision) {
    if (
      !isCommitRecord(
        body.commit,
        body.draft_id,
        body.operation_id,
        body.commit_id,
        requireRevision,
      )
    ) {
      return null;
    }
  } else if (body.commit != null && body.commit !== undefined) {
    if (
      !isCommitRecord(body.commit, body.draft_id, body.operation_id, body.commit_id, false)
    ) {
      return null;
    }
  }
  return body as unknown as ThreatPublicationCommitResponseV1;
}

async function publicationFetch<T extends { schema: string; result_label: string }>(
  path: string,
  init: RequestInit | undefined,
  validate: (body: unknown, status: number) => T | null,
): Promise<T> {
  const { response, csrf, requestEpoch } = await authenticatedApiFetch(path, init);
  blockStaleNativeGraphSession(response.status, csrf, requestEpoch);

  let body: unknown;
  try {
    body = await parseJsonBody<unknown>(response);
  } catch (parseError) {
    const message = parseError instanceof Error ? parseError.message : String(parseError);
    throw new LiveApiError(message, response.status);
  }

  if (PUBLICATION_TYPED_STATUSES.has(response.status)) {
    const validated = validate(body, response.status);
    if (validated) {
      return validated;
    }
    throw new LiveApiError(
      "Publication response failed schema, result_label, status, or record validation",
      response.status,
    );
  }

  let detail = response.statusText;
  if (isRecord(body)) {
    if (typeof body.message === "string") {
      detail = body.message;
    } else if (typeof body.detail === "string") {
      detail = body.detail;
    }
  }

  throw new LiveApiError(detail, response.status);
}

function threatPublicationOperationsPrefix(draftId: string): string {
  return `/api/live/threat-drafts/${encodeURIComponent(draftId)}/publication-operations`;
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

export async function getPlanView(worldId?: string | null): Promise<PlanViewProjection> {
  return apiFetch<PlanViewProjection>(
    worldId ? `/api/live/plan-view?world_id=${encodeURIComponent(worldId)}` : "/api/live/plan-view",
  );
}

export async function getManagedWorldPlanContext(worldId: string): Promise<ManagedWorldPlanContextV2> {
  const query = new URLSearchParams({ scope_mode: "world", world_id: worldId });
  return apiFetch<ManagedWorldPlanContextV2>(`/api/live/plan-view?${query.toString()}`);
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
  return withProjectionRequestCache("projection", request, () =>
    apiFetch<WorldGraphProjection>("/api/live/world-graph/projection", {
      method: "POST",
      body: JSON.stringify(request),
    }),
  );
}

export async function postManagedWorldGraphProjection(
  request: ManagedWorldGraphProjectionRequest,
): Promise<ManagedWorldGraphProjectionResponse> {
  return apiFetch<ManagedWorldGraphProjectionResponse>(
    "/api/live/world-graph/managed-projection",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

export async function postWorldGraphCompleteObject(
  request: WorldGraphObjectProjectionRequest,
): Promise<WorldGraphObjectProjectionResult> {
  return apiFetch<WorldGraphObjectProjectionResult>(
    "/api/live/world-graph/retrieval/complete-object",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

export async function postWorldGraphRecapProjection(
  request: WorldGraphProjectionRequest,
): Promise<WorldGraphRecapProjection> {
  return withProjectionRequestCache("recap-projection", request, () =>
    apiFetch<WorldGraphRecapProjection>("/api/live/world-graph/recap-projection", {
      method: "POST",
      body: JSON.stringify(request),
    }),
  );
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

export async function getBuildSourceNavigation(args: {
  sourceArtifactId: string;
  sourceSpanRefId: string;
}): Promise<BuildSourceNavigationResponse> {
  const params = new URLSearchParams({
    source_artifact_id: args.sourceArtifactId,
    source_span_ref_id: args.sourceSpanRefId,
  });
  return apiFetch<BuildSourceNavigationResponse>(
    `/api/live/source-navigation?${params.toString()}`,
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

export async function postIndexAgentTurn(
  request: IndexAgentTurnRequestV1,
): Promise<IndexAgentTurnResponseV1> {
  return apiFetch<IndexAgentTurnResponseV1>("/api/live/agent/turn", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function postWorldPlanAgentTurn(
  request: WorldPlanAgentTurnRequestV1,
): Promise<WorldPlanAgentTurnResponse> {
  return apiFetch<WorldPlanAgentTurnResponse>("/api/live/agent/turn", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export interface WorldAgentConversationHistoryOptions {
  limit?: number;
  beforeSequence?: number;
  includeTurnCorrelation?: boolean;
}

export async function getWorldAgentConversationHistory(
  worldId: string,
  options: WorldAgentConversationHistoryOptions = {},
): Promise<WorldAgentConversationHistoryResponse> {
  const query = new URLSearchParams();
  if (options.limit !== undefined) query.set("limit", String(options.limit));
  if (options.beforeSequence !== undefined) query.set("before_sequence", String(options.beforeSequence));
  if (options.includeTurnCorrelation === true) query.set("include_turn_correlation", "true");
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch<WorldAgentConversationHistoryResponse>(
    `/api/live/agent/worlds/${encodeURIComponent(worldId)}/conversation${suffix}`,
  );
}

export async function getWorldAgentNewConversationStatus(
  worldId: string, request: WorldAgentNewConversationRequestV1,
): Promise<WorldAgentNewConversationStatusV1> {
  const query = new URLSearchParams({
    expected_pointer_revision: String(request.expected_pointer_revision),
    expected_active_conversation_id: request.expected_active_conversation_id ?? "null",
  });
  return apiFetch<WorldAgentNewConversationStatusV1>(
    `/api/live/agent/worlds/${encodeURIComponent(worldId)}/conversation/commands/${encodeURIComponent(request.command_id)}?${query}`,
  );
}

export async function postWorldAgentNewConversation(
  worldId: string,
  request: WorldAgentNewConversationRequestV1,
): Promise<WorldAgentNewConversationResponseV1> {
  return apiFetch<WorldAgentNewConversationResponseV1>(
    `/api/live/agent/worlds/${encodeURIComponent(worldId)}/conversation/new`,
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
      ...(options.surfaceContext != null
        ? { surface_context: options.surfaceContext }
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

export async function postPlanDocumentEditProposal(
  request: PlanDocumentEditProposalRequest,
): Promise<PlanDocumentEditProposalResponse> {
  return apiFetch<PlanDocumentEditProposalResponse>("/api/live/plan-document-edit/propose", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function postWorldPlanDocumentEditProposal(
  request: WorldPlanDocumentEditProposalRequest,
): Promise<WorldPlanDocumentEditProposalResponse> {
  return apiFetch<WorldPlanDocumentEditProposalResponse>("/api/live/world-plan-edit/propose", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getWorldPlanDocumentEditActions(
  worldId: string,
  documentId: string,
): Promise<WorldPlanActionProjectionPage> {
  const query = new URLSearchParams({ world_id: worldId, document_id: documentId });
  return apiFetch<WorldPlanActionProjectionPage>(`/api/live/world-plan-edit/actions?${query.toString()}`);
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

export async function getWorldGraphBootstrapStatus(): Promise<WorldGraphBootstrapStatusV1> {
  return apiFetch<WorldGraphBootstrapStatusV1>("/api/live/world-graph-bootstrap/status");
}

export async function createThreatDraft(
  request: CreateThreatDraftRequest,
): Promise<ThreatDraft> {
  return apiFetch<ThreatDraft>("/api/live/threat-drafts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
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

export async function getThreatDraft(draftId: string): Promise<ThreatDraft> {
  return apiFetch<ThreatDraft>(`/api/live/threat-drafts/${encodeURIComponent(draftId)}`);
}

export async function postThreatQueryHydration(
  request: ThreatQueryHydrationRequestV1,
): Promise<ThreatQueryHydrationResponseV1> {
  return apiFetch<ThreatQueryHydrationResponseV1>("/api/live/threats/query-hydration", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export async function reviseThreatDraftCandidate(
  draftId: string,
  request: ReviseCandidateFromEditedDefinitionRequestV1,
): Promise<ReviseCandidateFromEditedDefinitionResponseV1> {
  return apiFetch<ReviseCandidateFromEditedDefinitionResponseV1>(
    `/api/live/threat-drafts/${encodeURIComponent(draftId)}/candidates:revise`,
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

export async function acceptThreatDraftMechanics(
  draftId: string,
  request: AcceptThreatDraftMechanicsRequestV1,
): Promise<AcceptThreatDraftMechanicsResponseV1> {
  return apiFetch<AcceptThreatDraftMechanicsResponseV1>(
    `/api/live/threat-drafts/${encodeURIComponent(draftId)}/mechanics:accept`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export async function getAcceptanceOperation(
  draftId: string,
  operationId: string,
): Promise<ReadAcceptanceOperationResponseV1> {
  return apiFetch<ReadAcceptanceOperationResponseV1>(
    `/api/live/threat-drafts/${encodeURIComponent(draftId)}/acceptance-operations/${encodeURIComponent(operationId)}`,
  );
}

export async function reconcileAcceptanceOperation(
  draftId: string,
  operationId: string,
): Promise<AcceptThreatDraftMechanicsResponseV1> {
  return apiFetch<AcceptThreatDraftMechanicsResponseV1>(
    `/api/live/threat-drafts/${encodeURIComponent(draftId)}/acceptance-operations/${encodeURIComponent(operationId)}:reconcile`,
    {
      method: "POST",
    },
  );
}

export async function beginThreatPublicationOperation(
  draftId: string,
  request: BeginThreatPublicationOperationRequestV1,
): Promise<ThreatPublicationOperationResponseV1> {
  return publicationFetch(
    threatPublicationOperationsPrefix(draftId),
    { method: "POST", body: JSON.stringify(request) },
    validateOperationPublicationEnvelope,
  );
}

export async function getThreatPublicationOperation(
  draftId: string,
  operationId: string,
): Promise<ThreatPublicationOperationResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}`,
    undefined,
    validateOperationPublicationEnvelope,
  );
}

export async function refreshThreatPublicationOperation(
  draftId: string,
  operationId: string,
): Promise<ThreatPublicationOperationResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}/refresh`,
    { method: "POST" },
    validateOperationPublicationEnvelope,
  );
}

export async function cancelThreatPublicationOperation(
  draftId: string,
  operationId: string,
  request: CancelThreatPublicationOperationRequestV1,
): Promise<ThreatPublicationOperationResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}/cancel`,
    { method: "POST", body: JSON.stringify(request) },
    validateOperationPublicationEnvelope,
  );
}

export async function retryThreatPublicationOperation(
  draftId: string,
  operationId: string,
  request: RetryThreatPublicationOperationRequestV1,
): Promise<ThreatPublicationOperationResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}/retry`,
    { method: "POST", body: JSON.stringify(request) },
    validateOperationPublicationEnvelope,
  );
}

export async function prepareThreatIdentityCandidates(
  draftId: string,
  operationId: string,
  request?: PrepareThreatIdentityCandidatesRequestV1,
): Promise<ThreatPublicationIdentityResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}/identity-candidates/prepare`,
    { method: "POST", body: JSON.stringify(request ?? {}) },
    validateIdentityPublicationEnvelope,
  );
}

export async function createThreatIdentityResolution(
  draftId: string,
  operationId: string,
  request: CreateThreatIdentityResolutionRequestV1,
): Promise<ThreatPublicationIdentityResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}/identity-resolutions`,
    { method: "POST", body: JSON.stringify(request) },
    validateIdentityPublicationEnvelope,
  );
}

export async function getThreatIdentityResolution(
  draftId: string,
  operationId: string,
  resolutionId: string,
): Promise<ThreatPublicationIdentityResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}/identity-resolutions/${encodeURIComponent(resolutionId)}`,
    undefined,
    validateIdentityPublicationEnvelope,
  );
}

export async function prepareThreatPublicationProposal(
  draftId: string,
  operationId: string,
  resolutionId: string,
  request: PrepareThreatPublicationProposalRequestV1,
): Promise<ThreatPublicationProposalResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}/identity-resolutions/${encodeURIComponent(resolutionId)}/proposals`,
    { method: "POST", body: JSON.stringify(request) },
    validateProposalPublicationEnvelope,
  );
}

export async function getThreatPublicationProposal(
  draftId: string,
  operationId: string,
  proposalId: string,
): Promise<ThreatPublicationProposalResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}/proposals/${encodeURIComponent(proposalId)}`,
    undefined,
    validateProposalPublicationEnvelope,
  );
}

export async function confirmThreatPublicationCommit(
  draftId: string,
  operationId: string,
  proposalId: string,
  request: ConfirmThreatPublicationRequestV1,
): Promise<ThreatPublicationCommitResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}/proposals/${encodeURIComponent(proposalId)}/commits`,
    { method: "POST", body: JSON.stringify(request) },
    validateCommitPublicationEnvelope,
  );
}

export async function getThreatPublicationCommit(
  draftId: string,
  operationId: string,
  commitId: string,
): Promise<ThreatPublicationCommitResponseV1> {
  return publicationFetch(
    `${threatPublicationOperationsPrefix(draftId)}/${encodeURIComponent(operationId)}/commits/${encodeURIComponent(commitId)}`,
    undefined,
    validateCommitPublicationEnvelope,
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

export async function listWorldContainers(): Promise<WorldContainersListResponse> {
  return apiFetch<WorldContainersListResponse>("/api/live/world-containers");
}

export async function createWorldContainer(
  request: CreateWorldContainerRequest,
): Promise<WorldContainerRecord> {
  return apiFetch<WorldContainerRecord>("/api/live/world-containers", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function listWorldOwnedPlans(worldId: string): Promise<WorldOwnedPlansResponseV2> {
  return apiFetch<WorldOwnedPlansResponseV2>(
    `/api/live/workspace-documents/world-plans?world_id=${encodeURIComponent(worldId)}`,
  );
}

export async function createWorldOwnedPlan(request: {
  schema_version: "dmb_workspace_document_create_v2";
  scope_mode: "world";
  world_id: string;
  title: string;
}): Promise<WorldOwnedPlanRecordV2> {
  return apiFetch<WorldOwnedPlanRecordV2>("/api/live/workspace-documents/world-plans", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getWorldOwnedPlanSnapshot(documentId: string): Promise<WorldOwnedPlanSnapshotV2> {
  return apiFetch<WorldOwnedPlanSnapshotV2>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}/snapshot`,
  );
}

const CANONICAL_API_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const CANONICAL_API_SHA256 = /^[0-9a-f]{64}$/;

function assertWorldRunbookRecord(
  value: unknown,
  worldId: string,
  expectedDocumentId?: string,
): asserts value is WorldOwnedRunbookRecordV2 {
  if (typeof value !== "object" || value == null) {
    throw new TypeError("World Runbook response is not an object.");
  }
  const record = value as Partial<WorldOwnedRunbookRecordV2> & { campaign_id?: unknown };
  if (
    record.schema_version !== "dmb_world_owned_runbook_record_v2"
    || record.scope_mode !== "world"
    || record.world_id !== worldId
    || record.campaign_id !== null
    || record.kind !== "runbook"
    || typeof record.document_id !== "string"
    || !CANONICAL_API_UUID.test(record.document_id)
    || (expectedDocumentId != null && record.document_id !== expectedDocumentId)
  ) {
    throw new TypeError("World Runbook response does not match the selected World and V2 contract.");
  }
}

function assertWorldPlayRun(
  value: unknown,
  worldId: string,
  expectedRunId?: string,
): asserts value is WorldPlayRunRecordV2 {
  if (typeof value !== "object" || value == null) {
    throw new TypeError("World Play Run response is not an object.");
  }
  const run = value as Partial<WorldPlayRunRecordV2> & { campaign_id?: unknown };
  if (
    run.schema_version !== "dmb_world_play_run_record_v2"
    || run.world_id !== worldId
    || Object.prototype.hasOwnProperty.call(run, "campaign_id")
    || typeof run.run_id !== "string"
    || !CANONICAL_API_UUID.test(run.run_id)
    || (expectedRunId != null && run.run_id !== expectedRunId)
    || typeof run.playable_artifact_id !== "string"
    || !CANONICAL_API_UUID.test(run.playable_artifact_id)
    || typeof run.playable_work_revision_id !== "string"
    || !CANONICAL_API_UUID.test(run.playable_work_revision_id)
    || !Number.isInteger(run.playable_revision)
    || (run.playable_revision ?? 0) <= 0
    || !Number.isInteger(run.run_revision)
    || (run.run_revision ?? 0) <= 0
    || typeof run.playable_content_sha256 !== "string"
    || !CANONICAL_API_SHA256.test(run.playable_content_sha256)
    || typeof run.progress !== "object"
    || run.progress == null
  ) {
    throw new TypeError("World Play Run response does not match the selected World and V2 contract.");
  }
}

function assertWorldPlayActiveRunState(
  value: unknown,
  worldId: string,
  expectedRunId?: string,
): asserts value is WorldPlayActiveRunStateV2 {
  if (typeof value !== "object" || value === null) {
    throw new TypeError("World active-Run response is not an object.");
  }
  const state = value as Partial<WorldPlayActiveRunStateV2>;
  if (
    Object.keys(value).sort().join(",") !== "run_id,schema_version,selected_at,world_id"
    || state.schema_version !== "dmb_world_play_active_run_v2"
    || state.world_id !== worldId
    || !(state.run_id === null || (
      typeof state.run_id === "string"
      && CANONICAL_API_UUID.test(state.run_id)
      && (expectedRunId === undefined || state.run_id === expectedRunId)
    ))
    || !(state.selected_at === null || (
      typeof state.selected_at === "string"
      && state.selected_at.trim() !== ""
      && Number.isFinite(Date.parse(state.selected_at))
    ))
    || ((state.run_id === null) !== (state.selected_at === null))
  ) {
    throw new TypeError("World active-Run response does not match the scoped V2 contract.");
  }
}

function worldQuery(worldId: string): string {
  const cleaned = worldId.trim();
  if (!cleaned || cleaned !== worldId) throw new TypeError("World ID must be non-empty and canonical.");
  return `world_id=${encodeURIComponent(cleaned)}`;
}

export async function listWorldOwnedRunbooks(worldId: string): Promise<WorldOwnedRunbooksResponseV2> {
  const response = await apiFetch<WorldOwnedRunbooksResponseV2>(
    `/api/live/workspace-documents/world-runbooks?${worldQuery(worldId)}`,
  );
  if (
    response.schema_version !== "dmb_world_owned_runbooks_list_v2"
    || response.scope_mode !== "world"
    || response.world_id !== worldId
    || !Array.isArray(response.records)
  ) {
    throw new TypeError("World Runbook inventory does not match the selected World and V2 contract.");
  }
  response.records.forEach((record) => assertWorldRunbookRecord(record, worldId));
  return response;
}

export async function createWorldOwnedRunbook(request: {
  world_id: string;
  title: string;
}): Promise<WorldOwnedRunbookRecordV2> {
  worldQuery(request.world_id);
  const record = await apiFetch<WorldOwnedRunbookRecordV2>("/api/live/workspace-documents/world-runbooks", {
    method: "POST",
    body: JSON.stringify({
      schema_version: "dmb_workspace_document_create_v2",
      scope_mode: "world",
      world_id: request.world_id,
      title: request.title,
    }),
  });
  assertWorldRunbookRecord(record, request.world_id);
  return record;
}

export async function getWorldOwnedRunbook(
  documentId: string,
  worldId: string,
): Promise<WorldOwnedRunbookRecordV2> {
  const record = await apiFetch<WorldOwnedRunbookRecordV2>(
    `/api/live/workspace-documents/world-runbooks/${encodeURIComponent(documentId)}?${worldQuery(worldId)}`,
  );
  assertWorldRunbookRecord(record, worldId, documentId);
  return record;
}

export async function getWorldOwnedRunbookSnapshot(
  documentId: string,
  worldId: string,
): Promise<WorldOwnedRunbookSnapshotV2> {
  const snapshot = await apiFetch<WorldOwnedRunbookSnapshotV2>(
    `/api/live/workspace-documents/world-runbooks/${encodeURIComponent(documentId)}/snapshot?${worldQuery(worldId)}`,
  );
  if (
    snapshot.schema_version !== "dmb_workspace_runbook_snapshot_v2"
    || snapshot.record == null
    || snapshot.record.document_id !== documentId
    || snapshot.record.world_id !== worldId
  ) {
    throw new TypeError("World Runbook snapshot does not match the selected World and document.");
  }
  assertWorldRunbookRecord(snapshot.record, worldId, documentId);
  return snapshot;
}

export async function getWorldOwnedRunbookCommittedRevision(
  documentId: string,
  worldId: string,
  revisionN?: number,
  expectedSha256?: string,
): Promise<WorldOwnedRunbookCommittedRevisionV2> {
  worldQuery(worldId);
  if ((revisionN == null) !== (expectedSha256 == null)) {
    throw new TypeError("Exact World revision reads require both revision and expected SHA-256.");
  }
  if (
    revisionN != null
    && (!Number.isInteger(revisionN) || revisionN <= 0 || !CANONICAL_API_SHA256.test(expectedSha256 ?? ""))
  ) {
    throw new TypeError("Exact World revision reads require a positive revision and canonical SHA-256.");
  }
  const suffix = revisionN == null ? "" : `/${encodeURIComponent(String(revisionN))}`;
  const query = new URLSearchParams({ world_id: worldId });
  if (expectedSha256 != null) query.set("expected_sha256", expectedSha256);
  const committed = await apiFetch<WorldOwnedRunbookCommittedRevisionV2>(
    `/api/live/workspace-documents/world-runbooks/${encodeURIComponent(documentId)}/committed-revision${suffix}?${query.toString()}`,
  );
  if (
    committed.schema_version !== "dmb_workspace_committed_revision_v2"
    || committed.scope_mode !== "world"
    || committed.world_id !== worldId
    || committed.campaign_id !== null
    || committed.document_id !== documentId
    || committed.kind !== "runbook"
    || (revisionN != null && committed.revision_n !== revisionN)
    || (expectedSha256 != null && committed.content_sha256 !== expectedSha256)
  ) {
    throw new TypeError("World Runbook revision does not match the selected World, document, and exact pin.");
  }
  return committed;
}

export async function prepareWorldRunbookMarkdownWrite(
  worldId: string,
  request: TiptapMarkdownWritePrepareRequest,
): Promise<TiptapMarkdownWritePrepareResponse> {
  const response = await apiFetch<TiptapMarkdownWritePrepareResponse>(
    `/api/live/workspace-documents/world-runbooks/${encodeURIComponent(request.document_id)}/tiptap/prepare?${worldQuery(worldId)}`,
    {
      method: "POST",
      body: JSON.stringify({
        ...request,
        schema_version: "dmb_tiptap_markdown_write_prepare_v2",
        scope_mode: "world",
        world_id: worldId,
      }),
    },
  );
  if (
    response.schema_version !== "dmb_tiptap_markdown_write_prepare_v2"
    || response.scope_mode !== "world"
    || response.world_id !== worldId
    || response.document_id !== request.document_id
  ) {
    throw new TypeError("World Runbook prepare response does not match the selected World and document.");
  }
  return response;
}

export async function commitWorldRunbookMarkdownWrite(
  worldId: string,
  request: TiptapMarkdownWriteCommitRequest,
): Promise<WorldOwnedRunbookMarkdownWriteCommitResponseV2> {
  const response = await apiFetch<WorldOwnedRunbookMarkdownWriteCommitResponseV2>(
    `/api/live/workspace-documents/world-runbooks/${encodeURIComponent(request.document_id)}/tiptap/commit?${worldQuery(worldId)}`,
    {
      method: "POST",
      body: JSON.stringify({
        ...request,
        schema_version: "dmb_tiptap_markdown_write_commit_v2",
        scope_mode: "world",
        world_id: worldId,
      }),
    },
  );
  if (
    response.schema_version !== "dmb_tiptap_markdown_write_commit_v2"
    || response.scope_mode !== "world"
    || response.world_id !== worldId
    || response.document_id !== request.document_id
  ) {
    throw new TypeError("World Runbook commit response does not match the selected World and document.");
  }
  assertWorldRunbookRecord(response.committed_record, worldId, request.document_id);
  return response;
}

export async function getWorkspaceDocument(documentId: string): Promise<WorkspaceDocumentRecord> {
  return apiFetch<WorkspaceDocumentRecord>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}`,
  );
}

export async function getWorkspaceDocumentAny(
  documentId: string,
): Promise<WorkspaceDocumentRecord | WorldOwnedPlanRecordV2> {
  return apiFetch<WorkspaceDocumentRecord | WorldOwnedPlanRecordV2>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}`,
  );
}

export async function getWorkspaceDocumentSnapshot(documentId: string): Promise<WorkspaceDocumentSnapshot> {
  return apiFetch<WorkspaceDocumentSnapshot>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}/snapshot`,
  );
}

export async function getNativeWorldSourceAdmissionStatus(
  documentId: string,
  expectedRevision?: number,
): Promise<NativeWorldSourceAdmissionStatus> {
  const query = expectedRevision == null
    ? ""
    : `?expected_revision=${encodeURIComponent(String(expectedRevision))}`;
  return apiFetch<NativeWorldSourceAdmissionStatus>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}/native-world-source${query}`,
  );
}

export async function admitNativeWorldSource(
  documentId: string,
  expectedRevision: number,
  expectedBodySha256: string,
): Promise<NativeWorldSourceAdmissionStatus> {
  return apiFetch<NativeWorldSourceAdmissionStatus>(
    `/api/live/workspace-documents/${encodeURIComponent(documentId)}/native-world-source`,
    {
      method: "POST",
      body: JSON.stringify({
        expected_revision: expectedRevision,
        expected_body_sha256: expectedBodySha256,
      }),
    },
  );
}

export async function getCommittedWorkspaceRevision(
  documentId: string,
  revisionN?: number,
): Promise<WorkspaceCommittedRevision> {
  const encodedId = encodeURIComponent(documentId);
  const suffix = revisionN == null ? "" : `/${encodeURIComponent(String(revisionN))}`;
  return apiFetch<WorkspaceCommittedRevision>(
    `/api/live/workspace-documents/${encodedId}/committed-revision${suffix}`,
  );
}

export async function getWorldOwnedPlanCommittedRevision(
  documentId: string,
  revisionN?: number,
): Promise<WorldOwnedCommittedRevisionV2> {
  const encodedId = encodeURIComponent(documentId);
  const suffix = revisionN == null ? "" : `/${encodeURIComponent(String(revisionN))}`;
  return apiFetch<WorldOwnedCommittedRevisionV2>(
    `/api/live/workspace-documents/${encodedId}/committed-revision${suffix}`,
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

export async function commitWorldOwnedPlanMarkdownWrite(
  request: TiptapMarkdownWriteCommitRequest & {
    schema_version: "dmb_tiptap_markdown_write_commit_v2";
    scope_mode: "world";
    world_id: string;
  },
): Promise<WorldOwnedPlanMarkdownWriteCommitResponseV2> {
  return apiFetch<WorldOwnedPlanMarkdownWriteCommitResponseV2>(
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

/** Exact-run historical recap source inspection (read-only; not promotion review). */
export async function getHistoricalRecapInspection(
  runId: string,
): Promise<HistoricalRecapInspectionResponse> {
  return apiFetch<HistoricalRecapInspectionResponse>(
    `/api/live/graph-preview/extraction-runs/${encodeURIComponent(runId)}/recap-inspection`,
  );
}

/** Exact-run durable recap projected onto the current governed World. */
export async function getHistoricalRecapWorldProjection(
  runId: string,
): Promise<HistoricalRecapWorldProjectionResponse> {
  return apiFetch<HistoricalRecapWorldProjectionResponse>(
    `/api/live/graph-preview/extraction-runs/${encodeURIComponent(runId)}/recap-projection`,
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

export async function getPlayActiveRun(): Promise<PlayActiveRunState> {
  return apiFetch<PlayActiveRunState>("/api/live/play-active-run");
}

export async function putPlayActiveRun(runId: string): Promise<PlayActiveRunState> {
  return apiFetch<PlayActiveRunState>("/api/live/play-active-run", {
    method: "PUT",
    body: JSON.stringify({ run_id: runId }),
  });
}

export async function getWorldPlayActiveRun(worldId: string): Promise<WorldPlayActiveRunStateV2> {
  const state = await apiFetch<WorldPlayActiveRunStateV2>(
    `/api/live/world-play-runs/v2/active?${worldQuery(worldId)}`,
  );
  assertWorldPlayActiveRunState(state, worldId);
  return state;
}

export async function putWorldPlayActiveRun(
  worldId: string,
  runId: string,
): Promise<WorldPlayActiveRunStateV2> {
  const state = await apiFetch<WorldPlayActiveRunStateV2>(
    `/api/live/world-play-runs/v2/active?${worldQuery(worldId)}`,
    { method: "PUT", body: JSON.stringify({ run_id: runId }) },
  );
  assertWorldPlayActiveRunState(state, worldId, runId);
  return state;
}

export async function listPlayRuns(args: {
  campaign_id?: string;
  playable_artifact_id?: string;
} = {}): Promise<PlayRunsListResponse> {
  const params = new URLSearchParams();
  if (args.campaign_id) params.set("campaign_id", args.campaign_id);
  if (args.playable_artifact_id) params.set("playable_artifact_id", args.playable_artifact_id);
  const query = params.toString();
  return apiFetch<PlayRunsListResponse>(`/api/live/play-runs${query ? `?${query}` : ""}`);
}

export async function getPlayRun(
  runId: string,
  options: { ensureNativeReady?: boolean } = {},
): Promise<PlayRunRecord> {
  const query = options.ensureNativeReady ? "?ensure_native_ready=true" : "";
  return apiFetch<PlayRunRecord>(`/api/live/play-runs/${encodeURIComponent(runId)}${query}`);
}

export async function putPlayRun(
  runId: string,
  request: CreatePlayRunRequest,
): Promise<PlayRunRecord> {
  return apiFetch<PlayRunRecord>(
    `/api/live/play-runs/${encodeURIComponent(runId)}`,
    { method: "PUT", body: JSON.stringify(request) },
  );
}

export async function getPlayRunReferenceManifest(runId: string): Promise<PlayRunReferenceManifest> {
  return apiFetch<PlayRunReferenceManifest>(
    `/api/live/play-runs/${encodeURIComponent(runId)}/reference-manifest`,
  );
}

export async function putPlayRunReferenceManifest(
  runId: string,
): Promise<PlayRunReferenceManifest> {
  return apiFetch<PlayRunReferenceManifest>(
    `/api/live/play-runs/${encodeURIComponent(runId)}/reference-manifest`,
    { method: "PUT" },
  );
}

export async function putPlayRunProgress(
  runId: string,
  request: ReplacePlayRunProgressRequest,
): Promise<PlayRunRecord> {
  return apiFetch<PlayRunRecord>(
    `/api/live/play-runs/${encodeURIComponent(runId)}/progress`,
    { method: "PUT", body: JSON.stringify(request) },
  );
}

export async function listWorldPlayRuns(worldId: string): Promise<WorldPlayRunsListResponseV2> {
  const response = await apiFetch<WorldPlayRunsListResponseV2>(
    `/api/live/world-play-runs/v2?${worldQuery(worldId)}`,
  );
  if (
    response.schema_version !== "dmb_world_play_runs_list_v2"
    || !Array.isArray(response.records)
  ) {
    throw new TypeError("World Play Run inventory does not match the V2 contract.");
  }
  response.records.forEach((run) => assertWorldPlayRun(run, worldId));
  return response;
}

export async function getWorldPlayRun(runId: string, worldId: string): Promise<WorldPlayRunRecordV2> {
  const run = await apiFetch<WorldPlayRunRecordV2>(
    `/api/live/world-play-runs/v2/${encodeURIComponent(runId)}?${worldQuery(worldId)}`,
  );
  assertWorldPlayRun(run, worldId, runId);
  return run;
}

export async function putWorldPlayRun(
  runId: string,
  worldId: string,
  request: CreatePlayRunRequest,
): Promise<WorldPlayRunRecordV2> {
  const run = await apiFetch<WorldPlayRunRecordV2>(
    `/api/live/world-play-runs/v2/${encodeURIComponent(runId)}?${worldQuery(worldId)}`,
    { method: "PUT", body: JSON.stringify(request) },
  );
  assertWorldPlayRun(run, worldId, runId);
  return run;
}

export async function putWorldPlayRunProgress(
  runId: string,
  worldId: string,
  request: ReplacePlayRunProgressRequest,
): Promise<WorldPlayRunRecordV2> {
  const run = await apiFetch<WorldPlayRunRecordV2>(
    `/api/live/world-play-runs/v2/${encodeURIComponent(runId)}/progress?${worldQuery(worldId)}`,
    { method: "PUT", body: JSON.stringify(request) },
  );
  assertWorldPlayRun(run, worldId, runId);
  return run;
}

export async function putWorldPlayRunRebase(
  runId: string,
  worldId: string,
  request: RebasePlayRunRequest,
): Promise<WorldPlayRunRecordV2> {
  const run = await apiFetch<WorldPlayRunRecordV2>(
    `/api/live/world-play-runs/v2/${encodeURIComponent(runId)}/rebase?${worldQuery(worldId)}`,
    { method: "PUT", body: JSON.stringify(request) },
  );
  assertWorldPlayRun(run, worldId, runId);
  return run;
}

export async function getWorldPlayRunReferenceManifest(
  runId: string,
  worldId: string,
): Promise<PlayRunReferenceManifest> {
  const manifest = await apiFetch<PlayRunReferenceManifest>(
    `/api/live/world-play-runs/v2/${encodeURIComponent(runId)}/reference-manifest?${worldQuery(worldId)}`,
  );
  if (manifest.run_id !== runId) {
    throw new TypeError("World Play Run manifest does not match the requested Run.");
  }
  return manifest;
}

export async function putWorldPlayRunReferenceManifest(
  runId: string,
  worldId: string,
): Promise<PlayRunReferenceManifest> {
  const manifest = await apiFetch<PlayRunReferenceManifest>(
    `/api/live/world-play-runs/v2/${encodeURIComponent(runId)}/reference-manifest?${worldQuery(worldId)}`,
    { method: "PUT" },
  );
  if (manifest.run_id !== runId) {
    throw new TypeError("World Play Run manifest does not match the requested Run.");
  }
  return manifest;
}
