import {useRef, useState} from 'react';
import type {SurfaceNativeCompletionV1} from '../../api/types';
import {authenticatedApiFetch} from '../../api/liveApi';
import {shouldInterceptPrimaryNavigationClick} from '../../chrome/appNavigation';

interface Props {
  worldId: string;
  conversationId: string;
  turnId: string;
  completion: SurfaceNativeCompletionV1;
  digest: () => Promise<string>;
  disabled: boolean;
  selectDocument?: (id: string) => Promise<boolean>;
}

export function ConversationLorePageConfirmation({
  worldId, conversationId, turnId, completion, digest, disabled, selectDocument,
}: Props) {
  const inFlight = useRef(false);
  const [saving, setSaving] = useState(false);
  const [preparedDigest, setPreparedDigest] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const draft = completion.collaboration;
  if (draft?.kind !== 'lore_page') return null;

  async function confirm() {
    if (disabled || inFlight.current || savedId) return;
    inFlight.current = true;
    setSaving(true);
    setError(null);
    try {
      const reviewSha256 = await digest();
      if (preparedDigest !== null && preparedDigest !== reviewSha256) {
        setPreparedDigest(null);
        throw new Error('This draft changed. Open its current review before saving.');
      }
      const action = preparedDigest === null ? 'review' : 'confirm';
      const path = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/conversation/lore-pages/${action}`;
      const {response} = await authenticatedApiFetch(path, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          conversation_id: conversationId, turn_id: turnId, review_sha256: reviewSha256,
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(typeof result.detail === 'string' ? result.detail : 'The lore page could not be saved.');
      }
      if (result.review_sha256 !== reviewSha256) {
        throw new Error('The save review did not match this draft.');
      }
      if (action === 'review') {
        setPreparedDigest(reviewSha256);
        return;
      }
      if (typeof result.document_id !== 'string') {
        throw new Error('The save receipt did not match this draft.');
      }
      setSavedId(result.document_id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The lore page could not be saved.');
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  }

  return <div>
    {draft.open_questions && <section aria-label="Open questions">
      <h4>Open questions</h4>
      <ul>{draft.open_questions.map((question, index) => <li key={index}>{question}</li>)}</ul>
    </section>}
    {savedId
      ? <a href={'/build?' + new URLSearchParams({world: worldId, documentId: savedId})} onClick={event => {
          if (!shouldInterceptPrimaryNavigationClick(event, event.currentTarget)) return;
          event.preventDefault();
          if (!selectDocument) { setError('The page selector is unavailable. Your current page and conversation are retained.'); return; }
          setError(null);
          void selectDocument(savedId).then(opened => {
            if (!opened) setError('The saved page could not be opened. Your current page and conversation are retained.');
          }).catch(() => setError('The saved page could not be opened. Your current page and conversation are retained.'));
        }}>Open saved page</a>
      : <button type="button" disabled={disabled || saving} onClick={() => void confirm()}>
        {saving ? 'Working…' : preparedDigest
          ? `Confirm save of ${draft.destination.title}`
          : `Review save of ${draft.destination.title}`}
      </button>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
