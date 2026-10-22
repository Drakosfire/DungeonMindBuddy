import type { AcceptedMechanicsRefV1 } from "./types";

export interface WorldMechanicsTarget {
  managed_world_id: string;
  native_world_id: string;
  binding_version: number;
  graph_revision_id: string;
  node_id: string;
  label: string;
  kind: string;
  role: string;
  campaign_scope: string | null;
}
export interface AssociateWorldMechanicsRequest {
  request_id: string;
  draft_id: string;
  expected_draft_version: number;
  target: WorldMechanicsTarget;
  expected_version: number;
}
export interface WorldMechanicsAssociation {
  association_id: string;
  request: AssociateWorldMechanicsRequest;
  request_digest: string;
  version: number;
  previous_association_id: string | null;
  proof: {
    locator: Pick<AcceptedMechanicsRefV1, "provider" | "statblock_id" | "revision_id" | "contract" | "contract_version" | "definition_digest">;
    acceptance_operation_id: string;
    accepted_from_draft_version: number;
    accepted_from_candidate_id: string | null;
    acceptance_request_digest: string;
  };
  actor: string;
  created_at: string;
}
export interface AssociateWorldMechanicsResponse {
  association: WorldMechanicsAssociation;
  replayed: boolean;
}
