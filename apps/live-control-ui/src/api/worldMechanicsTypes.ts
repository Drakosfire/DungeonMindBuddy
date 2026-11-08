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

/** Consumer selection witnesses from one Core-admitted World view. */
export interface WorldCreatureCatalog {
  schema: 'dmb_native_world_creatures_v1';
  managed_world_id: string;
  native_world_id: string;
  binding_version: number;
  revision_id: string;
  completeness: 'complete' | 'partial';
  targets: WorldMechanicsTarget[];
}
export function verifyWorldCreatureCatalog(view: WorldCreatureCatalog, worldId: string): void {
  if (view?.schema !== 'dmb_native_world_creatures_v1' || view.managed_world_id !== worldId
    || typeof view.native_world_id !== 'string' || !view.native_world_id
    || !Number.isSafeInteger(view.binding_version) || view.binding_version < 1
    || typeof view.revision_id !== 'string' || !view.revision_id
    || !['complete', 'partial'].includes(view.completeness) || !Array.isArray(view.targets)
    || new Set(view.targets.map(n => n?.node_id)).size !== view.targets.length
    || view.targets.some(n => !n || n.managed_world_id !== worldId || n.native_world_id !== view.native_world_id
      || n.binding_version !== view.binding_version || n.graph_revision_id !== view.revision_id
      || typeof n.node_id !== 'string' || !n.node_id || typeof n.label !== 'string' || !n.label
      || n.kind !== 'npc' || n.role !== '' || n.campaign_scope !== null && (typeof n.campaign_scope !== 'string' || !n.campaign_scope))) {
    throw new TypeError('Native creature selection did not match the selected World.');
  }
}
