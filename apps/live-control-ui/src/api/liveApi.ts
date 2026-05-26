import type {
  LiveEventsResponse,
  LiveJobsResponse,
  LiveQueryResponse,
  LiveSurfaceResponse,
  ResolvedRollResponse,
  SurfaceLayout,
} from "./types";

const baseUrl = (import.meta.env.VITE_LIVE_API_BASE_URL as string | undefined) ?? "";

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
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail != null) {
        detail = JSON.stringify(body.detail);
      }
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
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
