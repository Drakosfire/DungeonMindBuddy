/** A user-approved local handoff; opening never generates, saves or inserts. */
export function SurfaceImagePromptAction({ prompt, unavailableReason, onOpen }: {
  prompt: string;
  unavailableReason: string | null;
  onOpen: ((prompt: string) => void) | undefined;
}) {
  return <div className="surface-image-prompt-action">
    <button type="button" disabled={!onOpen || Boolean(unavailableReason)}
      onClick={() => { if (!unavailableReason) onOpen?.(prompt); }}>
      Open Image Studio
    </button>
    {unavailableReason ? <p role="note">{unavailableReason}</p>
      : <p>Review this prompt, then choose Generate in Image Studio.</p>}
  </div>;
}
