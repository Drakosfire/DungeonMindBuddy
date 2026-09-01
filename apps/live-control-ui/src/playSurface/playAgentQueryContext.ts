import type { AgentWorldGraphQueryContextRequest, PlayRunRecord } from "../api/types";
import { getWorldIdForCampaign } from "../worldGraph/worldGraphSurfaceContext";

export function buildPlayAgentWorldGraphQueryContextRequest(
  run: PlayRunRecord,
): AgentWorldGraphQueryContextRequest | null {
  const worldId = getWorldIdForCampaign(run.campaign_id);
  if (!worldId) {
    return null;
  }
  return {
    schema: "dmb_agent_world_graph_query_context_request_v1",
    world_id: worldId,
    campaign_id: run.campaign_id,
    scope_mode: "campaign",
    focus: { kind: "none", session_id: null },
    admissibility: "gm",
    revision_pin: null,
  };
}
