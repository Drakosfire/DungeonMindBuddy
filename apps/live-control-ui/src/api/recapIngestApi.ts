import type { RecapIngestRequest, RecapIngestStatus } from "./types";

import {authenticatedApiFetch} from "./liveApi";

async function parseJsonBody<T>(response: Response): Promise<T> {
  const text = await response.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`API response is not valid JSON (HTTP ${response.status}).`);
  }
}

export async function postRecapIngest(body: RecapIngestRequest): Promise<RecapIngestStatus> {
  const {response} = await authenticatedApiFetch("/api/live/recap-ingest", {
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

export interface RecapNameReview {
  schema: "dmb_recap_name_review_v1";
  scope: {managed_world_id: string; native_world_id: string; binding_version: number; campaign_id: string};
  source_sha256: string; catalog_sha256: string; review_id: string; exact_mention_count: number;
  suggestions: Array<{id: string; start: number; end: number; surface: string; options: string[]}>;
}
export async function postRecapNameReview(body: RecapIngestRequest): Promise<RecapNameReview> {
  const {response} = await authenticatedApiFetch("/api/live/recap-name-review", {
    method: "POST", cache: "no-store", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Names could not be checked (HTTP ${response.status}). Your draft is preserved.`);
  const result = await response.json() as RecapNameReview;
  if (result.schema !== "dmb_recap_name_review_v1" || result.scope?.managed_world_id !== body.managed_world_id || result.scope?.campaign_id !== body.campaign_id
      || !/^[a-f0-9]{64}$/.test(result.review_id) || !Array.isArray(result.suggestions)
      || !result.suggestions.every(s => /^[a-f0-9]{64}$/.test(s.id) && Number.isSafeInteger(s.start) && Number.isSafeInteger(s.end) && s.start >= 0 && s.end > s.start && typeof s.surface === "string" && Array.isArray(s.options) && s.options.length > 0 && s.options.every(o => typeof o === "string" && o.length > 0)))
    throw new Error("Name review does not match this source. Check names again.");
  return result;
}
