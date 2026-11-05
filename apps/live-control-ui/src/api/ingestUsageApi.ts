import { authenticatedApiFetch, LiveApiError } from "./liveApi";
export interface UsageMetrics {
  inputTokens: number | null; outputTokens: number | null;
  cachedInputTokens: number | null; reasoningTokens: number | null;
  totalTokens: number | null; knownInputTokens: number | null; knownOutputTokens: number | null;
  providerAttempts: number | null; costUsd: number | null; knownCostUsd: number | null;
  costStatus: "reported" | "partial" | "unavailable" | "not_dispatched";
  pricingSource: string | null;
}
export interface ExtractionUsage {
  schema: "dmb_extraction_usage_v1"; managedWorldId: string; runId: string; runRevision: number;
  currency: "USD"; totals: UsageMetrics; passes: (UsageMetrics & {passName: string})[];
}
const record = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const count = (v: unknown) => v === null || (Number.isSafeInteger(v) && Number(v) >= 0);
const money = (v: unknown) => v === null || (typeof v === "number" && Number.isFinite(v) && v >= 0);
function metrics(v: unknown): boolean {
  return record(v) && ["inputTokens","outputTokens","cachedInputTokens","reasoningTokens","totalTokens","knownInputTokens","knownOutputTokens","providerAttempts"].every(k=>count(v[k]))
    && money(v.costUsd) && money(v.knownCostUsd) && ["reported","partial","unavailable","not_dispatched"].includes(String(v.costStatus))
    && (v.costStatus !== "reported" || v.costUsd !== null) && (v.costStatus === "reported" || v.costUsd === null)
    && (v.costStatus !== "partial" || v.knownCostUsd !== null) && (v.pricingSource === null || typeof v.pricingSource === "string");
}
export async function getIngestUsage(world: string, runId: string, revision: number, signal: AbortSignal): Promise<ExtractionUsage> {
  const {response}=await authenticatedApiFetch(`/api/live/graph-preview/extraction-runs/${encodeURIComponent(runId)}/usage?${new URLSearchParams({managed_world_id:world,expected_run_revision:String(revision)})}`,{cache:"no-store",signal});
  if (!response.ok) throw new LiveApiError("Extraction usage could not be read.",response.status);
  const v:unknown=await response.json();
  if (!record(v) || v.schema!=="dmb_extraction_usage_v1" || v.managedWorldId!==world || v.runId!==runId || v.runRevision!==revision || v.currency!=="USD" || !metrics(v.totals) || !Array.isArray(v.passes) || !v.passes.every(p=>metrics(p) && record(p) && typeof p.passName==="string"))
    throw new LiveApiError("Usage does not match the selected extraction. Reload saved work.",0);
  return v as unknown as ExtractionUsage;
}
