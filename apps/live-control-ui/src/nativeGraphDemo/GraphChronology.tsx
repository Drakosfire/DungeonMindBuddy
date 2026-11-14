import { useEffect, useRef, useState } from "react";
import { nativeGraphPresentation } from "./nativeGraphPresentation";
import { buildGraphChronology } from "./graphChronologyModel";
import type { NativeGraph, NativeGraphDemoApi } from "./nativeGraphDemoApi";

export function GraphChronology({ graph, read, relatedTo, onExplore, strip = false, selectedEvent, connectedIds }: {
  graph: NativeGraph;
  read: NonNullable<NativeGraphDemoApi["readChronology"]>;
  relatedTo?: string;
  strip?: boolean;
  selectedEvent?: string;
  connectedIds?: ReadonlySet<string>;
  onExplore: (nodeId: string) => void;
}) {
  const [result, setResult] = useState<{
    graph: NativeGraph;
    events: ReturnType<typeof buildGraphChronology> | null;
    partial?: boolean;
  }>();
  const eventButtons = useRef(new Map<string, HTMLButtonElement>());
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

  const labels = new Map(graph.nodes.map(node => [node.id, node.name]));
  const relatedIds = new Set([relatedTo]);
  if (relatedTo) {
    for (const edge of graph.edges) {
      if (edge.source_id === relatedTo) relatedIds.add(edge.target_id);
      if (edge.target_id === relatedTo) relatedIds.add(edge.source_id);
    }
  }
  const loading = result?.graph !== graph;
  const catalogue = loading ? null : result.events;
  if (!catalogue) {
    const status = loading
      ? <p role="status">Loading chronology…</p>
      : <p role="alert">Chronology could not be loaded. Refresh the graph and try again.</p>;
    if (!strip) return status;
    const connected = graph.nodes.filter(node => relatedIds.has(node.id)
      && nativeGraphPresentation(node).displayKind === "event");
    return <section className="native-demo-event-strip" aria-label="Connected Events">
      {status}
      <ul>{connected.map(node => <li key={node.id}>
        <button type="button" aria-pressed={node.id === selectedEvent}
          data-connected={connectedIds?.has(node.id) || undefined}
          onClick={() => onExplore(node.id)}>{node.name}</button>
      </li>)}</ul>
    </section>;
  }
  const relatedEvents = relatedTo ? catalogue.filter(event => relatedIds.has(event.node.id)) : catalogue;
  const campaigns = [...new Set(relatedEvents.flatMap(event => event.campaignIds))];
  const events = relatedEvents.filter(event => !campaign || event.campaignIds.includes(campaign));
  function sessionOrder(event: typeof events[number]): number {
    const sessions = event.placementSessions.get(campaign);
    return sessions?.size === 1 ? [...sessions][0]! : Infinity;
  }
  if (campaign) events.sort((a, b) => sessionOrder(a) - sessionOrder(b) || a.node.name.localeCompare(b.node.name));

  const campaignAxis = "dungeonbuddy.scope:campaign";
  const selectedScopes = new Set(catalogue.flatMap(event =>
    event.placements.flatMap(placement =>
      placement.value.kind === "entity_ref" && placement.value.entity_id === campaign
        ? (placement.metadata.scope ?? []).filter(binding => binding.axis === campaignAxis).map(binding => binding.value)
        : [])));
  const candidateScope = selectedScopes.size === 1 ? [...selectedScopes][0] : undefined;
  const campaignLabelsByScope = new Map<string, Set<string>>();
  for (const event of catalogue) {
    for (const placement of event.placements) {
      if (placement.value.kind !== "entity_ref") continue;
      for (const binding of placement.metadata.scope ?? []) {
        if (binding.axis !== campaignAxis) continue;
        const key = JSON.stringify([binding.value]);
        const ids = campaignLabelsByScope.get(key) ?? new Set<string>();
        ids.add(placement.value.entity_id);
        campaignLabelsByScope.set(key, ids);
      }
    }
  }
  const scopeCampaigns = campaignLabelsByScope.get(JSON.stringify([candidateScope]));
  const selectedScope = scopeCampaigns?.size === 1 && scopeCampaigns.has(campaign)
    ? candidateScope : undefined;
  const orderByEvent = new Map<string, { label: string; other: string; id: string; scope: string }[]>();
  const eventIds = new Set(catalogue.map(event => event.node.id));
  for (const event of catalogue) {
    for (const assertion of event.assertions) {
      if (assertion.predicate !== "dungeonbuddy.custom:precedes" || assertion.value.kind !== "entity_ref") continue;
      if (campaign && (!selectedScope || !(assertion.metadata.scope ?? []).some(
        binding => binding.axis === campaignAxis && binding.value === selectedScope,
      ))) continue;
      const target = assertion.value.entity_id;
      if (!eventIds.has(target)) continue;
      for (const [id, other, label] of [[event.node.id, target, "Recorded before"], [target, event.node.id, "Recorded after"]]) {
        const links = orderByEvent.get(id) ?? [];
        links.push({ label, other, id: assertion.assertion_id, scope: JSON.stringify((assertion.metadata.scope ?? []).filter(binding => binding.axis === campaignAxis).map(binding => binding.value).sort()) });
        orderByEvent.set(id, links);
      }
    }
  }

  const cyclic = new Set<string>();
  const linksByScope = new Map<string, Map<string, NonNullable<ReturnType<typeof orderByEvent.get>>>>();
  for (const [id, links] of orderByEvent) {
    for (const link of links) {
      let scoped = linksByScope.get(link.scope);
      if (!scoped) {
        scoped = new Map();
        linksByScope.set(link.scope, scoped);
      }
      const eventLinks = scoped.get(id) ?? [];
      eventLinks.push(link);
      scoped.set(id, eventLinks);
    }
  }
  for (const scoped of linksByScope.values()) {
    const visited = new Set<string>();
    const finished: string[] = [];
    for (const root of scoped.keys()) {
      const pending = [{ id: root, exit: false }];
      while (pending.length) {
        const { id, exit } = pending.pop()!;
        if (exit) { finished.push(id); continue; }
        if (visited.has(id)) continue;
        visited.add(id);
        pending.push({ id, exit: true });
        for (const link of scoped.get(id) ?? []) {
          if (link.label === "Recorded before") pending.push({ id: link.other, exit: false });
        }
      }
    }
    visited.clear();
    for (const root of finished.reverse()) {
      if (visited.has(root)) continue;
      const component = [root];
      visited.add(root);
      for (const id of component) {
        for (const link of scoped.get(id) ?? []) {
          if (link.label !== "Recorded after" || visited.has(link.other)) continue;
          visited.add(link.other);
          component.push(link.other);
        }
      }
      if (component.length > 1 || scoped.get(root)?.some(link => link.other === root)) {
        for (const id of component) cyclic.add(id);
      }
    }

  }

  if (strip) {
    const sessionNumber = (event: typeof events[number]) => {
      const placements = campaign ? [event.placementSessions.get(campaign) ?? new Set<number>()] : [...event.placementSessions.values()];
      return placements.length === 1 && placements[0].size === 1 ? [...placements[0]][0] : undefined;
    };
    const byId = new Map(events.map(event => [event.node.id, event]));
    const edgesByScope = new Map<string, Map<string, Set<string>>>();
    for (const [source, links] of orderByEvent) {
      if (!byId.has(source) || cyclic.has(source)) continue;
      for (const link of links) {
        if (link.label !== "Recorded before" || !byId.has(link.other) || cyclic.has(link.other)) continue;
        const edges = edgesByScope.get(link.scope) ?? new Map<string, Set<string>>();
        const targets = edges.get(source) ?? new Set<string>();
        targets.add(link.other);
        edges.set(source, targets);
        edgesByScope.set(link.scope, edges);
      }
    }
    const recordedIds = new Set<string>();
    const recorded: typeof events = [];
    if (edgesByScope.size === 1) {
      const [edges] = edgesByScope.values();
      const incoming = new Map<string, number>();
      for (const [source, targets] of edges) {
        if (!incoming.has(source)) incoming.set(source, 0);
        for (const target of targets) incoming.set(target, (incoming.get(target) ?? 0) + 1);
      }
      const ready = [...incoming].filter(([, count]) => count === 0).map(([id]) => id);
      for (const id of ready) {
        recordedIds.add(id);
        recorded.push(byId.get(id)!);
        for (const target of edges.get(id) ?? []) {
          const remaining = incoming.get(target)! - 1;
          incoming.set(target, remaining);
          if (remaining === 0) ready.push(target);
        }
      }
    }
    const campaignIds = new Set(events.flatMap(event => event.campaignIds));
    const canCompareSessions = Boolean(campaign) || campaignIds.size === 1;
    const ordered = canCompareSessions
      ? events.filter(event => !recordedIds.has(event.node.id) && sessionNumber(event) !== undefined)
        .sort((a, b) => sessionNumber(a)! - sessionNumber(b)!)
      : [];
    const orderedIds = new Set(ordered.map(event => event.node.id));
    const unplaced = events.filter(event => !recordedIds.has(event.node.id) && !orderedIds.has(event.node.id));
    return <section className="native-demo-event-strip" aria-label="Connected Events">
      {campaigns.length > 0 && <label>Campaign <select value={campaign} onChange={event => setCampaign(event.target.value)}>
        <option value="">All campaigns</option>
        {campaigns.map(id => <option key={id} value={id}>{labels.get(id)}</option>)}
      </select></label>}
      {result?.partial && <small>Partial chronology</small>}
      {recorded.length > 0 && <small>Only the labeled links establish order between Events.</small>}
      {([{ items: recorded, label: "Recorded in-world links" },
        { items: ordered, label: "Campaign session order" },
        { items: unplaced, label: "Unplaced Events" }]).map(({ items, label }) => {
        return items.length > 0 && <div key={label}>
          <strong>{label}</strong>
          <ul>{items.map(event => <li key={event.node.id}>
            <button type="button" aria-pressed={event.node.id === selectedEvent}
              data-connected={connectedIds?.has(event.node.id) || undefined}
              onClick={() => onExplore(event.node.id)}>{event.node.name}</button>
            {sessionNumber(event) !== undefined && <small>Session {sessionNumber(event)}</small>}
            {cyclic.has(event.node.id) && <small>Conflicting recorded order</small>}
            {recordedIds.has(event.node.id) && orderByEvent.get(event.node.id)
              ?.filter(link => recordedIds.has(link.other))
              .map(link => <small key={link.label + link.id}>{link.label} {labels.get(link.other)}</small>)}
            {event.sourceSessions.length > 0 && <small>Source {event.sourceSessions.join(", ")}</small>}
          </li>)}</ul>
        </div>;
      })}
    </section>;
  }

  const sessions = new Map<number, string>();
  for (const event of events) {
    const session = sessionOrder(event);
    if (Number.isFinite(session) && !sessions.has(session)) sessions.set(session, event.node.id);
  }
  const point = (angle: number) => {
    const radius = 14 + 8 * angle;
    return [150 + radius * Math.cos(angle), 150 + radius * Math.sin(angle)];
  };
  const path = Array.from({ length: 121 }, (_, index) =>
    `${index ? "L" : "M"}${point(index / 10).join(",")}`).join(" ");
  // Limit overview markers; the complete session sequence remains in the list.
  const stride = Math.max(1, Math.ceil(sessions.size / 12));

  return <section aria-label="World chronology">
    {relatedTo && <h3>Events connected to {labels.get(relatedTo)}</h3>}
    <label>Campaign <select value={campaign} onChange={event => setCampaign(event.target.value)}>
      <option value="">All campaigns</option>
      {campaigns.map(id => <option key={id} value={id}>{labels.get(id)}</option>)}
    </select></label>
    {result?.partial && <p role="status">Partial chronology</p>}
    {events.length === 0 && <p>No Events found.</p>}
    {campaign && sessions.size > 0 && <details>
      <summary>Campaign session spiral</summary>
      <p>Read outward by Campaign session. Spacing is illustrative. Events with unresolved placement appear in the list.</p>
      {stride > 1 && <p>The spiral shows selected sessions. See the list for every recorded placement.</p>}
      <svg viewBox="0 0 300 300" width="100%" style={{ maxWidth: 420 }} aria-label="Campaign session spiral">
        <path d={path} fill="none" stroke="currentColor" opacity={0.45} />
        {[...sessions].map(([session, id], index) => {
          if (index % stride !== 0 && index !== sessions.size - 1) return null;
          const [x, y] = point(0.4 + 11.6 * index / Math.max(1, sessions.size - 1));
          const focusEvent = () => eventButtons.current.get(id)?.focus();
          return <g key={session} role="button" tabIndex={0} aria-label={`Go to Session ${session}`}
            onClick={focusEvent} onKeyDown={event => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                focusEvent();
              }
            }}>
            <circle cx={x} cy={y} r={7} fill="currentColor" />
            <text x={x + 10} y={y - 8} fill="currentColor" fontSize={12}>{session}</text>
          </g>;
        })}
      </svg>
    </details>}
    <ul>{events.map(event => <li key={event.node.id}>
      <button type="button" ref={element => {
        if (element) eventButtons.current.set(event.node.id, element);
        else eventButtons.current.delete(event.node.id);
      }} onClick={() => onExplore(event.node.id)}>{event.node.name}</button>
      <div>{event.occurrences.join(" · ") || (event.placementSessions.size ? "Campaign placement recorded" : "Occurrence unknown")}</div>
      {[...event.placementSessions].filter(([id]) => !campaign || campaign === id).map(([id, sessions]) =>
        <div key={id}>{labels.get(id)} · {sessions.size > 1 ? "Conflicting placements · " : ""}
          {[...sessions].sort((a, b) => a - b).map(session => `Session ${session}`).join(", ")}
        </div>)}
      {cyclic.has(event.node.id) && <div>Conflicting recorded order</div>}
      {orderByEvent.get(event.node.id)?.map(link => <div key={link.label + link.id}>
        {link.label} <button type="button" onClick={() => onExplore(link.other)}>{labels.get(link.other)}</button>
        {!campaign && link.scope !== "[]" && <small> · {campaignLabelsByScope.get(link.scope)?.size === 1
          ? labels.get([...campaignLabelsByScope.get(link.scope)!][0]!)
          : "Campaign name unavailable"}</small>}
      </div>)}
      {event.sourceSessions.length > 0 && <div>Source sessions {event.sourceSessions.join(", ")}</div>}
    </li>)}</ul>
  </section>;
}
