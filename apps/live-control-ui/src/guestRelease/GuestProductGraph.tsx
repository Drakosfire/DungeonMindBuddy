import { useEffect, useRef, useState } from "react";
import { IsolatedEntry, NativeGraphDemo } from "../appEntryShared";
import { dungeonMindLoginHref } from "../auth/HostedAuthGate";
import { AppChrome } from "../chrome/AppChrome";
import type { NativeGraphDemoApi } from "../nativeGraphDemo/nativeGraphDemoApi";
import { createGuestGraphApi, guestGraphTerm, parseGuestGraphRelease, type GuestGraphRelease, type GuestGraphOverlay } from "./guestGraphModel";
import "./guestReleasePage.css";

type Ready = { copy: GuestGraphRelease; api: NativeGraphDemoApi };

/** The product Graph reads only the immutable public copy, never a managed World. */
export function GuestProductGraph({ publicId }: { publicId: string }) {
  const [state, setState] = useState<{ publicId: string; ready: Ready | null; unavailable: boolean }>({ publicId, ready: null, unavailable: false });
  useEffect(() => {
    const controller = new AbortController();
    setState({ publicId, ready: null, unavailable: false });
    fetch(`/api/live/guest-releases/${encodeURIComponent(publicId)}`, { credentials: "omit", cache: "no-store", signal: controller.signal })
      .then((response) => { if (!response.ok) throw new Error("unavailable"); return response.json() as Promise<unknown>; })
      .then(parseGuestGraphRelease)
      .then(async (copy) => ({ copy, api: await createGuestGraphApi(publicId, copy) }))
      .then((ready) => { if (!controller.signal.aborted) setState({ publicId, ready, unavailable: false }); })
      .catch(() => { if (!controller.signal.aborted) setState({ publicId, ready: null, unavailable: true }); });
    return () => controller.abort();
  }, [publicId]);
  const ready = state.publicId === publicId ? state.ready : null;
  const unavailable = state.publicId === publicId && state.unavailable;
  return <IsolatedEntry><AppChrome activeRoute="graph" localOnlyNavigation workspaceLayout="bounded">
    <div className="guest-product-graph__notice"><strong>Shared World · demo</strong><span>Explore the released copy in Graph. Changes here do not affect the private World.</span><a href="/">Demo home</a><a href={dungeonMindLoginHref("/graph")}>Sign in to create your World</a></div>
    {unavailable ? <main role="alert"><h1>This shared World is unavailable</h1><p>The owner may have withdrawn it.</p><a href="/">Return to demo home</a></main>
      : !ready ? <main role="status">Opening the shared graph…</main>
      : <GuestGraphSession key={`${publicId}:${ready.copy.release_id}`} publicId={publicId} ready={ready} />}
  </AppChrome></IsolatedEntry>;
}

