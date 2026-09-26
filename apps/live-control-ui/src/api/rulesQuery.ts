export interface RulesEvidenceItem {
  rank: number;
  entity_id: string;
  assertion_id: string;
  evidence_ref_id: string;
  evidence_unit_id: string;
  source_artifact_id: string;
  source_revision_id: string | null;
  source_uri: string | null;
  source_locator: string | null;
  locator: string | null;
  source_anchor_id: string | null;
  excerpt: string | null;
}

export interface RulesQueryPacket {
  schema_version: "dmb_rules_query_packet_v1";
  query_id: string;
  ruleset_id: string;
  rules_space_id: string | null;
  rules_revision_id: string | null;
  status: "success" | "no_evidence" | "insufficient_evidence" | "rules_space_unavailable" | "downstream_failure";
  evidence: RulesEvidenceItem[];
  trace: {
    completeness: "complete" | "partial" | "unavailable";
    reason: string | null;
  };
}

const baseUrl = (import.meta.env.VITE_LIVE_API_BASE_URL as string | undefined) ?? "";

export async function queryRules(question: string, signal?: AbortSignal): Promise<RulesQueryPacket> {
  const response = await fetch(`${baseUrl}/api/live/rules/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      schema_version: "dmb_rules_query_request_v1",
      question,
      ruleset_id: "dnd5e-2024-srd-occupancy-v1",
      max_hits: 5,
    }),
    signal,
  });
  if (!response.ok) throw new Error(`Rules service returned ${response.status}`);
  const packet: unknown = await response.json();
  if (
    typeof packet !== "object" || packet === null ||
    (packet as RulesQueryPacket).schema_version !== "dmb_rules_query_packet_v1" ||
    !Array.isArray((packet as RulesQueryPacket).evidence)
  ) throw new Error("Invalid rules query packet");
  return packet as RulesQueryPacket;
}
