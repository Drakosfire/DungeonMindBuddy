import { useEffect, useRef, useState } from 'react';
import { imageMoveReview, type BuildImageMoveReviewRecord } from '../api/buildImageMoveReviewApi';
import { canonical } from '../shared/sourcePassageProtocol';
import type { BuildComposeBridge, PreparedBuildImageMove } from './buildComposeBridge';

interface Props {
  world: string;
  action: string;
  conversation: string;
  documentId: string;
  placementSha256: string;
  savedRevision: number;
  bridge: BuildComposeBridge;
}

export function BuildImageMoveReview({
  world, action, conversation, documentId, placementSha256, savedRevision, bridge,
}: Props) {
  const [review, setReview] = useState<BuildImageMoveReviewRecord | null>(null);
  const [busy, setBusy] = useState(false);
  const [applied, setApplied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const owner = useRef<AbortController | null>(null);
  const applying = useRef(false);
  const confirmed = useRef<string | null>(null);
  const pendingClaim = useRef<{claimId: string; prepared: PreparedBuildImageMove} | null>(null);

  useEffect(() => {
    const scope = new AbortController();
    owner.current = scope;
    applying.current = false;
    confirmed.current = null;
    pendingClaim.current = null;
    setReview(null);
    setApplied(false);
    setError(null);
    setBusy(false);
    void imageMoveReview(world, action, undefined, scope.signal).then(async ({review: record}) => {
      const placementBytes = new TextEncoder().encode(canonical(record.placement));
      const hash = new Uint8Array(await crypto.subtle.digest('SHA-256', placementBytes));
      const digest = Array.from(hash, byte => byte.toString(16).padStart(2, '0')).join('');
      if (digest !== placementSha256 || record.conversation_id !== conversation
        || record.placement.basis.document_id !== documentId) {
        throw new Error('The Image move Review does not match this conversation and Page.');
      }
      if (!scope.signal.aborted) setReview(record);
    }).catch(failure => {
      if (!scope.signal.aborted) setError(failure instanceof Error ? failure.message : String(failure));
    });
    return () => scope.abort();
  }, [world, action, conversation, documentId, placementSha256, bridge]);

  useEffect(() => {
    const scope = owner.current;
    if (!scope || scope.signal.aborted || review?.state !== 'claimed' || !review.claim_id
      || savedRevision !== review.placement.basis.registry_revision + 1
      || confirmed.current === review.claim_id) return;
    confirmed.current = review.claim_id;
    void imageMoveReview(world, action, {operation: 'confirm', claim_id: review.claim_id}, scope.signal)
      .then(({review: saved}) => {
        if (saved.state !== 'saved' || saved.claim_id !== review.claim_id
          || canonical(saved.placement) !== canonical(review.placement)) {
          throw new Error('The saved Page does not match the image move.');
        }
        if (!scope.signal.aborted) setReview(saved);
      }).catch(failure => {
        if (!scope.signal.aborted) setError(failure instanceof Error ? failure.message : String(failure));
      });
  }, [world, action, review, savedRevision]);

  async function apply() {
    const scope = owner.current;
    if (!scope || scope.signal.aborted || applying.current || review?.state !== 'editing'
      || !bridge.prepareImageMove || !bridge.applyPreparedImageMove || !bridge.canReviewImageMove?.(review.placement)) return;
    applying.current = true;
    setBusy(true);
    setError(null);
    try {
      const pending = pendingClaim.current ?? {
        claimId: crypto.randomUUID(), prepared: await bridge.prepareImageMove(review.placement),
      };
      if (scope.signal.aborted) return;
      pendingClaim.current = pending;
      const {claimId, prepared} = pending;
      const {review: claimed, issued} = await imageMoveReview(world, action, {
        operation: 'claim', expected_revision: review.revision, claim_id: claimId,
        editor_json: prepared.editorJson, after_editor_json: prepared.afterEditorJson,
      }, scope.signal);
      if (scope.signal.aborted) return;
      if (claimed.state !== 'claimed' || claimed.claim_id !== claimId
        || canonical(claimed.placement) !== canonical(review.placement)) {
        throw new Error('This Review could not issue a fresh editor action. Send the request again.');
      }
      pendingClaim.current = null;
      setReview(claimed);
      if (!issued) return;
      bridge.applyPreparedImageMove(prepared);
      setApplied(true);
    } catch (failure) {
      if (!scope.signal.aborted) {
        setError(failure instanceof Error ? failure.message : String(failure));
        if (pendingClaim.current) {
          const current = await imageMoveReview(world, action, undefined, scope.signal).catch(() => null);
          if (!scope.signal.aborted && current && canonical(current.review.placement) === canonical(review.placement)
            && current.review.conversation_id === conversation && current.review.state !== 'editing') {
            pendingClaim.current = null;
            setReview(current.review);
          }
        }
      }
    } finally {
      if (!scope.signal.aborted) {
        applying.current = false;
        setBusy(false);
      }
    }
  }

  return <section aria-label="Image move review">
    {review?.state === 'editing' && bridge.canReviewImageMove?.(review.placement)
      && <button type="button" disabled={busy} onClick={() => void apply()}>Apply image move</button>}
    {review?.state === 'claimed' && <p role="status">{applied ? 'Use Save to keep the image move.'
      : 'This review was already claimed. Check the page before saving or sending a new request.'}</p>}
    {review?.state === 'saved' && <p role="status">Image move saved.</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
