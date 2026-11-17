import { useId, useState } from "react";
import {
  openConversationDraft,
  saveConversationDraft,
  type ConversationDraft,
  type ConversationDraftScope,
} from "../api/conversationDraftApi";

export function ConversationDraftEditor({ scope }: { scope: ConversationDraftScope }) {
  const id = useId();
  const [draft, setDraft] = useState<ConversationDraft | null>(null);
  const [markdown, setMarkdown] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function open() {
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
