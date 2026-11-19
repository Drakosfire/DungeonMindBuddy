import {useRef, useState} from 'react';
import type {SurfaceNativeCompletionV1} from '../../api/types';
import {authenticatedApiFetch} from '../../api/liveApi';

interface Props {
  worldId: string;
  conversationId: string;
  turnId: string;
  completion: SurfaceNativeCompletionV1;
  digest: () => Promise<string>;
  disabled: boolean;
}

export function ConversationLorePageConfirmation({
  worldId, conversationId, turnId, completion, digest, disabled,
}: Props) {
  const inFlight = useRef(false);
  const [saving, setSaving] = useState(false);
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
      const path = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/conversation/lore-pages/confirm`;
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
      if (result.review_sha256 !== reviewSha256 || typeof result.document_id !== 'string') {
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
    {savedId
      ? <a href={'/build?' + new URLSearchParams({world: worldId, documentId: savedId})}>Open saved page</a>
      : <button type="button" disabled={disabled || saving} onClick={() => void confirm()}>
        {saving ? 'Saving…' : `Confirm save of ${draft.destination.title}`}
      </button>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
