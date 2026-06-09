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
  LiveSurfaceResponse,
  ResolvedRollResponse,
  SurfaceLayout,
  StatblockWorkbenchCommandRequest,
  StatblockWorkbenchCommandResponse,
  StatblockWorkbenchSampleResponse,
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
): Promise<LiveQueryResponse> {
  return apiFetch<LiveQueryResponse>("/api/live/query", {
    method: "POST",
    body: JSON.stringify({
      campaign_id: campaignId,
      session,
      mode: "live",
      text,
      manifest_path: DEFAULT_PLANNING_MANIFEST_PATH,
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
