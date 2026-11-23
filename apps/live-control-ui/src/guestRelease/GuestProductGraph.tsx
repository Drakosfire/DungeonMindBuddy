import { useEffect, useState } from "react";
import { IsolatedEntry, NativeGraphDemo } from "../appEntryShared";
import { dungeonMindLoginHref } from "../auth/HostedAuthGate";
import { AppChrome } from "../chrome/AppChrome";
import type { NativeGraphDemoApi } from "../nativeGraphDemo/nativeGraphDemoApi";
import { createGuestGraphApi, guestGraphTerm, parseGuestGraphRelease, type GuestGraphRelease } from "./guestGraphModel";
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
      : <NativeGraphDemo key={`${publicId}:${ready.copy.release_id}`} api={ready.api} embedded mode="guest" worldTitle="Shared World" renderGuestNodeDetails={(id) => <GuestEvidence copy={ready.copy} nodeId={id} />} />}
  </AppChrome></IsolatedEntry>;
}

function GuestEvidence({ copy, nodeId }: { copy: GuestGraphRelease; nodeId: string }) {
  const node = copy.manifest.graph.nodes.find((item) => item.id === nodeId);
  if (!node) return null;
  const sources = new Map(copy.manifest.sources.map((source) => [source.id, source]));
  const labels = new Map(copy.manifest.graph.nodes.map((item) => [item.id, item.label]));
  const when = (value?: string) => value === "unknown" ? "When this applied is not specified" : value === "timeless" ? "Timeless" : value;
  const excerpt = (id: string) => {
    const source = sources.get(id);
    if (!source) return null;
    const characters = Array.from(source.text.replace(/\s+/gu, " ").trim());
    const preview = characters.length > 64 ? `${characters.slice(0, 64).join("").trimEnd()}…` : characters.join("");
    return <details key={id}><summary>Read {source.evidence_role === "context" ? "context" : "source"}{preview ? `: ${preview}` : ""}</summary><p>{source.evidence_role === "context" ? "Context, not direct support." : "Evidence role: support."}</p><blockquote>{source.text}</blockquote></details>;
  };
  return <section className="guest-product-graph__evidence" aria-label="Shared source evidence"><h3>Sources in this copy</h3>
    <p>Name: {node.name_basis}{node.name_temporal ? ` · ${when(node.name_temporal)}` : ""}</p>
    <p>Classification: {node.kind_basis}{node.kind_temporal ? ` · ${when(node.kind_temporal)}` : ""}</p>
    {[...new Set([...node.name_citations, ...node.kind_citations])].map(excerpt)}
    {copy.manifest.graph.edges.filter((edge) => edge.source === nodeId || edge.target === nodeId).map((edge) => <section key={edge.id}>
      <h4>{labels.get(edge.source)} · {guestGraphTerm(edge.label)} · {labels.get(edge.target)}</h4>
      <p>{edge.basis} · {edge.temporal === "unknown" ? "When this happened is not specified" : edge.temporal === "timeless" ? "Timeless" : edge.temporal}</p>
      {[...new Set(edge.citations)].map(excerpt)}
    </section>)}
  </section>;
}
