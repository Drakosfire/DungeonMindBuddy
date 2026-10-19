import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import "./FloatingSceneNotes.css";

/** Presentation only: the cockpit retains the note target, draft and writer. */
export function FloatingSceneNotes({ sceneTitle, status, available = true, suspended = false, children }: {
  sceneTitle: string | null;
  status: string;
  available?: boolean;
  suspended?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const toggle = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (open && !suspended) panel.current?.querySelector<HTMLTextAreaElement>("textarea")?.focus();
  }, [open, suspended]);
  const close = () => { setOpen(false); toggle.current?.focus(); };
  return (
    <aside className="floating-scene-notes" data-open={open ? "true" : "false"}
      data-testid="floating-scene-notes" hidden={suspended}
      onKeyDown={event => {
        if (event.key === "Escape" && open) {
          event.preventDefault(); event.stopPropagation(); close();
        }
      }}>
      <button ref={toggle} type="button" className="floating-scene-notes__toggle"
        aria-expanded={open} aria-controls={id} disabled={!available}
        onClick={() => setOpen(value => !value)}>
        <span className="floating-scene-notes__target">Scene notes — {sceneTitle ?? "No current scene"}</span>
        <span className="floating-scene-notes__summary">{status} · {open ? "Collapse" : "Open"}</span>
      </button>
      <div ref={panel} id={id} className="floating-scene-notes__panel" hidden={!open}
        role="region" aria-label={`Notes for current scene: ${sceneTitle ?? "No current scene"}`}>
        {children}
      </div>
    </aside>
  );
}
