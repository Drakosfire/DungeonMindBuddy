import { useEffect, useId, useRef, useState, type ReactNode, type RefObject } from "react";
import "./FloatingSceneNotes.css";

/** Presentation only: the cockpit retains the note target, draft and writer. */
export function FloatingSceneNotes({ sceneTitle, status, available = true, suspended = false, open: controlledOpen, onOpenChange, returnFocusRef, hideToggle = false, children }: {
  sceneTitle: string | null;
  status: string;
  available?: boolean;
  suspended?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  returnFocusRef?: RefObject<HTMLElement | null>;
  hideToggle?: boolean;
  children: ReactNode;
}) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen ?? internalOpen;
  const id = useId();
  const toggle = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (open && !suspended) panel.current?.querySelector<HTMLTextAreaElement>("textarea")?.focus();
  }, [open, suspended]);
  const setOpen = (value: boolean) => { setInternalOpen(value); onOpenChange?.(value); };
  const close = () => { setOpen(false); (returnFocusRef?.current ?? toggle.current)?.focus(); };
  return (
    <aside className="floating-scene-notes" data-open={open ? "true" : "false"}
      data-testid="floating-scene-notes" hidden={suspended || (hideToggle && !open)}
      onKeyDown={event => {
        if (event.key === "Escape" && open) {
          event.preventDefault(); event.stopPropagation(); close();
        }
      }}>
      {!hideToggle ? <button ref={toggle} type="button" className="floating-scene-notes__toggle"
        aria-expanded={open} aria-controls={id} disabled={!available}
        onClick={() => setOpen(!open)}>
        <span className="floating-scene-notes__target">Scene notes — {sceneTitle ?? "No current scene"}</span>
        <span className="floating-scene-notes__summary">{status} · {open ? "Collapse" : "Open"}</span>
      </button> : null}
      <div ref={panel} id={id} className="floating-scene-notes__panel" hidden={!open}
        role="region" aria-label={`Notes for current scene: ${sceneTitle ?? "No current scene"}`}>
        {children}
      </div>
    </aside>
  );
}
