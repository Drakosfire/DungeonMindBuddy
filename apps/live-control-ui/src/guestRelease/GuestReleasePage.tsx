import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { dungeonMindLoginHref } from "../auth/HostedAuthGate";
import { isSavedExample } from "./savedExample";
import { isSavedChoice } from "./savedChoice";
import "./guestReleasePage.css";

type Node = { id: string; label: string; kind: string; name_citations: string[]; kind_citations: string[]; name_basis: string; kind_basis: string; temporary?: boolean };
type Edge = { id: string; source: string; target: string; label: string; citations: string[]; temporal: string; basis: string; temporary?: boolean };
type Source = { id: string; text: string; evidence_role: "support" | "context" };
type Snapshot = { release_id: string; manifest: { graph: { nodes: Node[]; edges: Edge[] }; sources: Source[]; assets: { id: string }[]; saved_example?: unknown; saved_choice?: unknown } };

function fragment(release: string, node?: string | null, source?: string | null): string {
  const parts = ["copy", release];
  if (node) parts.push("point", node);
  if (source) parts.push("source", source);
  return `#${parts.map(encodeURIComponent).join("/")}`;
}

function selectionFromFragment(hash: string, snapshot: Snapshot): { node: string | null; source: string | null } {
  const empty = { node: null, source: null };
  try {
    const parts = hash.slice(1).split("/").map(decodeURIComponent);
    if (parts[0] !== "copy" || parts[1] !== snapshot.release_id) return empty;
    let node: string | null = null, source: string | null = null;
    for (let index = 2; index < parts.length; index += 2) {
      if (!parts[index + 1]) return empty;
      if (parts[index] === "point" && node === null) node = parts[index + 1];
      else if (parts[index] === "source" && source === null) source = parts[index + 1];
      else return empty;
    }
    if (node && !snapshot.manifest.graph.nodes.some(item => item.id === node)) return empty;
    if (source && !snapshot.manifest.sources.some(item => item.id === source)) return empty;
    return { node, source };
  } catch {
    return empty;
  }
}

/** Public release copies only: this component never loads a managed World. */
export function GuestReleasePage({ publicId, home = false }: { publicId: string; home?: boolean }) {
  const [result, setResult] = useState<{ publicId: string; snapshot: Snapshot | null; unavailable: boolean } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setResult({ publicId, snapshot: null, unavailable: false });
    fetch(`/api/live/guest-releases/${encodeURIComponent(publicId)}`, { credentials: "omit", cache: "no-store", signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error("unavailable"); return response.json() as Promise<Snapshot>; })
      .then(data => { if (!controller.signal.aborted) setResult({ publicId, snapshot: data, unavailable: false }); })
      .catch(() => { if (!controller.signal.aborted) setResult({ publicId, snapshot: null, unavailable: true }); });
    return () => controller.abort();
  }, [publicId]);
  const current = result?.publicId === publicId ? result : null;
  const snapshot = current?.snapshot ?? null;
  return <GuestReleaseView key={JSON.stringify([publicId, snapshot ? "copy" : "pending", snapshot?.release_id])}
    publicId={publicId} home={home} snapshot={snapshot} unavailable={current?.unavailable ?? false} />;
}

