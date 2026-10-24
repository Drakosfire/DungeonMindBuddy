import { authenticatedApiFetch } from './liveApi';

export interface BuildProposalBasis {
  world_id: string; document_id: string; registry_revision: number; content_sha256: string;
  visibility: 'internal' | 'player_safe'; draft_sha256: string; caret: number;
  draft_generation: number; selection_generation: number; editor_sha256?: string | null;
  selection?: { end: number; text: string } | null;
}
export interface BuildProposalRequest {
  idempotency_key: string; conversation_id: string; expected_pointer_revision: number;
  basis: BuildProposalBasis; instruction: string; draft_markdown: string;
  origin?: { client_turn_id: string; durable_turn_id: string; turn_attempt: number; broker_operation_id: string; arguments_sha256: string } | null;
}
export interface BuildProposalRecord {
  schema_version: 'dmb_build_document_proposal_v1'; action_id: string;
  reservation: Omit<BuildProposalRequest, 'draft_markdown'>;
  request_fingerprint: string; after_turn_sequence: number; revision: number;
  state: 'reserved' | 'authorized' | 'sdk_entered' | 'response_received' | 'proposed' | 'failed' | 'unknown';
  created_at: string; updated_at: string; claim_expires_at: string;
  authorization: null | { provider_attempt_id: string; provider: string; model: string; api_mode: string;
    payload_sha256: string; payload_utf8_bytes: number; evidence_id: string | null; serializer_version: string };
  proposal: null | { replacement_markdown: string; summary: string; assumptions: string[] };
  failure_code: string | null; inserted_in_draft: boolean;
}
const root = (world: string) => `/api/live/agent/worlds/${encodeURIComponent(world)}/build-proposals`;
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { response } = await authenticatedApiFetch(path, init);
  if (!response.ok) throw new Error(`Build proposal unavailable (${response.status}). No new request was sent automatically.`);
  return response.json() as Promise<T>;
}
function checked(record: BuildProposalRecord, world: string, action?: string, conversation?: string) {
  if (record.schema_version !== 'dmb_build_document_proposal_v1' || record.reservation.basis.world_id !== world
    || (action && record.action_id !== action) || (conversation && record.reservation.conversation_id !== conversation)) {
    throw new Error('The returned proposal does not belong to this conversation.');
  }
  return record;
}
export async function composeBuildProposal(body: BuildProposalRequest): Promise<BuildProposalRecord> {
  const reply = await request<{ record: BuildProposalRecord }>(root(body.basis.world_id), { method: 'POST', body: JSON.stringify(body) });
  return checked(reply.record, body.basis.world_id, body.idempotency_key, body.conversation_id);
}
export async function getBuildProposal(world: string, action: string): Promise<BuildProposalRecord> {
  const reply = await request<{ record: BuildProposalRecord }>(`${root(world)}/${encodeURIComponent(action)}`);
  return checked(reply.record, world, action);
}
export async function listBuildProposals(world: string, conversation: string, signal?: AbortSignal): Promise<BuildProposalRecord[]> {
  const reply = await request<{ schema: string; world_id: string; conversation_id: string; records: BuildProposalRecord[] }>(
    `${root(world)}?conversation_id=${encodeURIComponent(conversation)}`, { signal });
  if (reply.schema !== 'dmb_build_proposal_list_v1' || reply.world_id !== world || reply.conversation_id !== conversation) throw new Error('Proposal history scope changed.');
  return reply.records.map(record => checked(record, world, undefined, conversation));
}
export async function reportBuildInsertion(world: string, record: BuildProposalRecord): Promise<BuildProposalRecord> {
  const reply = await request<{ record: BuildProposalRecord }>(`${root(world)}/${encodeURIComponent(record.action_id)}/inserted?expected_revision=${record.revision}`, { method: 'POST' });
  return checked(reply.record, world, record.action_id);
}
export async function getBuildProposalPrompt(world: string, action: string, signal?: AbortSignal) {
  return request<{ schema: string; world_id: string; action_id: string; payload_json: string;
    reference: NonNullable<BuildProposalRecord['authorization']> }>(`${root(world)}/${encodeURIComponent(action)}/prompt`, { signal });
}
