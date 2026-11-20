import { useEffect, useState, type CSSProperties } from "react";
import "./guestReleasePage.css";

type Node = { id: string; label: string; kind: string; name_citations: string[]; kind_citations: string[]; name_basis: string; kind_basis: string };
type Edge = { id: string; source: string; target: string; label: string; citations: string[]; temporal: string; basis: string };
type Source = { id: string; text: string; evidence_role: "support" | "context" };
type Snapshot = { release_id: string; manifest: { graph: { nodes: Node[]; edges: Edge[] }; sources: Source[]; assets: { id: string }[] } };

/** Public release copies only: this component never loads a managed World. */
export function GuestReleasePage({ publicId }: { publicId: string }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setSnapshot(null); setUnavailable(false); setSelectedNode(null); setSelectedSource(null);
    fetch(`/api/live/guest-releases/${encodeURIComponent(publicId)}`, { credentials: "omit", cache: "no-store", signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error("unavailable"); return response.json() as Promise<Snapshot>; })
      .then(data => { if (!controller.signal.aborted) setSnapshot(data); })
      .catch(() => { if (!controller.signal.aborted) setUnavailable(true); });
    return () => controller.abort();
  }, [publicId]);
  const nodes = snapshot?.manifest.graph.nodes ?? [];
  const edges = snapshot?.manifest.graph.edges ?? [];
  const sources = snapshot?.manifest.sources ?? [];
  const labels = new Map(nodes.map(node => [node.id, node.label]));
  const source = sources.find(item => item.id === selectedSource);
  const active = nodes.find(item => item.id === selectedNode);
  const connected = edges.filter(edge => edge.source === selectedNode || edge.target === selectedNode);
  const columns = Math.min(4, Math.max(1, Math.ceil(Math.sqrt(nodes.length))));
  const rows = Math.max(1, Math.ceil(nodes.length / columns));
  const positions = new Map(nodes.map((node, index) => [node.id, {
    x: (index % columns + .5) * 100 / columns, y: (Math.floor(index / columns) + .5) * 100 / rows,
  }]));
  const citationButton = (id: string, index: number) => <button type="button" key={`${id}-${index}`} onClick={() => setSelectedSource(id)}>Read {sources.find(item => item.id === id)?.evidence_role === "context" ? "context" : "source"} {sources.findIndex(item => item.id === id) + 1}</button>;
  return <main className="guest-world">
    <header className="guest-world__header"><a href="/">DungeonMind · Buddy</a><nav aria-label="Guest navigation"><a href="https://www.dungeonmind.net/">DungeonMind.net ↗</a><a href="/">Start your own World →</a></nav></header>
    {unavailable ? <section role="alert"><h1>This guest World is unavailable</h1><p>The owner may have withdrawn it, or the link may have changed.</p><a href="/">Return to Buddy</a></section>
      : !snapshot ? <p role="status">Opening this guest World…</p>
      : <><section className="guest-world__intro"><p className="guest-world__eyebrow">A SHARED WORLD · GUEST VIEW</p><h1>Follow the threads.</h1><p>Explore an owner-selected copy of a World. Choose a point to see its connections and the source behind each one.</p></section>
        <div className="guest-world__layout"><section className="guest-world__graph" aria-labelledby="guest-graph-heading"><div className="guest-world__section-head"><div><p className="guest-world__eyebrow">THE STORY MAP</p><h2 id="guest-graph-heading">A web of connections</h2></div><span>{nodes.length} {nodes.length === 1 ? "point" : "points"} · {edges.length} {edges.length === 1 ? "connection" : "connections"}</span></div>
          {nodes.length ? <div className="guest-world__points" style={{ height: `${Math.max(260, rows * 135)}px`, "--graph-columns": columns } as CSSProperties}>
            <svg className="guest-world__lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{edges.map(edge => { const start = positions.get(edge.source), end = positions.get(edge.target); return start && end ? <line key={edge.id} x1={start.x} y1={start.y} x2={end.x} y2={end.y} vectorEffect="non-scaling-stroke" /> : null; })}</svg>
            {nodes.map(node => { const position = positions.get(node.id)!; return <button key={node.id} type="button" style={{ left: `${position.x}%`, top: `${position.y}%` }} className={selectedNode === node.id ? "guest-world__point is-selected" : "guest-world__point"} aria-pressed={selectedNode === node.id} onClick={() => { setSelectedNode(node.id); setSelectedSource(null); }}><span aria-hidden="true">✦</span><strong>{node.label}</strong><small>{node.kind}</small></button>; })}
          </div> : <p>This copy has no Graph points yet.</p>}
        </section><aside className="guest-world__detail" aria-live="polite"><p className="guest-world__eyebrow">{source ? "SOURCE EXCERPT" : "FOLLOW A THREAD"}</p>
          {source ? <><h2>From the owner’s notes</h2><p>{source.evidence_role === "context" ? "Context for this claim; not direct support." : source.evidence_role === "support" ? "Supporting excerpt." : "Evidence role unavailable."}</p><p className="guest-world__excerpt">{source.text}</p><button type="button" onClick={() => setSelectedSource(null)}>← Back to connections</button></>
            : active ? <><h2>{active.label}</h2><p>{active.kind}</p><small>Name: {active.name_basis} · Classification: {active.kind_basis}</small><div className="guest-world__citations">{[...new Set([...active.name_citations, ...active.kind_citations])].map(citationButton)}</div><h3>Connections</h3>{connected.length ? <ul>{connected.map(edge => { const other = edge.source === active.id ? edge.target : edge.source; return <li key={edge.id}><p>{labels.get(edge.source)} <em>{edge.label}</em> {labels.get(edge.target)}</p><small>{edge.basis} · {edge.temporal === "unknown" ? "When this happened is not specified" : edge.temporal === "timeless" ? "Timeless" : edge.temporal}</small><div className="guest-world__citations"><button type="button" onClick={() => setSelectedNode(other)}>Explore {labels.get(other)}</button>{edge.citations.map(citationButton)}</div></li>; })}</ul> : <p>No connections were included for this point.</p>}</>
              : <><h2>Every story has a trail.</h2><p>Select a point to follow it through the owner’s shared notes.</p></>}
        </aside></div>
        {snapshot.manifest.assets.length > 0 && <section className="guest-world__gallery"><h2>From the World</h2>{snapshot.manifest.assets.map((asset, index) => <img key={asset.id} src={`/api/live/guest-releases/${encodeURIComponent(publicId)}/releases/${encodeURIComponent(snapshot.release_id)}/assets/${encodeURIComponent(asset.id)}`} alt={`Shared World image ${index + 1}`} />)}</section>}
        <section className="guest-world__next"><h2>Make room for your own story.</h2><p>This is a read-only snapshot. Guest editing and creation are not available here yet.</p><a href="/">Explore Buddy →</a></section></>}
    <footer className="guest-world__footer">A shared copy · Your private Worlds stay separate</footer>
  </main>;
}
