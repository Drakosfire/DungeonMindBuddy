import { useId, useLayoutEffect, useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import "./ConversationDock.css";

export interface ConversationDockProps {
  reader: ReactNode;
  messages: ReactNode;
  composer: ReactNode;
  title?: string;
  contextLabel?: string;
  contextDetails?: ReactNode;
  collapsedPreview?: ReactNode;
  headerActions?: ReactNode;
  initialExpanded?: boolean;
  initialHeight?: number;
  minHeight?: number;
  maxHeight?: number;
  minimumReaderHeight?: number;
  onExpandedChange?: (expanded: boolean) => void;
  className?: string;
  style?: CSSProperties;
}

/**
 * A height-owning workspace's reader and bottom conversation layout.
 * Slots retain their mounted state through collapse. Callers own messages,
 * compact composer behavior, verified context and all external actions.
 * Paint through --conversation-dock-* variables; no application providers.
 */
export function ConversationDock({
  reader, messages, composer, title = "Buddy", contextLabel = "Context",
  contextDetails, collapsedPreview, headerActions, initialExpanded = false,
  initialHeight = 340, minHeight = 280, maxHeight = 520,
  minimumReaderHeight = 160, onExpandedChange, className = "", style,
}: ConversationDockProps) {
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const messageRegion = useRef<HTMLDivElement>(null);
  const composerRegion = useRef<HTMLDivElement>(null);
  const scrollPosition = useRef(0);
  const drag = useRef<{ y: number; height: number; pointerId: number } | null>(null);
  const [expanded, setExpanded] = useState(initialExpanded);
  const [contextOpen, setContextOpen] = useState(false);
  const [requestedHeight, setRequestedHeight] = useState(initialHeight);
  const [containerHeight, setContainerHeight] = useState<number | null>(null);
  const [resizing, setResizing] = useState(false);
  const hasContext = contextDetails !== undefined && contextDetails !== null && contextDetails !== false;

  const reserve = containerHeight === null ? minimumReaderHeight : Math.min(minimumReaderHeight, containerHeight * 0.3);
  const ceiling = Math.max(160, Math.min(maxHeight, containerHeight === null ? maxHeight : containerHeight - reserve));
  const floor = Math.min(Math.max(160, minHeight), ceiling);
  const height = Math.max(floor, Math.min(ceiling, requestedHeight));

  useLayoutEffect(() => {
    const element = root.current;
    if (!element) return;
    const measure = () => {
      const next = element.getBoundingClientRect().height;
      if (next > 0) setContainerHeight(next);
    };
    measure();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(measure);
      observer.observe(element);
      return () => observer.disconnect();
    }
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  useLayoutEffect(() => {
    if (expanded && messageRegion.current) messageRegion.current.scrollTop = scrollPosition.current;
  }, [expanded]);

  useLayoutEffect(() => {
    if (!hasContext) setContextOpen(false);
  }, [hasContext]);

  function changeExpanded(next: boolean) {
    if (next === expanded) return;
    if (!next) {
      scrollPosition.current = messageRegion.current?.scrollTop ?? 0;
      setContextOpen(false);
      const focused = document.activeElement;
      if (focused && messageRegion.current?.contains(focused)) {
        composerRegion.current?.querySelector<HTMLElement>("textarea,input,button,select")?.focus({ preventScroll: true });
      }
    }
    setExpanded(next);
    onExpandedChange?.(next);
  }

  function resizeFromKeyboard(event: KeyboardEvent<HTMLButtonElement>) {
    const requested = event.key === "ArrowUp" ? height + 24
      : event.key === "ArrowDown" ? height - 24
      : event.key === "Home" ? floor
      : event.key === "End" ? ceiling : null;
    if (requested === null) return;
    event.preventDefault();
    changeExpanded(true);
    setRequestedHeight(Math.max(floor, Math.min(ceiling, requested)));
  }

  function startResize(event: PointerEvent<HTMLButtonElement>) {
    if (event.button !== 0 || event.isPrimary === false || drag.current) return;
    drag.current = { y: event.clientY, height, pointerId: event.pointerId };
    event.currentTarget.setPointerCapture?.(event.pointerId);
    changeExpanded(true);
    setResizing(true);
  }

  function moveResize(event: PointerEvent<HTMLButtonElement>) {
    if (!drag.current || drag.current.pointerId !== event.pointerId) return;
    setRequestedHeight(Math.max(floor, Math.min(ceiling, drag.current.height + drag.current.y - event.clientY)));
  }

  function finishResize(event: PointerEvent<HTMLButtonElement>) {
    if (drag.current?.pointerId !== event.pointerId) return;
    drag.current = null;
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture?.(event.pointerId);
    setResizing(false);
  }

  const variables = {
    ...style,
    "--conversation-dock-height": `${height}px`,
  } as CSSProperties;

  return (
    <div ref={root} className={`conversation-dock ${expanded ? "is-expanded" : ""} ${resizing ? "is-resizing" : ""} ${className}`.trim()} style={variables}>
      <div className="conversation-dock__reader" aria-label="Document workspace">{reader}</div>
      <section className="conversation-dock__conversation" aria-label={`${title} conversation`}>
        <button type="button" role="separator" aria-label={`Resize ${title} conversation`} aria-orientation="horizontal"
          aria-controls={`${id}-messages`} aria-valuemin={floor} aria-valuemax={ceiling} aria-valuenow={height}
          className="conversation-dock__resize" onKeyDown={resizeFromKeyboard}
          onPointerDown={startResize} onPointerMove={moveResize} onPointerUp={finishResize} onPointerCancel={finishResize} onLostPointerCapture={finishResize}>
          <span aria-hidden="true" />
        </button>
        <header className="conversation-dock__header">
          <strong>{title}</strong>
          {hasContext && <button type="button" className="conversation-dock__context-toggle"
            aria-expanded={contextOpen} aria-controls={`${id}-context`} title={contextLabel}
            onClick={() => { changeExpanded(true); setContextOpen(!contextOpen); }}>
            <span>{contextLabel}</span><span aria-hidden="true">▾</span>
          </button>}
          <div className="conversation-dock__actions">{headerActions}</div>
          <button type="button" className="conversation-dock__toggle" aria-expanded={expanded}
            aria-controls={`${id}-messages`} onClick={() => changeExpanded(!expanded)}>{expanded ? "Collapse" : "Open chat"}</button>
        </header>
        <div id={`${id}-context`} className="conversation-dock__context" hidden={!contextOpen}>{contextDetails}</div>
        <div ref={messageRegion} id={`${id}-messages`} className="conversation-dock__messages" role="log"
          aria-label={`${title} messages`} hidden={!expanded}
          onScroll={() => { if (expanded) scrollPosition.current = messageRegion.current?.scrollTop ?? 0; }}>{messages}</div>
        {collapsedPreview !== undefined && <div className="conversation-dock__preview" hidden={expanded}>{collapsedPreview}</div>}
        <div ref={composerRegion} className="conversation-dock__composer">{composer}</div>
      </section>
    </div>
  );
}
