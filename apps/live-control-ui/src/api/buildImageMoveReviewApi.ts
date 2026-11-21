import type { BuildProposalBasis } from './buildDocumentProposalApi';
import { authenticatedApiFetch } from './liveApi';

export interface BuildImageMoveCapture {
  basis: BuildProposalBasis;
  conversation_id: string;
  expected_pointer_revision: number;
  editor_json: string;
  author_selected_block_id: string | null;
}

export interface BuildImageMovePlacement {
  basis: BuildProposalBasis;
  presentation_sha256: string;
  row_id: string;
  source_slot_id: string;
  destination_slot_id: string;
  image_block_id: string;
}

export interface BuildImageMoveReviewRecord {
  schema: 'dmb_build_image_move_review_v1';
  action_id: string;
  conversation_id: string;
  expected_pointer_revision: number;
  placement: BuildImageMovePlacement;
  after_editor_sha256: string;
  after_presentation_sha256: string;
  state: 'editing' | 'claimed' | 'saved';
  claim_id: string | null;
  saved_revision: number | null;
  revision: number;
  updated_at: string;
}

type Command = {
  operation: 'claim';
  expected_revision: number;
  claim_id: string;
  editor_json: string;
  after_editor_json: string;
} | {operation: 'confirm'; claim_id: string};

const digest = /^[0-9a-f]{64}$/;
const uuid = /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i;
const text = (value: unknown): value is string => typeof value === 'string' && value.length > 0;
const positive = (value: number) => Number.isSafeInteger(value) && value >= 1;

export function isBuildImageMoveCapture(value: unknown, world: string, document: string, revision: number, content: string): value is BuildImageMoveCapture {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const capture = value as BuildImageMoveCapture;
  const basis = capture.basis;
  return basis?.world_id === world && basis.document_id === document && basis.registry_revision === revision
    && basis.content_sha256 === content && basis.draft_sha256 === content && basis.visibility === 'internal'
    && text(basis.editor_sha256) && digest.test(basis.editor_sha256)
    && text(capture.conversation_id) && uuid.test(capture.conversation_id) && positive(capture.expected_pointer_revision)
    && text(capture.editor_json) && capture.editor_json.length <= 1_000_000
    && (capture.author_selected_block_id === null || text(capture.author_selected_block_id));
}

export class BuildImageMoveReviewError extends Error {
  constructor(readonly status: number) {
    super(status === 409 ? 'The page or image move changed. Reopen the page before continuing.'
      : 'The image move review is unavailable.');
  }
}

export async function imageMoveReview(world: string, action: string, command?: Command, signal?: AbortSignal) {
  const url = `/api/live/agent/worlds/${encodeURIComponent(world)}/build-image-moves/${encodeURIComponent(action)}/review`;
  const {response} = await authenticatedApiFetch(url, command ? {
    method: 'POST', cache: 'no-store', signal, body: JSON.stringify(command),
  } : {cache: 'no-store', signal});
  if (!response.ok) throw new BuildImageMoveReviewError(response.status);
  const result = await response.json() as {review: BuildImageMoveReviewRecord; issued: boolean};
  const review = result?.review;
  const placement = review?.placement;
  const basis = placement?.basis;
  if (typeof result?.issued !== 'boolean' || review?.schema !== 'dmb_build_image_move_review_v1'
    || review.action_id !== action || !text(review.conversation_id) || !uuid.test(review.conversation_id)
    || !positive(review.revision) || !positive(review.expected_pointer_revision)
    || !['editing', 'claimed', 'saved'].includes(review.state)
    || (review.state === 'editing' ? review.claim_id !== null : !text(review.claim_id) || !uuid.test(review.claim_id))
    || (review.state === 'saved' ? review.saved_revision !== (basis?.registry_revision ?? -1) + 1 : review.saved_revision !== null)
    || !placement || !basis || basis.world_id !== world || basis.visibility !== 'internal' || basis.content_sha256 !== basis.draft_sha256
    || !positive(basis.registry_revision) || !text(basis.document_id)
    || ![basis.content_sha256, basis.editor_sha256, placement.presentation_sha256, review.after_editor_sha256,
      review.after_presentation_sha256].every(hash => text(hash) && digest.test(hash))
    || ![placement.row_id, placement.source_slot_id, placement.destination_slot_id, placement.image_block_id].every(text)
    || placement.source_slot_id === placement.destination_slot_id
    || (result.issued && (command?.operation !== 'claim' || review.state !== 'claimed' || review.claim_id !== command.claim_id))) {
    throw new Error('The saved review does not match this Build image move.');
  }
  return result;
}
