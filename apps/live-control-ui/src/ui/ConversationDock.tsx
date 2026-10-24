import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent, type ReactNode, type RefObject } from "react";
import "./ConversationDock.css";
import { useConversationPlacement } from "./conversationPlacement";

export interface ConversationDockProps {
  reader: ReactNode;
  readerLabel?: string;
  conversationLabel?: string;
  messages: ReactNode;
  composer: ReactNode;
  title?: string;
  showTitle?: boolean;
  contextLabel?: string;
  contextDetails?: ReactNode;
  collapsedPreview?: ReactNode;
  collapseMode?: "composer" | "launcher";
  launcher?: ReactNode;
  fullscreenEnabled?: boolean;
  headerActions?: ReactNode;
  menuActions?: ReactNode;
  menuRef?: RefObject<HTMLDetailsElement | null>;
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
 * A height-owning workspace's reader and floating conversation column.
 * Context mounts on first opening, then retains its state through collapse.
 * Other slots stay mounted throughout. Callers own messages,
 * compact composer behavior, verified context and all external actions.
 * Paint through --conversation-dock-* variables; no application providers.
 */
export function ConversationDock({
  reader, readerLabel = "Workspace content", conversationLabel, messages, composer, title = "Buddy", showTitle = true, contextLabel = "Context",
  contextDetails, collapsedPreview, collapseMode = "composer", launcher, fullscreenEnabled = false, headerActions, menuActions, menuRef, initialExpanded = false, expanded: controlledExpanded,
  initialHeight, minHeight = 280, maxHeight = 1440,
  minimumReaderHeight = 160, onExpandedChange, className = "", style,
}: ConversationDockProps) {
  const id = useId();
  const [placement, setPlacement] = useConversationPlacement();
  const ownMenu = useRef<HTMLDetailsElement>(null);
  const menu = menuRef ?? ownMenu;
  const [menuOpen, setMenuOpen] = useState(false);
  const [diagnosticsVisible, setDiagnosticsVisible] = useState(false);
  useEffect(() => {
    const outside = (event: globalThis.PointerEvent) => {
      if (menu.current?.open && event.target instanceof Node && !menu.current.contains(event.target)) { menu.current.open = false; setMenuOpen(false); }
    };
    const escape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape" && menu.current?.open) {
        event.preventDefault(); event.stopPropagation(); menu.current.open = false; setMenuOpen(false);
        menu.current.querySelector<HTMLElement>("summary")?.focus({preventScroll:true});
      }
    };
    document.addEventListener("pointerdown", outside, true);
    document.addEventListener("keydown", escape, true);
    return () => { document.removeEventListener("pointerdown", outside, true); document.removeEventListener("keydown", escape, true); };
  }, [menu]);
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
  const [contextVisited, setContextVisited] = useState(false);
  const [requestedHeight, setRequestedHeight] = useState<number | null>(initialHeight ?? null);
  const [containerHeight, setContainerHeight] = useState<number | null>(null);
  const [containerWidth, setContainerWidth] = useState<number | null>(null);
  const hasReader = reader !== null && reader !== undefined && reader !== false;
  const [resizing, setResizing] = useState(false);
  const hasContext = contextDetails !== undefined && contextDetails !== null && contextDetails !== false;

  const reserve = containerHeight === null ? minimumReaderHeight : Math.min(minimumReaderHeight, containerHeight * 0.3);
  const ceiling = Math.max(160, Math.min(maxHeight, containerHeight === null ? maxHeight : containerHeight - reserve - (hasReader ? 32 : 0)));
  const floor = Math.min(Math.max(160, minHeight), ceiling);
  const narrowWorkspace = hasReader && containerWidth !== null && containerWidth < 832;
  const effectivePlacement = narrowWorkspace && placement === "side" ? "bottom" : placement;
  const preferredHeight = narrowWorkspace || effectivePlacement === "bottom"
    ? Math.round((containerHeight ?? 680) * 0.62) : 640;
  const height = Math.max(floor, Math.min(ceiling, requestedHeight ?? preferredHeight));

  useLayoutEffect(() => {
    const element = root.current;
    if (!element) return;
    const measure = () => {
      const next = element.getBoundingClientRect();
      if (next.height > 0) setContainerHeight(next.height);
      if (next.width > 0) setContainerWidth(next.width);
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
      if (menu.current) menu.current.open = false;
      setMenuOpen(false);
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
    <div ref={root} data-placement={effectivePlacement} data-preferred-placement={placement} data-diagnostics-visible={diagnosticsVisible} className={`conversation-dock ${hasReader ? "has-reader" : ""} ${narrowWorkspace ? "is-narrow" : ""} ${expanded ? "is-expanded" : ""} ${resizing ? "is-resizing" : ""} ${fullscreen ? "is-fullscreen" : ""} ${collapseMode === "launcher" ? "has-launcher-collapse" : ""} ${className}`.trim()} style={variables}>
      <div className="conversation-dock__reader" hidden={fullscreen} role="region" aria-label={readerLabel}>{reader}</div>
      <section ref={conversationRegion} id={`${id}-conversation`} className="conversation-dock__conversation" hidden={collapseMode === "launcher" && !expanded} role={fullscreen ? "dialog" : undefined} aria-modal={fullscreen || undefined} onKeyDown={fullscreenKeys} onSubmitCapture={() => setContextOpen(false)} aria-label={conversationLabel ?? `${title} conversation`}>
        <button type="button" role="separator" aria-label={title === "Conversation" ? "Resize conversation" : `Resize ${title} conversation`} aria-orientation="horizontal"
          aria-controls={`${id}-messages`} aria-valuemin={floor} aria-valuemax={ceiling} aria-valuenow={height}
          hidden={fullscreen} className="conversation-dock__resize" onKeyDown={resizeFromKeyboard}
          onPointerDown={startResize} onPointerMove={moveResize} onPointerUp={finishResize} onPointerCancel={finishResize} onLostPointerCapture={finishResize}>
          <span aria-hidden="true" />
        </button>
        <header className="conversation-dock__header">
          {showTitle && <strong>{title}</strong>}
          <div className="conversation-dock__actions">{headerActions}
            <details ref={menu} className="conversation-dock__menu" aria-label="Conversation options" onToggle={event => setMenuOpen(event.currentTarget.open)}>
              <summary aria-label="Conversation options" title="Conversation options" onClick={event => { event.preventDefault(); if (menu.current) { menu.current.open = !menu.current.open; setMenuOpen(menu.current.open); } }}><svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg></summary>
              <div hidden={!menuOpen}>
                <div role="group" aria-label="Conversation placement" className="conversation-dock__placement">
                  {(["side", "bottom", "float"] as const).map(value => <button key={value} type="button"
                    aria-pressed={placement === value} onClick={() => setPlacement(value)}>
                    {value === "side" ? "Side" : value === "bottom" ? "Bottom" : "Float"}</button>)}
                </div>
                {narrowWorkspace && placement === "side" && <p>Side placement uses Bottom at this width.</p>}
                {hasContext && <button type="button" aria-expanded={contextOpen} aria-controls={`${id}-context`}
                  onClick={() => { changeExpanded(true); setContextVisited(true); setContextOpen(!contextOpen); }}>
                  {contextOpen ? "Hide" : "Show"} {contextLabel}
                </button>}
                <label className="conversation-dock__diagnostics"><input type="checkbox" checked={diagnosticsVisible} onChange={event => setDiagnosticsVisible(event.target.checked)}/>Technical details</label>
                {menuActions}
              </div>
            </details>
          </div>
          {fullscreenEnabled && expanded && <button ref={fullscreenButton} className="conversation-dock__icon-button" type="button" title={fullscreen ? "Restore dock" : "Fullscreen"} aria-label={fullscreen ? "Restore conversation dock" : "Expand conversation fullscreen"} aria-pressed={fullscreen} onClick={toggleFullscreen}>
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d={fullscreen ? "M3 8h5V3M21 8h-5V3M8 21v-5H3M16 21v-5h5" : "M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5"} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>}
          <button type="button" aria-label={expanded ? collapseMode === "launcher" ? "Close conversation" : "Collapse" : "Open chat"} title={expanded ? collapseMode === "launcher" ? "Close conversation" : "Collapse" : "Open chat"} className={`conversation-dock__toggle${expanded ? " conversation-dock__icon-button" : ""}`} aria-expanded={expanded}
            aria-controls={`${id}-messages`} onClick={() => changeExpanded(!expanded)}>
            {expanded ? <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d={collapseMode === "launcher" ? "M6 6l12 12M18 6 6 18" : "m6 9 6 6 6-6"} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg> : "Open chat"}
          </button>
        </header>
        <div id={`${id}-context`} className="conversation-dock__context" hidden={!contextOpen}>{contextVisited ? contextDetails : null}</div>
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
