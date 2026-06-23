import type {
  ArtifactReadResponse,
  CapabilityReadResponse,
  LiveEventsResponse,
  LiveJobsResponse,
  PlanViewProjection,
  ProjectionCommand,
  ProjectionWriteResult,
  ProjectionTarget,
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
} from "./types";

const baseUrl = (import.meta.env.VITE_LIVE_API_BASE_URL as string | undefined) ?? "";

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
    try {
      const body = await parseJsonBody<{ detail?: unknown }>(response);
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail != null) {
        detail = JSON.stringify(body.detail);
      }
    } catch (parseError) {
      if (parseError instanceof Error) {
        detail = parseError.message;
      }
    }
    throw new Error(detail);
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

export async function postLiveQuery(
  text: string,
  campaignId: string,
  session: number,
  queryBackend: LiveQueryBackend = "live",
  options: LiveQueryOptions = {},
): Promise<LiveQueryResponse> {
  return apiFetch<LiveQueryResponse>("/api/live/query", {
    method: "POST",
    body: JSON.stringify({
      campaign_id: campaignId,
      session,
      mode: "live",
      query_backend: queryBackend,
      text,
      manifest_path: DEFAULT_PLANNING_MANIFEST_PATH,
      agent_thread_id: options.agentThreadId ?? null,
      hermes_session_id: options.hermesSessionId ?? null,
      trace_requested: options.traceRequested ?? null,
    }),
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
