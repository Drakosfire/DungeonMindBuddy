import { isValidGraphNodeId } from '../tiptap/references/runbookReferences';
import { isBuildProseBoundaryTarget, type BuildProposalBasis, type BuildProseBoundaryTarget } from './buildDocumentProposalApi';
import { authenticatedApiFetch } from './liveApi';
import type { AuthoredGraphReferenceV1 } from './types';

export interface BuildGraphReferencePlacement {
  basis: BuildProposalBasis;
  boundary: BuildProseBoundaryTarget;
  reference: AuthoredGraphReferenceV1;
  entity_kind: string;
}

export interface BuildGraphReferenceApply {
  apply_id: string;
  editor_sha256: string;
  draft_sha256: string;
  content_sha256: string;
  presentation_sha256: string | null;
}

export interface BuildGraphReferenceReviewRecord {
  schema: 'dmb_build_graph_reference_review_v1';
  action_id: string;
  placement: BuildGraphReferencePlacement;
  revision: number;
  state: 'editing' | 'applying' | 'applied' | 'discarded';
  apply: BuildGraphReferenceApply | null;
  saved_revision: number | null;
}

type Command = {
  operation: 'prepare';
  expected_revision: number;
  apply: BuildGraphReferenceApply;
  editor_json: string;
  draft_markdown: string;
  after_editor_json: string;
  after_draft_markdown: string;
} | {operation: 'authorize_save' | 'confirm'; apply_id: string}
  | {operation: 'discard'; expected_revision: number};

export class BuildGraphReferenceReviewError extends Error {
  constructor(readonly status: number) {
    super(status === 409 ? 'The page or Graph reference changed. Review the current source before continuing.'
      : 'The Graph reference review is unavailable.');
  }
}

export async function graphReferenceReview(world: string, action: string, command?: Command, signal?: AbortSignal) {
  const url = `/api/live/agent/worlds/${encodeURIComponent(world)}/build-proposals/${encodeURIComponent(action)}/review`;
  const { response } = await authenticatedApiFetch(url, command ? {
    method: 'POST', cache: 'no-store', signal,
    body: JSON.stringify({schema: 'dmb_build_graph_reference_command_v1', ...command}),
  } : {cache: 'no-store', signal});
  if (!response.ok) throw new BuildGraphReferenceReviewError(response.status);
  const review = await response.json() as BuildGraphReferenceReviewRecord;
  const placement = review?.placement;
  const reference = placement?.reference;
  if (review?.schema !== 'dmb_build_graph_reference_review_v1' || review.action_id !== action
    || !Number.isSafeInteger(review.revision) || review.revision < 1
    || !['editing', 'applying', 'applied', 'discarded'].includes(review.state)
    || (review.state === 'applying' || review.state === 'applied') !== !!review.apply
    || placement?.basis?.world_id !== world || placement.basis.visibility !== 'internal' || placement.basis.selection
    || !isBuildProseBoundaryTarget(placement.boundary) || typeof placement.entity_kind !== 'string' || !placement.entity_kind
    || reference?.schema !== 'dmb_authored_graph_reference_v1' || reference.managed_world_id !== world
    || typeof reference.node_id !== 'string' || !isValidGraphNodeId(reference.node_id)
    || typeof reference.label !== 'string' || !reference.label.trim()) {
    throw new Error('The saved review does not match this Build Graph reference.');
  }
  return review;
}
