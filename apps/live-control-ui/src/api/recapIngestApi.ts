import type { RecapExtractionProgress, RecapIngestRequest, RecapIngestStatus } from "./types";

const baseUrl = (import.meta.env.VITE_LIVE_API_BASE_URL as string | undefined) ?? "";

async function parseJsonBody<T>(response: Response): Promise<T> {
  const text = await response.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`API response is not valid JSON (HTTP ${response.status}).`);
  }
}

export async function postRecapIngest(body: RecapIngestRequest): Promise<RecapIngestStatus> {
  const response = await fetch(`${baseUrl}/api/live/recap-ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const errorBody = await parseJsonBody<{ detail?: unknown }>(response);
      if (typeof errorBody.detail === "string") {
        detail = errorBody.detail;
      } else if (errorBody.detail != null) {
        detail = JSON.stringify(errorBody.detail);
      }
    } catch {
      // Keep default response status text.
    }
    throw new Error(detail);
  }
  return parseJsonBody<RecapIngestStatus>(response);
}

export async function getRecapExtractionProgress(query: {
  campaignId: string;
  session: number;
}): Promise<RecapExtractionProgress> {
  const params = new URLSearchParams({
    campaign_id: query.campaignId,
    session: String(query.session),
  });
  const response = await fetch(`${baseUrl}/api/live/recap-ingest/extraction-progress?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to load extraction progress (HTTP ${response.status}).`);
  }
  return parseJsonBody<RecapExtractionProgress>(response);
}
