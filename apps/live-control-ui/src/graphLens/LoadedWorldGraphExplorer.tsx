import { useEffect, useRef, useState } from "react";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { useOptionalWorldGraphLensProjection } from "./useWorldGraphLensProjection";
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

/** Inspect the shared, verified loaded projection; opening this view never fetches or mutates Graph. */
export function LoadedWorldGraphExplorer() {
  const world = useSelectedWorld();
  const graph = useOptionalWorldGraphLensProjection();
  if (world.kind !== "managed" || !graph) return null;
  return <LoadedGraphBrowser key={world.worldId} worldName={world.name}
    projection={graph.projectionState === "ready" ? graph.projection : null} />;
}

export function LoadedGraphBrowser({ worldName, projection }: {
  worldName: string; projection: WorldGraphProjection | null;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const launcher = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(100);
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);
  useEffect(() => {
    setSelectedId(null);
    setVisibleCount(100);
  }, [projection?.snapshot.revisionId]);
  const close = () => { setOpen(false); launcher.current?.focus(); };
  const nodes = projection?.nodes ?? [];
  const filtered = nodes.filter((node) => [node.label, node.kind, ...node.aliases]
    .some((text) => text.toLocaleLowerCase().includes(query.toLocaleLowerCase().trim())));
  const selected = nodes.find((node) => node.nodeId === selectedId);
  const secondaryRole = selected ? graphObjectSecondaryRoleLabel(selected.kind, selected.role) : null;
  const byId = new Map(nodes.map((node) => [node.nodeId, node]));
  return <>
    <button ref={launcher} type="button" disabled={!projection} onClick={() => setOpen(true)}
      aria-haspopup="dialog" title={projection ? `Explore the loaded graph for ${worldName}` : "The World graph is not loaded yet"}>
      Explore loaded graph
    </button>
    <dialog ref={dialog} className="loaded-graph-explorer" aria-label={`${worldName} loaded graph`}
      onCancel={close} onClose={close}>
      <header><div><h2>{worldName}</h2><p>{nodes.length} loaded nodes · {projection?.summary.relationshipCount ?? 0} connections</p></div>
        <button type="button" onClick={close}>Close graph</button></header>
      <p className="loaded-graph-explorer__scope">This is the loaded World projection. Buddy selects relevant evidence for each question.</p>
      {projection?.summary.projectionTruncated ? <p role="status">This projection is truncated; additional graph content is not shown.</p> : null}
      {!projection ? <p role="status">The graph is loading or unavailable. The previous projection is no longer shown.</p> :
        <div className="loaded-graph-explorer__layout">
          <nav aria-label="Loaded graph nodes">
            <label>Find a node<input type="search" value={query} onChange={(event) => { setQuery(event.target.value); setVisibleCount(100); }} /></label>
            <ul>{filtered.slice(0, visibleCount).map((node) => <li key={node.nodeId}>
              <button type="button" aria-current={selectedId === node.nodeId ? "true" : undefined} onClick={() => setSelectedId(node.nodeId)}>
                {node.label}<small>{readableGraphLabel(node.kind)}</small>
              </button></li>)}</ul>
            {!filtered.length ? <p>No matching nodes in the loaded projection.</p> : null}
            {filtered.length > visibleCount ? <button type="button" onClick={() => setVisibleCount((count) => count + 100)}>Show more nodes</button> : null}
          </nav>
          <article aria-label="Selected graph node">
            {selected ? <><h3>{selected.label}</h3><p>{readableGraphLabel(selected.kind)}{secondaryRole ? ` · ${readableGraphLabel(secondaryRole)}` : ""}</p>
              {selected.aliases.length ? <p>Also known as {selected.aliases.join(", ")}</p> : null}
              <p>{selected.summary || "No summary is included in the loaded projection."}</p>
              <h4>Connections</h4>
              {selected.adjacency.length ? <ul>{selected.adjacency.map((edge) => <li key={edge.edgeId}>
                <span>{edge.edgeLabel || edge.predicate} · </span>
                {byId.has(edge.nodeId) ? <button type="button" onClick={() => setSelectedId(edge.nodeId)}>{byId.get(edge.nodeId)!.label}</button>
                  : <span>{edge.label} (outside the loaded projection)</span>}
                {edge.relatedSummary ? <p>{edge.relatedSummary}</p> : null}
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
