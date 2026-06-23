import type {
  AgentInteractionTurnMeta,
  LiveQueryBackend,
  LiveQueryResponse,
} from "../../api/types";

export const AGENT_TURN_HISTORY_CAP = 20;

export function historyStorageKey(campaignId: string): string {
  return `plan-agent-turns-v1:${campaignId}`;
}

export function turnMetaFromResponse(
  question: string,
  response: LiveQueryResponse,
  backend: LiveQueryBackend,
): AgentInteractionTurnMeta {
  const trace = response.agent_trace;
  const admitted =
    trace?.context_summary?.admitted_count ??
    response.context_packet?.admitted_evidence?.length ??
    null;
  const rejected =
    trace?.context_summary?.rejected_count ??
    response.context_packet?.rejected_evidence?.length ??
    null;

  return {
    id: trace?.trace_id ?? response.query_id ?? crypto.randomUUID(),
    question,
    answer: response.answer,
    backend,
    model: trace?.model ?? null,
    status: response.status ?? trace?.status ?? "unknown",
    askedAt: trace?.started_at ?? new Date().toISOString(),
    traceId: trace?.trace_id ?? null,
    admittedCount: admitted,
    rejectedCount: rejected,
    runtime: trace?.runtime ?? null,
    elapsedMs: trace?.elapsed_ms ?? null,
    provider: trace?.provider ?? null,
    stepCount: trace?.steps?.length ?? null,
  };
}

export function loadTurnHistory(campaignId: string): AgentInteractionTurnMeta[] {
  try {
    const raw = localStorage.getItem(historyStorageKey(campaignId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as AgentInteractionTurnMeta[];
    if (!Array.isArray(parsed)) return [];
    return parsed.slice(0, AGENT_TURN_HISTORY_CAP);
  } catch {
    return [];
  }
}

export function persistTurnHistory(campaignId: string, turns: AgentInteractionTurnMeta[]): void {
  const bounded = turns.slice(0, AGENT_TURN_HISTORY_CAP);
  localStorage.setItem(historyStorageKey(campaignId), JSON.stringify(bounded));
}
