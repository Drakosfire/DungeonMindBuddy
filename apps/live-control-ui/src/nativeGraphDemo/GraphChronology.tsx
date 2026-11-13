import { useEffect, useState } from "react";
import { buildGraphChronology } from "./graphChronologyModel";
import type { NativeGraph, NativeGraphDemoApi } from "./nativeGraphDemoApi";

export function GraphChronology({ graph, read, relatedTo, onExplore }: {
  graph: NativeGraph;
  read: NonNullable<NativeGraphDemoApi["readChronology"]>;
  relatedTo?: string;
  onExplore: (nodeId: string) => void;
}) {
  const [result, setResult] = useState<{
    graph: NativeGraph;
    events: ReturnType<typeof buildGraphChronology> | null;
    partial?: boolean;
  }>();
  const [campaign, setCampaign] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    void read(graph, abort.signal).then(catalogue => {
      if (!abort.signal.aborted) setResult({
        graph, events: buildGraphChronology(graph, catalogue),
        partial: catalogue.completeness.status === "partial",
      });
    }).catch(() => {
      if (!abort.signal.aborted) setResult({ graph, events: null });
    });
    return () => abort.abort();
  }, [graph, read]);

  if (result?.graph !== graph) return <p role="status">Loading chronology…</p>;
  if (!result.events) return <p role="alert">Chronology could not be loaded. Refresh the graph and try again.</p>;
  const labels = new Map(graph.nodes.map(node => [node.id, node.name]));
  const relatedIds = new Set([relatedTo]);
  if (relatedTo) {
    for (const edge of graph.edges) {
      if (edge.source_id === relatedTo) relatedIds.add(edge.target_id);
      if (edge.target_id === relatedTo) relatedIds.add(edge.source_id);
    }
  }
  const relatedEvents = relatedTo ? result.events.filter(event => relatedIds.has(event.node.id)) : result.events;
  const campaigns = [...new Set(relatedEvents.flatMap(event => event.campaignIds))];
  const events = relatedEvents.filter(event => !campaign || event.campaignIds.includes(campaign));
  function sessionOrder(event: typeof events[number]): number {
    const sessions = event.placementSessions.get(campaign);
    return sessions?.size === 1 ? [...sessions][0]! : Infinity;
  }
  if (campaign) events.sort((a, b) => sessionOrder(a) - sessionOrder(b) || a.node.name.localeCompare(b.node.name));

  return <section aria-label="World chronology">
    {relatedTo && <h3>Events connected to {labels.get(relatedTo)}</h3>}
    <label>Campaign <select value={campaign} onChange={event => setCampaign(event.target.value)}>
      <option value="">All campaigns</option>
      {campaigns.map(id => <option key={id} value={id}>{labels.get(id)}</option>)}
    </select></label>
    {result.partial && <p role="status">Partial chronology</p>}
    {events.length === 0 && <p>No Events found.</p>}
    <ul>{events.map(event => <li key={event.node.id}>
      <button type="button" onClick={() => onExplore(event.node.id)}>{event.node.name}</button>
      <div>{event.occurrences.join(" · ") || (event.placementSessions.size ? "Campaign placement recorded" : "Occurrence unknown")}</div>
      {[...event.placementSessions].filter(([id]) => !campaign || campaign === id).map(([id, sessions]) =>
        <div key={id}>{labels.get(id)} · {sessions.size > 1 ? "Conflicting placements · " : ""}
          {[...sessions].sort((a, b) => a - b).map(session => `Session ${session}`).join(", ")}
        </div>)}
      {event.sourceSessions.length > 0 && <div>Source sessions {event.sourceSessions.join(", ")}</div>}
    </li>)}</ul>
  </section>;
}
