import { useId, useState } from "react";
import {
  openConversationDraft,
  openVariantReview,
  confirmVariantReview,
  type ConversationVariantReview,
  saveConversationDraft,
  type ConversationDraft,
  type ConversationDraftScope,
} from "../api/conversationDraftApi";

import { savedConversationVariantHref } from "../statblocks/savedStatblockLocation";
import { StatblockRenderer } from "../statblocks/render/StatblockRenderer";

export function ConversationDraftEditor({ scope }: { scope: ConversationDraftScope }) {
  const id = useId();
  const [draft, setDraft] = useState<ConversationDraft | null>(null);
  const [markdown, setMarkdown] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [review, setReview] = useState<{ id: string; data: ConversationVariantReview } | null>(null);
  const [savedVariant, setSavedVariant] = useState(false);

  async function inspectVariant(reviewId: string) {
    setBusy(true);
    setError("");
    setSavedVariant(false);
    setReview(null);
    try {
      const data = await openVariantReview(scope, reviewId);
      if (data.revision !== draft?.revision) throw new Error("Reopen the latest draft before reviewing.");
      setReview({ id: reviewId, data });
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not open the variant review.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmVariant() {
    if (!draft || !review || markdown !== draft.markdown) return;
    setBusy(true);
    setError("");
    try {
      await confirmVariantReview(scope, review.id);
      setSavedVariant(true);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not save the variant.");
    } finally {
      setBusy(false);
    }
  }

  async function open() {
    setReview(null);
    setSavedVariant(false);
    setBusy(true);
    setError("");
    try {
      const latest = await openConversationDraft(scope);
      setDraft(latest);
      setMarkdown(latest.markdown);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not open the draft.");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!draft) return;
    setReview(null);
    setSavedVariant(false);
    setBusy(true);
    setError("");
    try {
      const saved = await saveConversationDraft(scope, draft.revision, markdown);
      setDraft(saved);
      setMarkdown(saved.markdown);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not save the draft.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Conversation draft">
      {draft ? (
        <>
          <label htmlFor={id}>Draft Markdown</label>
          <textarea id={id} value={markdown} disabled={busy} onChange={event => setMarkdown(event.target.value)} />
          <button type="button" disabled={busy || markdown === draft.markdown} onClick={() => void save()}>
            Save draft
          </button>
          {markdown === draft.markdown && draft.variant_review_ids?.map(reviewId => (
            <button key={reviewId} type="button" disabled={busy} onClick={() => void inspectVariant(reviewId)}>
              Review statblock variant
            </button>
          ))}
          {review && markdown === draft.markdown && (
            <section aria-label="Statblock variant review">
              <StatblockRenderer chrome="campaign" draft={{
                definition: review.data.definition,
                hitPoints: summary => summary,
                ruleEditor: () => null,
              }} />
              <button type="button" disabled={busy || savedVariant} onClick={() => void confirmVariant()}>
                Confirm and save as new statblock
              </button>
              {savedVariant && <>
                <p role="status">Statblock variant saved.</p>
                <a href={savedConversationVariantHref({ ...scope, reviewId: review.id })}>Open saved variant</a>
              </>}
            </section>
          )}
          {error && (
            <button type="button" disabled={busy} onClick={() => void open()}>
              Discard local edits and reopen
            </button>
          )}
        </>
      ) : (
        <button type="button" disabled={busy} onClick={() => void open()}>
          Open draft
        </button>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
