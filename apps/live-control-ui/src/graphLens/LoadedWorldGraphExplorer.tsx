import { listWorldCreatures, listWorldMechanicsAssociations } from "../api/liveApi";
import type { WorldMechanicsAssociation } from "../api/worldMechanicsTypes";
import { buildSavedStatblockHref } from "../statblocks/savedStatblockLocation";
import { interceptPrimaryNavigationClick } from "../chrome/appNavigation";
import { useEffect, useRef, useState } from "react";
import { deferredComponent } from "../ui/deferredComponent";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import "./LoadedWorldGraphExplorer.css";

const NativeGraphInspection = deferredComponent(
  () => import("./NativeGraphInspection").then(module => ({ default: module.NativeGraphInspection })),
  "World graph",
);

const NativeSourceInspection = deferredComponent(
  () => import("./NativeSourceInspection").then(module => ({default: module.NativeSourceInspection})),
  "World sources",
);

type WorldBrowserEntry = "graph" | "recaps";

/** All entry points inspect the same published authority, only while open. */
export function LoadedWorldGraphExplorer({ compact = false, entry = "graph" }: { compact?: boolean; entry?: WorldBrowserEntry } = {}) {
  const world = useSelectedWorld();
  if (world.kind !== "managed") return null;
  return <WorldGraphBrowser key={world.worldId} worldName={world.name} worldId={world.worldId} compact={compact} entry={entry} />;
}

function WorldGraphBrowser({ worldName, worldId, compact, entry }: {
  worldName: string; worldId: string; compact: boolean; entry: WorldBrowserEntry;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const launcher = useRef<HTMLButtonElement>(null);
  const recaps = entry === "recaps";
  const initialMaterial = recaps ? "sources" : "objects";
  const [open, setOpen] = useState(false);
  const [material, setMaterial] = useState<"objects"|"sources"|"threats">(initialMaterial);
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);
  const close = () => { setOpen(false); launcher.current?.focus(); };
  return <>
    <button ref={launcher} type="button" onClick={() => { if (recaps) setMaterial("sources"); setOpen(true); }}
      className={recaps ? "surface-context-action build-browse-recaps" : compact ? "app-world-graph-status__trigger" : undefined}
      data-testid={!recaps && compact ? "app-chrome-world-graph-status" : undefined}
      aria-expanded={open} aria-haspopup="dialog"
      aria-label={!recaps && compact ? `Explore ${worldName} World graph` : undefined}
      title={recaps ? `Browse recaps in ${worldName}` : `Explore the published Graph for ${worldName}`}>
      {recaps ? "Browse recaps" : compact ? <><svg className="app-world-graph-status__glyph" viewBox="0 0 16 14" width="14" height="12" aria-hidden="true" focusable="false">
        <line className="app-world-graph-status__edge" x1="8" y1="3" x2="3" y2="11" />
        <line className="app-world-graph-status__edge" x1="8" y1="3" x2="13" y2="11" />
        <line className="app-world-graph-status__edge" x1="3" y1="11" x2="13" y2="11" />
        <circle className="app-world-graph-status__node" cx="8" cy="3" r="2" />
        <circle className="app-world-graph-status__node" cx="3" cy="11" r="2" />
        <circle className="app-world-graph-status__node" cx="13" cy="11" r="2" />
      </svg><span>Graph</span></> : "Explore graph"}
    </button>
    <dialog ref={dialog} data-native-escape-owner className="loaded-graph-explorer" aria-label={`${worldName} World ${recaps ? "sources" : "graph"}`}
      onCancel={close} onClose={close}>
      <header className="loaded-graph-explorer__header"><div>
        <span className="loaded-graph-explorer__eyebrow">World atlas</span>
        <h2>{worldName}</h2>
        <p className="loaded-graph-explorer__scope">Browse sources and reviewed World Graph objects.</p>
      </div><button type="button" className="loaded-graph-explorer__close" onClick={close} aria-label={recaps ? "Close sources" : "Close graph"} title={recaps ? "Close sources" : "Close graph"}>×</button></header>
      {open ? <><div role="group" aria-label="World material">
        <button type="button" aria-pressed={material==='objects'} onClick={()=>setMaterial('objects')}>Objects</button>
        <button type="button" aria-pressed={material==='sources'} onClick={()=>setMaterial('sources')}>Sources</button>
        {recaps && <button type="button" aria-pressed={material==="threats"} onClick={()=>setMaterial("threats")}>Threats</button>}
      </div>{material==="threats"?<BuildThreats worldId={worldId} close={close}/>:material==='objects'?<NativeGraphInspection worldId={worldId}/>:<NativeSourceInspection worldId={worldId} initialKind={recaps ? "recap" : ""}/>}</> : null}
    </dialog>
  </>;
}

function BuildThreats({ worldId, close }: { worldId: string; close: () => void }) {
  const [records, setRecords] = useState<WorldMechanicsAssociation[]>();
  const [failed, setFailed] = useState(false);
  const [query, setQuery] = useState("");
  useEffect(() => {
    let active = true;
    void Promise.all([listWorldMechanicsAssociations(worldId), listWorldCreatures(worldId)]).then(([associations, catalog]) => {
      const creatureIds = new Set(catalog.targets.filter(target =>
        target.kind === "creature" && target.campaign_scope === null,
      ).map(target => target.node_id));

      if (active) setRecords(associations.filter(({ request: { target } }) =>
        target.managed_world_id === worldId && target.native_world_id === catalog.native_world_id
        && target.binding_version === catalog.binding_version && target.kind === "creature"
        && target.campaign_scope === null && creatureIds.has(target.node_id),
      ));
    }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [worldId]);
  if (failed) return <p role="alert">Could not load statblocks. Reopen Threats to retry.</p>;
  if (!records) return <p role="status">Loading statblocks…</p>;
  const matching = records.filter(({ request }) =>
    request.target.label.toLowerCase().includes(query.trim().toLowerCase()),
  );
  return <section aria-label="Published threat statblocks">
    <label>Find a threat <input type="search" value={query} onChange={event => setQuery(event.target.value)} /></label>
    {matching.length ? <ul>{matching.map(({ association_id, request, proof }) =>
      <li key={association_id}>
        <a href={buildSavedStatblockHref({ worldId, draftId: request.draft_id, revisionId: proof.locator.revision_id })}
          onClick={event => {
            interceptPrimaryNavigationClick(event);
            if (event.defaultPrevented) close();
          }}>{request.target.label}</a>
      </li>,
    )}</ul> : <p>No matching statblocks.</p>}
  </section>;
}
