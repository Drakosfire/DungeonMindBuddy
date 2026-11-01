import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import "./LoadedWorldGraphExplorer.css";

const NativeGraphInspection = lazy(() => import("./NativeGraphInspection").then(module => ({ default: module.NativeGraphInspection })));

/** Both entry points inspect the same published authority, only while open. */
export function LoadedWorldGraphExplorer({ compact = false }: { compact?: boolean } = {}) {
  const world = useSelectedWorld();
  if (world.kind !== "managed") return null;
  return <WorldGraphBrowser key={world.worldId} worldName={world.name} worldId={world.worldId} compact={compact} />;
}

function WorldGraphBrowser({ worldName, worldId, compact }: {
  worldName: string; worldId: string; compact: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const launcher = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);
  const close = () => { setOpen(false); launcher.current?.focus(); };
  return <>
    <button ref={launcher} type="button" onClick={() => setOpen(true)}
      className={compact ? "app-world-graph-status__trigger" : undefined}
      data-testid={compact ? "app-chrome-world-graph-status" : undefined}
      aria-expanded={open} aria-haspopup="dialog"
      aria-label={compact ? `Explore ${worldName} World graph` : undefined}
      title={`Explore the published Graph for ${worldName}`}>
      {compact ? <><svg className="app-world-graph-status__glyph" viewBox="0 0 16 14" width="14" height="12" aria-hidden="true" focusable="false">
        <line className="app-world-graph-status__edge" x1="8" y1="3" x2="3" y2="11" />
        <line className="app-world-graph-status__edge" x1="8" y1="3" x2="13" y2="11" />
        <line className="app-world-graph-status__edge" x1="3" y1="11" x2="13" y2="11" />
        <circle className="app-world-graph-status__node" cx="8" cy="3" r="2" />
        <circle className="app-world-graph-status__node" cx="3" cy="11" r="2" />
        <circle className="app-world-graph-status__node" cx="13" cy="11" r="2" />
      </svg><span>Graph</span></> : "Explore graph"}
    </button>
    <dialog ref={dialog} className="loaded-graph-explorer" aria-label={`${worldName} World graph`}
      onCancel={close} onClose={close}>
      <header className="loaded-graph-explorer__header"><div>
        <span className="loaded-graph-explorer__eyebrow">World atlas</span>
        <h2>{worldName}</h2>
        <p className="loaded-graph-explorer__scope">Inspect published objects and their supporting sources. This view does not publish changes.</p>
      </div><button type="button" className="loaded-graph-explorer__close" onClick={close} aria-label="Close graph" title="Close graph">×</button></header>
      {open ? <Suspense fallback={<p role="status">Loading World graph…</p>}><NativeGraphInspection worldId={worldId} /></Suspense> : null}
    </dialog>
  </>;
}
