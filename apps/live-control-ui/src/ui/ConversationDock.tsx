import { useId, useLayoutEffect, useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import "./ConversationDock.css";

export interface ConversationDockProps {
  reader: ReactNode;
  readerLabel?: string;
  conversationLabel?: string;
  messages: ReactNode;
  composer: ReactNode;
  title?: string;
  contextLabel?: string;
  contextDetails?: ReactNode;
  collapsedPreview?: ReactNode;
  collapseMode?: "composer" | "launcher";
  launcher?: ReactNode;
  fullscreenEnabled?: boolean;
  headerActions?: ReactNode;
  initialExpanded?: boolean;
  expanded?: boolean;
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
  reader, readerLabel = "Workspace content", conversationLabel, messages, composer, title = "Buddy", contextLabel = "Context",
  contextDetails, collapsedPreview, collapseMode = "composer", launcher, fullscreenEnabled = false, headerActions, initialExpanded = false, expanded: controlledExpanded,
  initialHeight = 340, minHeight = 280, maxHeight = 520,
  minimumReaderHeight = 160, onExpandedChange, className = "", style,
}: ConversationDockProps) {
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const messageRegion = useRef<HTMLDivElement>(null);
  const composerRegion = useRef<HTMLDivElement>(null);
  const scrollPosition = useRef(0);
  const launcherRegion = useRef<HTMLDivElement>(null);
  const conversationRegion = useRef<HTMLElement>(null);
  const fullscreenButton = useRef<HTMLButtonElement>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const drag = useRef<{ y: number; height: number; pointerId: number } | null>(null);
  const [localExpanded, setExpanded] = useState(initialExpanded);
  const expanded = controlledExpanded ?? localExpanded;
  const previousExpanded = useRef(expanded);
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
    if (!expanded) {
      setContextOpen(false);
      setFullscreen(false);
      if (collapseMode === "launcher" && previousExpanded.current) launcherRegion.current?.querySelector<HTMLElement>("button,a")?.focus({ preventScroll: true });
    } else if (collapseMode === "launcher" && !previousExpanded.current) {
      composerRegion.current?.querySelector<HTMLElement>("textarea,input")?.focus({ preventScroll: true });
    }
    previousExpanded.current = expanded;
  }, [expanded, collapseMode]);

  useLayoutEffect(() => {
    if (!hasContext) setContextOpen(false);
  }, [hasContext]);

  function changeExpanded(next: boolean) {
    if (next === expanded) return;
    if (!next) {
      scrollPosition.current = messageRegion.current?.scrollTop ?? 0;
      setContextOpen(false);
      const focused = document.activeElement;
      if (collapseMode === "composer" && focused && messageRegion.current?.contains(focused)) {
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

  function toggleFullscreen() {
    scrollPosition.current = messageRegion.current?.scrollTop ?? 0;
    setFullscreen(!fullscreen);
  }

  function fullscreenKeys(event: KeyboardEvent<HTMLElement>) {
    if (!fullscreen) return;
    if (event.key === "Escape") {
      event.preventDefault(); setFullscreen(false); fullscreenButton.current?.focus({ preventScroll: true });
    } else if (event.key === "Tab") {
      const controls = Array.from(conversationRegion.current?.querySelectorAll<HTMLElement>("button:not(:disabled),input:not(:disabled),textarea:not(:disabled),select:not(:disabled),a[href],summary,[tabindex='0']") ?? []).filter((node) => {
        if (node.closest("[hidden]")) return false;
        const details = node.closest("details");
        return (!details || details.open || node === details.querySelector("summary")) && node.getClientRects().length > 0;
      });
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first && last) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last && first) { event.preventDefault(); first.focus(); }
    }
  }

  useLayoutEffect(() => {
    if (messageRegion.current && expanded) messageRegion.current.scrollTop = scrollPosition.current;
  }, [fullscreen, expanded]);

  const variables = {
    ...style,
    "--conversation-dock-height": `${height}px`,
  } as CSSProperties;

  return (
    <div ref={root} className={`conversation-dock ${expanded ? "is-expanded" : ""} ${resizing ? "is-resizing" : ""} ${fullscreen ? "is-fullscreen" : ""} ${collapseMode === "launcher" ? "has-launcher-collapse" : ""} ${className}`.trim()} style={variables}>
      <div className="conversation-dock__reader" hidden={fullscreen} role="region" aria-label={readerLabel}>{reader}</div>
      <section ref={conversationRegion} id={`${id}-conversation`} className="conversation-dock__conversation" hidden={collapseMode === "launcher" && !expanded} role={fullscreen ? "dialog" : undefined} aria-modal={fullscreen || undefined} onKeyDown={fullscreenKeys} aria-label={conversationLabel ?? `${title} conversation`}>
        <button type="button" role="separator" aria-label={title === "Conversation" ? "Resize conversation" : `Resize ${title} conversation`} aria-orientation="horizontal"
          aria-controls={`${id}-messages`} aria-valuemin={floor} aria-valuemax={ceiling} aria-valuenow={height}
          hidden={fullscreen} className="conversation-dock__resize" onKeyDown={resizeFromKeyboard}
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
          {fullscreenEnabled && expanded && <button ref={fullscreenButton} type="button" aria-label={fullscreen ? "Restore conversation dock" : "Expand conversation fullscreen"} aria-pressed={fullscreen} onClick={toggleFullscreen}>{fullscreen ? "Restore" : "Fullscreen"}</button>}
          <button type="button" aria-label={collapseMode === "launcher" && expanded ? "Close conversation" : undefined} className="conversation-dock__toggle" aria-expanded={expanded}
            aria-controls={`${id}-messages`} onClick={() => changeExpanded(!expanded)}>{expanded ? collapseMode === "launcher" ? "Close" : "Collapse" : "Open chat"}</button>
        </header>
        <div id={`${id}-context`} className="conversation-dock__context" hidden={!contextOpen}>{contextDetails}</div>
        <div ref={messageRegion} id={`${id}-messages`} className="conversation-dock__messages" role="log"
          aria-label={`${title} messages`} hidden={!expanded}
          onScroll={() => { if (expanded) scrollPosition.current = messageRegion.current?.scrollTop ?? 0; }}>{messages}</div>
        {collapsedPreview !== undefined && <div className="conversation-dock__preview" hidden={expanded}>{collapsedPreview}</div>}
        <div ref={composerRegion} className="conversation-dock__composer">{composer}</div>
      </section>
      {collapseMode === "launcher" && <div ref={launcherRegion} className="conversation-dock__launcher" hidden={expanded} onClickCapture={() => changeExpanded(true)}>{launcher ?? <button type="button" aria-label="Open conversation" aria-expanded={expanded} aria-controls={`${id}-conversation`} onClick={() => changeExpanded(true)}>Conversation</button>}</div>}
    </div>
  );
}
