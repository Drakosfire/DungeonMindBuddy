import { useId, useRef, useState } from "react";
import {
  openConversationDraft,
  openVariantReview,
  confirmVariantReview,
  type ConversationVariantReview,
  saveConversationDraft,
  type ConversationDraft,
  type ConversationDraftScope,
} from "../api/conversationDraftApi";

import type { BuildComposeBridge, PreparedBuildProposal } from "../buildSurface/buildComposeBridge";
import { savedConversationVariantHref } from "../statblocks/savedStatblockLocation";
import { StatblockRenderer } from "../statblocks/render/StatblockRenderer";

interface VariantPagePlacement {
  documentId: string;
  bridge: BuildComposeBridge;
}

export function ConversationDraftEditor({ scope, placement }: {
  scope: ConversationDraftScope;
  placement?: VariantPagePlacement;
}) {
  const id = useId();
  const [draft, setDraft] = useState<ConversationDraft | null>(null);
  const [markdown, setMarkdown] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [review, setReview] = useState<{ id: string; data: ConversationVariantReview } | null>(null);
  const [savedVariant, setSavedVariant] = useState(false);

  const pendingPlacement = useRef<{ href: string; prepared: PreparedBuildProposal } | null>(null);
  const [linkedHref, setLinkedHref] = useState<string | null>(null);

  async function saveVariantLink(reviewId: string) {
    if (!placement?.bridge.placeSavedVariantLink) return;
    const variant = { ...scope, reviewId };
    const href = savedConversationVariantHref(variant);
    const { bridge, documentId } = placement;
    setBusy(true);
    setError("");
    try {
      const pending = pendingPlacement.current;
      if (pending && pending.href !== href) {
        throw new Error("Finish saving the previous variant link first.");
      }
      let prepared = pending?.prepared;
      if (!prepared) {
        const captured = await bridge.capture();
        if (captured.basis.document_id !== documentId || captured.basis.world_id !== scope.worldId) {
          throw new Error("Open the original Build page before linking the variant.");
        }
        prepared = await bridge.placeSavedVariantLink!(captured, variant);
        pendingPlacement.current = { href, prepared };
      }
      await bridge.saveProposal(
        prepared.captured.basis, prepared.afterEditorSha256, prepared.afterDraftSha256,
      );
      pendingPlacement.current = null;
      setLinkedHref(href);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not save the variant link.");
    } finally {
      setBusy(false);
    }
  }

  async function inspectVariant(reviewId: string) {
    setBusy(true);
    setError("");
    setSavedVariant(false);
    setReview(null);
    try {
      const data = await openVariantReview(scope, reviewId);
      if (data.revision !== draft?.revision) throw new Error("Reopen the latest draft before reviewing.");
      setReview({ id: reviewId, data });
      setSavedVariant(data.saved === true);
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
                {placement?.bridge.placeSavedVariantLink && <button type="button" disabled={busy || linkedHref === savedConversationVariantHref({ ...scope, reviewId: review.id })}
                  onClick={() => void saveVariantLink(review.id)}>
                  Insert at cursor and save page
                </button>}
                {linkedHref === savedConversationVariantHref({ ...scope, reviewId: review.id }) &&
                  <p role="status">Variant link verified on the saved page.</p>}
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
