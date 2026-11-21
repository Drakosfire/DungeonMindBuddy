import { useEffect, useRef, useState } from 'react';
import {
  BuildGraphReferenceReviewError, graphReferenceReview,
  type BuildGraphReferenceApply, type BuildGraphReferenceReviewRecord,
} from '../api/buildGraphReferenceReviewApi';
import { canonical } from '../shared/sourcePassageProtocol';
import type { BuildComposeBridge, PreparedBuildGraphReference } from './buildComposeBridge';

export function BuildGraphReferenceReview({world,action,bridge,onComplete,conversationId,documentId,placementSha256}: {
  world: string;
  action: string;
  bridge: BuildComposeBridge;
  onComplete?: (state: 'applied' | 'discarded') => void;
  conversationId?: string;
  documentId?: string;
  placementSha256?: string;
}) {
  const [review,setReview] = useState<BuildGraphReferenceReviewRecord | null>(null);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState<string | null>(null);
  const scope = useRef<AbortController | null>(null);
  const submitting = useRef(false);

  useEffect(() => {
    const owner = new AbortController();
    scope.current = owner;
    submitting.current = false;
    setReview(null);
    setBusy(false);
    setError(null);
    void graphReferenceReview(world,action,undefined,owner.signal).then(async result => {
      if (placementSha256) {
        const bytes = new TextEncoder().encode(canonical(result.placement));
        const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),
          byte => byte.toString(16).padStart(2,'0')).join('');
        if (digest !== placementSha256 || result.conversation_id !== conversationId
          || result.placement.basis.document_id !== documentId) {
          throw new Error('The saved review does not match this conversation and page.');
        }
      }
      if (!owner.signal.aborted) setReview(result);
    }).catch(failure => {
      if (!owner.signal.aborted) setError(String(failure.message ?? failure));
    });
    return () => owner.abort();
  }, [world,action,bridge,conversationId,documentId,placementSha256]);

  async function submit(intent: 'apply' | 'discard') {
    const owner = scope.current;
    if (!review || review.action_id !== action || review.placement.basis.world_id !== world
      || !owner || owner.signal.aborted || submitting.current) return;
    const signal = owner.signal;
    submitting.current = true;
    setBusy(true);
    setError(null);
    const command = (body: NonNullable<Parameters<typeof graphReferenceReview>[2]>) =>
      graphReferenceReview(world,action,body,signal);
    function settle(result: BuildGraphReferenceReviewRecord, state: 'applied' | 'discarded') {
      if (signal.aborted) return;
      if (result.state !== state || canonical(result.placement) !== canonical(review?.placement))
        throw new Error('The saved result does not match this reference. Reopen the review.');
      setReview(result);
      onComplete?.(state);
    }
    try {
      if (intent === 'discard') {
        settle(await command({operation:'discard',expected_revision:review.revision}),'discarded');
        return;
      }
      const {basis,boundary} = review.placement;
      let apply = review.apply;
      let prepared: PreparedBuildGraphReference | undefined;
      if (apply) {
        // A lost acknowledgement may leave the Content revision committed already.
        try {
          settle(await command({operation:'confirm',apply_id:apply.apply_id}),'applied');
          return;
        } catch (failure) {
          if (!(failure instanceof BuildGraphReferenceReviewError) || failure.status !== 409) throw failure;
        }
      }
      if (signal.aborted) return;
      const inspected = apply ? await bridge.inspectProposal(basis,apply.editor_sha256,apply.draft_sha256,boundary) : undefined;
      if (inspected?.state === 'changed' || inspected?.savedProjection)
        throw new Error('The current working copy differs from this reference. Reopen the original page to check it.');
      if (signal.aborted) return;
      if (!inspected || inspected.state === 'before') {
        if (!bridge.prepareGraphReference || !bridge.applyGraphReference) throw new Error('Open the editable Build page to place this reference.');
        prepared = await bridge.prepareGraphReference(review.placement);
        if (signal.aborted) return;
        const next: BuildGraphReferenceApply = {...prepared.postimage,apply_id: apply?.apply_id ?? crypto.randomUUID()};
        if (apply && canonical(apply) !== canonical(next))
          throw new Error('The prepared insertion changed. Reopen the original page before continuing.');
        const result = await command({operation:'prepare',expected_revision:review.revision,apply:next,
          editor_json:prepared.captured.editorJson,draft_markdown:prepared.captured.draftMarkdown,
          after_editor_json:prepared.afterEditorJson,after_draft_markdown:prepared.afterDraft});
        if (signal.aborted) return;
        if (result.state === 'applied') { settle(result,'applied'); return; }
        if (result.state !== 'applying' || canonical(result.apply) !== canonical(next)
          || canonical(result.placement) !== canonical(review.placement))
          throw new Error('The saved preparation does not match this reference. Reopen the review.');
        apply = next;
        setReview(result);
      }
      if (!apply) throw new Error('The saved review has no prepared insertion. Reopen the review.');
      const permitted = await command({operation:'authorize_save',apply_id:apply.apply_id});
      if (signal.aborted) return;
      if (permitted.state !== 'applying' || canonical(permitted.apply) !== canonical(apply)
        || canonical(permitted.placement) !== canonical(review.placement))
        throw new Error('The save permission does not match this reference. Reopen the review.');
      if (prepared) bridge.applyGraphReference?.(prepared);
      await bridge.saveProposal(basis,apply.editor_sha256,apply.draft_sha256,undefined,boundary);
      if (!signal.aborted) settle(await command({operation:'confirm',apply_id:apply.apply_id}),'applied');
    } catch (failure) {
      if (!signal.aborted) {
        setError(failure instanceof Error ? failure.message : String(failure));
        // A dropped reply can leave a durable apply receipt even if this tab
        // has not yet inserted it. Recover the ID before the next author action.
        const refreshed = await graphReferenceReview(world,action,undefined,signal).catch(() => null);
        if (!signal.aborted && refreshed && canonical(refreshed.placement) === canonical(review.placement)) setReview(refreshed);
      }
    } finally {
      if (!signal.aborted) { submitting.current = false; setBusy(false); }
    }
  }

  const current = review?.action_id === action && review.placement.basis.world_id === world ? review : null;
  return <section aria-label="Graph reference review">
    {current && <>
      <strong>{current.placement.reference.label}</strong>
      <p>{current.placement.entity_kind} · {current.placement.boundary.operation === 'insert_before' ? 'Before' : 'After'} the requested paragraph</p>
      {current.state === 'applied' && <p role="status">Graph reference saved.</p>}
      {current.state === 'discarded' && <p role="status">Graph reference discarded.</p>}
      {(current.state === 'editing' || current.state === 'applying') && <>
        <button type="button" disabled={busy} onClick={() => void submit('apply')}>
          {current.state === 'editing' ? 'Insert and save reference' : 'Finish saving reference'}
        </button>
        {current.state === 'editing' && <button type="button" disabled={busy} onClick={() => void submit('discard')}>Discard</button>}
      </>}
    </>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
