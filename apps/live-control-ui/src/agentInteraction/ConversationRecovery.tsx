/** A terminal question becomes a new draft, never a replay of the historical request. */
export function ConversationRecovery({ question, draft, blocked, onRestore }: {
  question: string; draft: string; blocked: boolean; onRestore: (question: string) => void;
}) {
  const hasOtherDraft = Boolean(draft.trim()) && draft !== question;
  return <span>
    <button type="button" disabled={blocked || hasOtherDraft} onClick={() => onRestore(question)}
      title={hasOtherDraft ? "Keep or clear your current draft before retrying this question." : blocked ? "Resolve the current request before preparing a retry." : "Restore this question, then review and send using current saved work."}>
      Retry question…
    </button>
    {!hasOtherDraft && <small> Review and send again using current saved work.</small>}
    {hasOtherDraft && <small> Your current draft is kept. Send or clear it before retrying.</small>}
  </span>;
}
