import { useEffect, useRef, useState } from "react";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { useWorldGraphLensProjectionDemand, useOptionalWorldGraphLensProjection, type WorldGraphLensProjectionState } from "./useWorldGraphLensProjection";
import type { WorldGraphProjection } from "../api/types";
import { graphObjectTypeBadgeLabel, graphObjectSecondaryRoleLabel } from "../graphObjectCard/graphObjectDisplay";
import "./LoadedWorldGraphExplorer.css";

function readableGraphLabel(value: string): string {
  const labels: Record<string, string> = {
    npc: "NPC", pc: "Player character", player_character: "Player character",
    session_recap: "Session recap", worldbuilding: "Worldbuilding", other: "Other sources",
  };
  return labels[value.trim().toLowerCase()] ?? graphObjectTypeBadgeLabel(value);
}

/** Opening acquires the shared verified projection; closing releases this consumer. */
export function LoadedWorldGraphExplorer() {
  const world = useSelectedWorld();
  const graph = useOptionalWorldGraphLensProjection();
  if (world.kind !== "managed" || !graph) return null;
  return <LoadedGraphBrowser key={world.worldId} worldName={world.name}
    projection={graph.projectionState === "ready" ? graph.projection : null}
    projectionState={graph.projectionState} projectionError={graph.projectionError} />;
}