function GuestReleaseView({ publicId, home, snapshot, unavailable }: { publicId: string; home: boolean; snapshot: Snapshot | null; unavailable: boolean }) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [additions, setAdditions] = useState<{ nodes: Node[]; edges: Edge[] }>({ nodes: [], edges: [] });
  const [name, setName] = useState("");
  const [relation, setRelation] = useState("connected to");
  const [target, setTarget] = useState("");
  const [formError, setFormError] = useState("");
  const [selectedChoice, setSelectedChoice] = useState<0 | 1 | null>(null);
  const sequence = useRef(0);
  const additionCount = useRef(0);
  const detailRef = useRef<HTMLElement>(null);
  const graphRef = useRef<HTMLElement>(null);
  const exampleRef = useRef<HTMLElement>(null);
  const showSection = (section: HTMLElement | null) => {
    section?.focus({ preventScroll: true });
    section?.scrollIntoView?.({ behavior: "auto", block: "start" });
  };
  useEffect(() => {
    if (!snapshot) return;
    const sync = () => {
      const selection = selectionFromFragment(window.location.hash, snapshot);
      setSelectedNode(selection.node); setSelectedSource(selection.source);
    };
    sync();
    window.addEventListener("popstate", sync);
    window.addEventListener("hashchange", sync);
    return () => { window.removeEventListener("popstate", sync); window.removeEventListener("hashchange", sync); };
  }, [snapshot]);
  const navigate = (node: string | null, source: string | null) => {
    if (!snapshot) return;
    const releasedNode = snapshot.manifest.graph.nodes.some(item => item.id === node) ? node : null;
    window.history.pushState(null, "", fragment(snapshot.release_id, releasedNode, source));
    setSelectedNode(node); setSelectedSource(source);
  };
  const sharedNodes = snapshot?.manifest.graph.nodes ?? [];
  const sharedEdges = snapshot?.manifest.graph.edges ?? [];
  const nodes = [...sharedNodes, ...additions.nodes];
  const edges = [...sharedEdges, ...additions.edges];
  const sources = snapshot?.manifest.sources ?? [];
  const exampleValue = snapshot?.manifest.saved_example;
  const example = snapshot && isSavedExample(exampleValue, sources, snapshot.manifest.assets) ? exampleValue : null;
  const choiceValue = snapshot?.manifest.saved_choice;
  const choice = example && isSavedChoice(choiceValue) ? choiceValue : null;
  const labels = new Map(nodes.map(node => [node.id, node.label]));
  const source = sources.find(item => item.id === selectedSource);
  const active = nodes.find(item => item.id === selectedNode);
  const connected = edges.filter(edge => edge.source === selectedNode || edge.target === selectedNode);
  const columns = Math.min(4, Math.max(1, Math.ceil(Math.sqrt(nodes.length))));
  const rows = Math.max(1, Math.ceil(nodes.length / columns));
  const positions = new Map(nodes.map((node, index) => [node.id, {
    x: (index % columns + .5) * 100 / columns, y: (Math.floor(index / columns) + .5) * 100 / rows,
  }]));
  const addPoint = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const label = name.trim(), link = relation.trim();
    const invalid = /[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/;
    if (!label || !link || label.length > 80 || link.length > 60 || invalid.test(label) || invalid.test(link)
      || !sharedNodes.some(node => node.id === target) || additionCount.current >= 10) {
      setFormError("Enter a point and connection, and choose a shared point. Avoid control characters.");
      return;
    }
    const used = new Set([...nodes.map(node => node.id), ...edges.map(edge => edge.id)]);
    const localId = () => { let id: string; do { id = `guest-local-${++sequence.current}`; } while (used.has(id)); used.add(id); return id; };
    const id = localId(), edgeId = localId();
    const node: Node = { id, label, kind: "Your addition", name_citations: [], kind_citations: [], name_basis: "", kind_basis: "", temporary: true };
    const edge: Edge = { id: edgeId, source: id, target, label: link, citations: [], temporal: "", basis: "", temporary: true };
    additionCount.current++;
    setAdditions(previous => ({ nodes: [...previous.nodes, node], edges: [...previous.edges, edge] }));
    setName(""); setRelation("connected to"); setTarget(""); setFormError("");
    navigate(id, null);
  };
  const reset = () => {
    additionCount.current = 0;
    setAdditions({ nodes: [], edges: [] }); setName(""); setRelation("connected to"); setTarget(""); setFormError("");
    setSelectedChoice(null);
    setSelectedNode(null); setSelectedSource(null);
    if (snapshot) window.history.replaceState(null, "", fragment(snapshot.release_id));
  };
  const citationButton = (id: string, index: number) => <button type="button" key={`${id}-${index}`} onClick={() => { navigate(selectedNode, id); detailRef.current?.focus({ preventScroll: true }); detailRef.current?.scrollIntoView?.({ behavior: "auto", block: "nearest" }); }}>Read {sources.find(item => item.id === id)?.evidence_role === "context" ? "context" : "source"} {sources.findIndex(item => item.id === id) + 1}</button>;
  return <main className="guest-world">
    <header className="guest-world__header"><a href="/">DungeonMind · Buddy</a><nav aria-label="Guest navigation">{snapshot && <button type="button" onClick={() => showSection(graphRef.current)}>Explore graph</button>}{example && <button type="button" onClick={() => showSection(exampleRef.current)}>Saved scene</button>}<a href="https://www.dungeonmind.net/">DungeonMind.net ↗</a><a href={dungeonMindLoginHref("/")}>Sign in to create your World →</a></nav></header>
    {unavailable ? <section role="alert"><h1>This guest World is unavailable</h1><p>The owner may have withdrawn it, or the link may have changed.</p><a href={home ? dungeonMindLoginHref("/") : "/"}>{home ? "Sign in to Buddy" : "Return to Buddy"}</a></section>
      : !snapshot ? <p role="status">Opening this guest World…</p>
      : <><section className="guest-world__intro"><p className="guest-world__eyebrow">A SHARED WORLD · GUEST VIEW</p><h1>Follow the threads.</h1><p>Explore an owner-selected copy of a World. Choose a point to see its connections and the source behind each one.</p></section>
        <div className="guest-world__layout"><section ref={graphRef} tabIndex={-1} className="guest-world__graph" aria-labelledby="guest-graph-heading"><div className="guest-world__section-head"><div><p className="guest-world__eyebrow">THE STORY MAP</p><h2 id="guest-graph-heading">A web of connections</h2></div><span>{sharedNodes.length} shared {sharedNodes.length === 1 ? "point" : "points"} · {additions.nodes.length} yours</span></div>
          {nodes.length ? <div className="guest-world__points" style={{ height: `${Math.max(260, rows * 135)}px`, "--graph-columns": columns } as CSSProperties}>
            <svg className="guest-world__lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{edges.map(edge => { const start = positions.get(edge.source), end = positions.get(edge.target); return start && end ? <line key={edge.id} x1={start.x} y1={start.y} x2={end.x} y2={end.y} vectorEffect="non-scaling-stroke" /> : null; })}</svg>
            {nodes.map(node => { const position = positions.get(node.id)!; return <button key={node.id} type="button" style={{ left: `${position.x}%`, top: `${position.y}%` }} className={`guest-world__point${selectedNode === node.id ? " is-selected" : ""}${node.temporary ? " is-temporary" : ""}`} aria-pressed={selectedNode === node.id} onClick={() => navigate(node.id, null)}><span aria-hidden="true">✦</span><strong>{node.label}</strong><small>{node.kind}</small></button>; })}
          </div> : <p>This copy has no Graph points yet.</p>}
          <section className="guest-world__sandbox" aria-labelledby="guest-sandbox-heading">
            <h3 id="guest-sandbox-heading">Add your own thread</h3>
            <p>Your additions are temporary. They stay in this view and disappear when you leave, reload, or reset. They never change the shared World.</p>
            {sharedNodes.length ? <form onSubmit={addPoint}>
              <label>Point name <input value={name} onChange={event => setName(event.target.value)} maxLength={80} required /></label>
              <label>Connection <input value={relation} onChange={event => setRelation(event.target.value)} maxLength={60} required /></label>
              <label>Connect to a shared point <select value={target} onChange={event => setTarget(event.target.value)} required><option value="">Choose a shared point</option>{sharedNodes.map(node => <option key={node.id} value={node.id}>{node.label} · {node.kind}</option>)}</select></label>
              {formError && <p role="alert">{formError}</p>}
              <button type="submit" disabled={additions.nodes.length >= 10}>Add temporary point</button>
              {additions.nodes.length >= 10 && <p>You've reached the ten-point limit. Reset to start again.</p>}
            </form> : <p>This copy has no shared points to connect to yet.</p>}
            <button type="button" onClick={reset}>Reset my additions</button>
          </section>
        </section><aside ref={detailRef} tabIndex={-1} className="guest-world__detail" aria-live="polite"><p className="guest-world__eyebrow">{source ? "SOURCE EXCERPT" : "FOLLOW A THREAD"}</p>
          {source ? <><h2>From the owner’s notes</h2><p>{source.evidence_role === "context" ? "Evidence role: context, not direct support." : source.evidence_role === "support" ? "Evidence role: support." : "Evidence role unavailable."}</p><p className="guest-world__excerpt">{source.text}</p><p><a href={fragment(snapshot.release_id, sharedNodes.some(node => node.id === selectedNode) ? selectedNode : null, source.id)}>Link to this excerpt</a></p><button type="button" onClick={() => navigate(selectedNode, null)}>← Back to connections</button></>
            : active ? <><h2>{active.label}</h2><p>{active.kind}</p>{active.temporary ? <p>This point is your temporary addition, not part of the shared World.</p> : <><small>Name: {active.name_basis} · Classification: {active.kind_basis}</small><p><a href={fragment(snapshot.release_id, active.id)}>Link to this point</a></p><div className="guest-world__citations">{[...new Set([...active.name_citations, ...active.kind_citations])].map(citationButton)}</div></>}<h3>Connections</h3>{connected.length ? <ul>{connected.map(edge => { const other = edge.source === active.id ? edge.target : edge.source; return <li key={edge.id}><p>{labels.get(edge.source)} <em>{edge.label}</em> {labels.get(edge.target)}</p><small>{edge.temporary ? "Your temporary connection · not sourced from the shared World" : <>{edge.basis} · {edge.temporal === "unknown" ? "When this happened is not specified" : edge.temporal === "timeless" ? "Timeless" : edge.temporal}</>}</small><div className="guest-world__citations"><button type="button" onClick={() => navigate(other, null)}>Explore {labels.get(other)}</button>{edge.citations.map(citationButton)}</div></li>; })}</ul> : <p>No connections were included for this point.</p>}</>
              : <><h2>Every story has a trail.</h2><p>Select a point to follow it through the owner’s shared notes.</p></>}
        </aside></div>
        {exampleValue !== undefined && !example && <p role="alert">This saved example is unavailable.</p>}
        {example && <section ref={exampleRef} tabIndex={-1} className="guest-world__example" aria-labelledby="guest-example-title">
          <p className="guest-world__eyebrow">OWNER-AUTHORED SAVED EXAMPLE</p><h2 id="guest-example-title">{example.title}</h2>
          <p>This is a saved scene, not a live generation. Your temporary additions were not used.</p>
          <div className="guest-world__example-body">{example.body}</div>
          {example.image && <img src={`/api/live/guest-releases/${encodeURIComponent(publicId)}/releases/${encodeURIComponent(snapshot.release_id)}/assets/${encodeURIComponent(example.image.id)}`} alt={example.image.description} />}
          <p>Selected references. They do not automatically prove the scene.</p>
          <div className="guest-world__citations">{example.references.map(citationButton)}</div>
          {choiceValue !== undefined && !choice && <p role="alert">This saved choice is unavailable.</p>}
          {choice && <section className="guest-world__choice" aria-labelledby="guest-choice-heading">
            <h3 id="guest-choice-heading">{choice.prompt}</h3>
            <p>Choose a prewritten possibility. These owner-authored outcomes are not a record of play and do not use your additions.</p>
            <div role="group" aria-labelledby="guest-choice-heading" className="guest-world__choice-options">
              {choice.options.map((option, index) => <button key={index} type="button" aria-pressed={selectedChoice === index}
                onClick={() => setSelectedChoice(index as 0 | 1)}>{option.label}</button>)}
            </div>
            <div aria-live="polite" aria-atomic="true">{selectedChoice !== null && <p className="guest-world__choice-outcome">{choice.options[selectedChoice].outcome}</p>}</div>
            <button type="button" onClick={() => setSelectedChoice(null)}>Reset choice</button>
          </section>}
        </section>}
        {choiceValue !== undefined && !example && <p role="alert">This saved choice is unavailable.</p>}
        {snapshot.manifest.assets.length > 0 && <section className="guest-world__gallery"><h2>From the World</h2>{snapshot.manifest.assets.map((asset, index) => <img key={asset.id} src={`/api/live/guest-releases/${encodeURIComponent(publicId)}/releases/${encodeURIComponent(snapshot.release_id)}/assets/${encodeURIComponent(asset.id)}`} alt={`Shared World image ${index + 1}`} />)}</section>}
        <section className="guest-world__next"><h2>Make room for your own story.</h2><p>The shared World stays unchanged. Your temporary additions cannot be transferred to an account.</p><a href={dungeonMindLoginHref("/")}>Sign in to Buddy →</a></section></>}
    <footer className="guest-world__footer">A shared copy · Your private Worlds stay separate</footer>
  </main>;
}