function GuestGraphSession({ publicId, ready }: { publicId: string; ready: Ready }) {
  const [overlay, setOverlay] = useState<GuestGraphOverlay>({ nodes: [], edges: [] });
  const [api, setApi] = useState<NativeGraphDemoApi | null>(ready.api);
  const [name, setName] = useState("");
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [predicate, setPredicate] = useState("");
  const [message, setMessage] = useState("");
  const [graphError, setGraphError] = useState(false);
  const revision = useRef(0);
  const pointLimit = Math.min(50, 512 - ready.copy.manifest.graph.nodes.length);
  const edgeLimit = Math.min(100, 1024 - ready.copy.manifest.graph.edges.length);
  const allNodes = [...ready.copy.manifest.graph.nodes.map((node) => ({ id: node.id, name: node.label })), ...overlay.nodes];
  useEffect(() => {
    let current = true;
    const expectedRevision = revision.current;
    void createGuestGraphApi(publicId, ready.copy, overlay).then((next) => { if (current && revision.current === expectedRevision) { setGraphError(false); setApi(next); } }).catch(() => { if (current && revision.current === expectedRevision) { setApi(null); setGraphError(true); } });
    return () => { current = false; };
  }, [publicId, ready.copy, overlay]);
  function addPoint(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || overlay.nodes.length >= pointLimit) return;
    const id = `guest-point:${crypto.randomUUID()}`;
    revision.current += 1;
    setOverlay((old) => ({ ...old, nodes: [...old.nodes, { id, name: trimmed }] }));
    setName(""); setSource(id); setMessage(`Added ${trimmed}. Select it in the graph to explore it, or connect it below.`);
  }
  function addConnection(event: React.FormEvent) {
    event.preventDefault();
    const label = predicate.trim();
    if (!label || source === target || !allNodes.some((node) => node.id === source) || !allNodes.some((node) => node.id === target) || overlay.edges.length >= edgeLimit) return;
    revision.current += 1;
    setOverlay((old) => ({ ...old, edges: [...old.edges, { id: `guest-edge:${crypto.randomUUID()}`, source_id: source, target_id: target, predicate: label }] }));
    setPredicate(""); setMessage("Added your temporary connection.");
  }
  function reset() {
    revision.current += 1;
    setApi(null); setOverlay({ nodes: [], edges: [] }); setName(""); setSource(""); setTarget(""); setPredicate(""); setMessage("Your additions were reset to the shared copy.");
  }
  function closeTools(details: HTMLDetailsElement | null) {
    if (!details) return;
    details.open = false;
    details.querySelector("summary")?.focus();
  }
  return <>
    <details className="guest-product-graph__tools" onKeyDown={(event) => { if (event.key === "Escape" && event.currentTarget.open) { event.preventDefault(); event.stopPropagation(); closeTools(event.currentTarget); } }}><summary>Add to this graph</summary>
      <div className="guest-product-graph__tools-panel"><p>Your additions stay in this tab until you leave or reset. They do not change the shared World.</p>
      <form onSubmit={addPoint}><label>New point <input value={name} maxLength={120} onChange={(event) => setName(event.target.value)} /></label><button type="submit" disabled={!name.trim() || overlay.nodes.length >= pointLimit}>Add point</button></form>
      <form onSubmit={addConnection}>
        <label>From <select value={source} onChange={(event) => setSource(event.target.value)}><option value="">Choose a point</option>{allNodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
        <label>Connection <input value={predicate} maxLength={120} onChange={(event) => setPredicate(event.target.value)} /></label>
        <label>To <select value={target} onChange={(event) => setTarget(event.target.value)}><option value="">Choose a point</option>{allNodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select></label>
        <button type="submit" disabled={!source || !target || source === target || !predicate.trim() || overlay.edges.length >= edgeLimit}>Connect points</button>
      </form>
      <button type="button" onClick={reset}>Reset my additions</button>
      <p role="status">{message}</p>
      <button type="button" onClick={(event) => closeTools(event.currentTarget.closest("details"))}>Done</button></div>
    </details>
    {api ? <NativeGraphDemo api={api} embedded mode="guest" worldTitle="Shared World" renderGuestNodeDetails={(id, onExplore) => <GuestEvidence copy={ready.copy} overlay={overlay} nodeId={id} onExplore={onExplore} />} /> : graphError ? <p role="alert">This graph could not be updated. Try resetting your additions.</p> : <p role="status">Updating your graph…</p>}
  </>;
}

function GuestEvidence({ copy, overlay, nodeId, onExplore }: { copy: GuestGraphRelease; overlay: GuestGraphOverlay; nodeId: string; onExplore: (nodeId: string) => void }) {
  const node = copy.manifest.graph.nodes.find((item) => item.id === nodeId);
  const temporary = overlay.nodes.find((item) => item.id === nodeId);
  if (!node && !temporary) return null;
  const sources = new Map(copy.manifest.sources.map((source) => [source.id, source]));
  const labels = new Map([...copy.manifest.graph.nodes.map((item) => [item.id, item.label] as const), ...overlay.nodes.map((item) => [item.id, item.name] as const)]);
  const when = (value?: string) => value === "unknown" ? "When this applied is not specified" : value === "timeless" ? "Timeless" : value;
  const excerpt = (id: string) => {
    const source = sources.get(id);
    if (!source) return null;
    const characters = Array.from(source.text.replace(/\s+/gu, " ").trim());
    const preview = characters.length > 64 ? `${characters.slice(0, 64).join("").trimEnd()}…` : characters.join("");
    return <details key={id}><summary>Read {source.evidence_role === "context" ? "context" : "source"}{preview ? `: ${preview}` : ""}</summary><p>{source.evidence_role === "context" ? "Context, not direct support." : "Evidence role: support."}</p><blockquote>{source.text}</blockquote></details>;
  };
  return <section className="guest-product-graph__evidence" aria-label="Shared source evidence"><h3>Sources in this copy</h3>
    {temporary ? <p>Your temporary point · not sourced from the shared World.</p> : null}
    {node ? <><p>Name: {node.name_basis}{node.name_temporal ? ` · ${when(node.name_temporal)}` : ""}</p>
    <p>Classification: {node.kind_basis}{node.kind_temporal ? ` · ${when(node.kind_temporal)}` : ""}</p>
    {[...new Set([...node.name_citations, ...node.kind_citations])].map(excerpt)}</> : null}
    {copy.manifest.graph.edges.filter((edge) => edge.source === nodeId || edge.target === nodeId).map((edge) => <section key={edge.id}>
      <h4>{labels.get(edge.source)} · {guestGraphTerm(edge.label)} · {labels.get(edge.target)}</h4>
      <p>{edge.basis} · {edge.temporal === "unknown" ? "When this happened is not specified" : edge.temporal === "timeless" ? "Timeless" : edge.temporal}</p>
      <button type="button" onClick={() => onExplore(edge.source === nodeId ? edge.target : edge.source)}>Explore {labels.get(edge.source === nodeId ? edge.target : edge.source)}</button>
      {[...new Set(edge.citations)].map(excerpt)}
    </section>)}
    {overlay.edges.filter((edge) => edge.source_id === nodeId || edge.target_id === nodeId).map((edge) => <section key={edge.id}>
      <h4>{labels.get(edge.source_id)} · {edge.predicate} · {labels.get(edge.target_id)}</h4>
      <p>Your temporary connection · not sourced from the shared World.</p>
      <button type="button" onClick={() => onExplore(edge.source_id === nodeId ? edge.target_id : edge.source_id)}>Explore {labels.get(edge.source_id === nodeId ? edge.target_id : edge.source_id)}</button>
    </section>)}
  </section>;
}
