import { useEffect, useLayoutEffect, useId, useRef, useState, type ReactNode, type RefObject, type PointerEvent } from "react";
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
  const floating = useRef<HTMLElement>(null);
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);
  const drag = useRef<{ id: number; x: number; y: number; originX: number; originY: number } | null>(null);
  const clamp = (point: { x: number; y: number }) => {
    const element = floating.current;
    const rect = element?.getBoundingClientRect();
    const workspace = element?.closest(".app-chrome-play-workspace")?.getBoundingClientRect();
    const header = element?.closest(".app-shell-layout")?.querySelector(".app-chrome-header")?.getBoundingClientRect();
    const bottomChat = document.querySelector('.agent-interaction-shell.open[data-surface-id="play"][data-play-layout="bottom"]')?.getBoundingClientRect();
    const left = Math.max(8, workspace?.left ?? 0);
    const top = Math.max(8, (header?.bottom ?? 0) + 8);
    const right = Math.min(window.innerWidth - 8, workspace?.right ?? window.innerWidth);
    const bottom = Math.min(window.innerHeight - 8, bottomChat?.top ?? window.innerHeight);
    return { x: Math.max(left, Math.min(right - (rect?.width ?? 0), point.x)), y: Math.max(top, Math.min(bottom - (rect?.height ?? 0), point.y)) };
  };
  useLayoutEffect(() => {
    if (!open || suspended) { drag.current = null; return; }
    const fit = () => setPosition(current => {
      const rect = floating.current?.getBoundingClientRect();
      const next = clamp(current ?? { x: rect?.left ?? 16, y: rect?.top ?? 100 });
      return current?.x === next.x && current?.y === next.y ? current : next;
    });
    fit();
    window.addEventListener("resize", fit);
    const observer = typeof ResizeObserver === "function" ? new ResizeObserver(fit) : null;
    if (floating.current) observer?.observe(floating.current);
    const workspace = floating.current?.closest(".app-chrome-play-workspace");
    if (workspace) observer?.observe(workspace);
    return () => { window.removeEventListener("resize", fit); observer?.disconnect(); };
  }, [open, suspended]);
  const stopDrag = (event: PointerEvent<HTMLButtonElement>) => {
    if (drag.current?.id !== event.pointerId) return;
    drag.current = null;
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  };

  useEffect(() => {
    if (open && !suspended) panel.current?.querySelector<HTMLTextAreaElement>("textarea")?.focus();
  }, [open, suspended]);
  const setOpen = (value: boolean) => { setInternalOpen(value); onOpenChange?.(value); };
  const close = () => { setOpen(false); (returnFocusRef?.current ?? toggle.current)?.focus(); };
  return (
    <aside ref={floating} style={position ? { left: position.x, top: position.y, bottom: "auto", right: "auto" } : undefined} className="floating-scene-notes" data-open={open ? "true" : "false"}
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
      {open ? <div className="floating-scene-notes__header">
        <button type="button" className="floating-scene-notes__move" aria-label="Move scene notes" title="Drag to move notes, or use arrow keys"
          onPointerDown={event => {
            if (event.button !== 0) return;
            event.preventDefault();
            const rect = floating.current?.getBoundingClientRect();
            drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY, originX: rect?.left ?? 16, originY: rect?.top ?? 100 };
            event.currentTarget.setPointerCapture?.(event.pointerId);
          }}
          onPointerMove={event => {
            const start = drag.current;
            if (!start || start.id !== event.pointerId) return;
            setPosition(clamp({ x: start.originX + event.clientX - start.x, y: start.originY + event.clientY - start.y }));
          }}
          onPointerUp={stopDrag} onPointerCancel={stopDrag} onLostPointerCapture={() => { drag.current = null; }}
          onKeyDown={event => {
            const step = event.shiftKey ? 48 : 16;
            const delta = event.key === "ArrowLeft" ? [-step, 0] : event.key === "ArrowRight" ? [step, 0] : event.key === "ArrowUp" ? [0, -step] : event.key === "ArrowDown" ? [0, step] : null;
            if (!delta) return;
            event.preventDefault();
            const rect = floating.current?.getBoundingClientRect();
            setPosition(current => clamp({ x: (current?.x ?? rect?.left ?? 16) + delta[0], y: (current?.y ?? rect?.top ?? 100) + delta[1] }));
          }}>
          <span>⠿ Scene notes — {sceneTitle ?? "No current scene"}</span><small>{status}</small>
        </button>
        <button type="button" className="floating-scene-notes__collapse" aria-label="Collapse scene notes" onClick={close}>−</button>
      </div> : null}
      <div ref={panel} id={id} className="floating-scene-notes__panel" hidden={!open}
        role="region" aria-label={`Notes for current scene: ${sceneTitle ?? "No current scene"}`}>
        {children}
      </div>
    </aside>
  );
}