export function LoadedGraphBrowser({ worldName, projection, projectionState, projectionError }: {
  worldName: string; projection: WorldGraphProjection | null;
  projectionState: WorldGraphLensProjectionState; projectionError: string | null;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const launcher = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const retry = useWorldGraphLensProjectionDemand(open);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [kindFilter, setKindFilter] = useState("all");
  const [visibleCount, setVisibleCount] = useState(100);
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);
  useEffect(() => {
    setSelectedId(null);
    setKindFilter("all");
    setVisibleCount(100);
  }, [projection?.snapshot.revisionId]);
  const close = () => { setOpen(false); launcher.current?.focus(); };
  const nodes = projection?.nodes ?? [];
  const kinds = [...new Set(nodes.map((node) => node.kind))].sort((left, right) => left.localeCompare(right));
  const normalizedQuery = query.toLocaleLowerCase().trim();
  const filtered = nodes.filter((node) => (kindFilter === "all" || node.kind === kindFilter)
    && [node.label, node.kind, ...node.aliases]
      .some((text) => text.toLocaleLowerCase().includes(normalizedQuery)));
  const selected = nodes.find((node) => node.nodeId === selectedId);
  const secondaryRole = selected ? graphObjectSecondaryRoleLabel(selected.kind, selected.role) : null;
  const byId = new Map(nodes.map((node) => [node.nodeId, node]));
  return <>
    <button ref={launcher} type="button" onClick={() => setOpen(true)}
      aria-haspopup="dialog" title={projection ? `Explore the loaded graph for ${worldName}` : `Load the World graph for ${worldName}`}>
      Explore graph
    </button>
    <dialog ref={dialog} className="loaded-graph-explorer" aria-label={`${worldName} loaded graph`}
      onCancel={close} onClose={close}>
      <header className="loaded-graph-explorer__header"><div>
        <span className="loaded-graph-explorer__eyebrow">World atlas</span>
        <h2>{worldName}</h2>
        <p className="loaded-graph-explorer__scope">Browse the loaded World projection. Buddy retrieves relevant evidence separately for each question.</p>
      </div><button type="button" className="loaded-graph-explorer__close" onClick={close} aria-label="Close graph" title="Close graph">×</button></header>
      {projection ? <div className="loaded-graph-explorer__overview" aria-label="Loaded graph summary">
        <span><strong>{nodes.length}</strong> subjects</span>
        <span><strong>{projection.summary.relationshipCount}</strong> connections</span>
        <span><strong>{projection.summary.sourceArtifactCount}</strong> source artifacts</span>
        <span className={projection.summary.projectionTruncated ? "loaded-graph-explorer__coverage loaded-graph-explorer__coverage--partial" : "loaded-graph-explorer__coverage"}>
          {projection.summary.projectionTruncated ? "Partial projection" : "Loaded projection"}
        </span>
      </div> : null}
      {projection?.summary.projectionTruncated ? <p className="loaded-graph-explorer__notice" role="status">This loaded projection is truncated. More graph content may exist; the counts and search below describe only what is loaded here.</p> : null}
      {!projection ? <div><p role="status">{projectionState === "error" ? projectionError || "The World graph could not be loaded."
        : projectionState === "unavailable" ? "The World graph is unavailable."
        : "Loading the World graph…"} The previous projection is no longer shown.</p>
        {(projectionState === "error" || projectionState === "unavailable") && retry ? <button type="button" onClick={retry}>Retry graph load</button> : null}</div> :
        <div className="loaded-graph-explorer__layout">
          <nav aria-label="Loaded graph nodes">
            <label className="loaded-graph-explorer__search">Find a node<input type="search" placeholder="Name, alias, or type" value={query} onChange={(event) => { setQuery(event.target.value); setVisibleCount(100); }} /></label>
            <label className="loaded-graph-explorer__filter">Show
              <select value={kindFilter} onChange={(event) => { setKindFilter(event.target.value); setVisibleCount(100); }}>
                <option value="all">All subjects</option>
                {kinds.map((kind) => <option key={kind} value={kind}>{readableGraphLabel(kind)}</option>)}
              </select>
            </label>
            <p className="loaded-graph-explorer__result-count">{filtered.length} {filtered.length === 1 ? "match" : "matches"} in the loaded projection</p>
            <ul>{filtered.slice(0, visibleCount).map((node) => <li key={node.nodeId}>
              <button type="button" aria-label={`${node.label} ${readableGraphLabel(node.kind)}`} aria-current={selectedId === node.nodeId ? "true" : undefined} onClick={() => setSelectedId(node.nodeId)}>
                <span>{node.label}</span><small>{readableGraphLabel(node.kind)} · {node.adjacency.length} connections</small>
              </button></li>)}</ul>
            {!filtered.length ? <p>No matching nodes in the loaded projection.</p> : null}
            {filtered.length > visibleCount ? <button type="button" onClick={() => setVisibleCount((count) => count + 100)}>Show more nodes</button> : null}
          </nav>
          <article aria-label="Selected graph node">
            {selected ? <><span className="loaded-graph-explorer__eyebrow">{readableGraphLabel(selected.kind)}{secondaryRole ? ` · ${readableGraphLabel(secondaryRole)}` : ""}</span><h3>{selected.label}</h3>
              {selected.aliases.length ? <p>Also known as {selected.aliases.join(", ")}</p> : null}
              <p className="loaded-graph-explorer__summary">{selected.summary || "No summary is included in the loaded projection."}</p>
              <h4>Connections <span>{selected.adjacency.length}</span></h4>
              {selected.adjacency.length ? <ul className="loaded-graph-explorer__connections">{selected.adjacency.map((edge) => <li key={edge.edgeId}>
                <span>{edge.edgeLabel || edge.predicate} · </span>
                {byId.has(edge.nodeId) ? <button type="button" onClick={() => setSelectedId(edge.nodeId)}>{byId.get(edge.nodeId)!.label}</button>
                  : <span>{edge.label} (outside the loaded projection)</span>}
                {edge.relatedSummary ? <details><summary>Read connection context</summary><p>{edge.relatedSummary}</p></details> : null}
              </li>)}</ul> : <p>No connections are included for this node.</p>}
              {selected.sourceDomains.length ? <><h4>Sources</h4><ul>{selected.sourceDomains.map((source) => <li key={source}>{readableGraphLabel(source)}</li>)}</ul></> : null}
              <details><summary>Projection details</summary><p>Node: {selected.nodeId}</p><p>Revision: {projection.snapshot.revisionId}</p>
                <p>{selected.evidenceRefIds.length} evidence references · {selected.sourceArtifactIds.length} source artifacts</p></details>
            </> : <p>Select a node to inspect its summary and connections.</p>}
          </article>
        </div>}
    </dialog>
  </>;
}
