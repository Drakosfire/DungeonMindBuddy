import { useState, type Ref } from "react";
import { type NativeAssertion, type NativeGraphEntity } from "../api/nativeGraphInspection";
import { nativeObjectEvidenceChoices } from "../graphLens/nativeObjectEvidence";
import { projectNativeObject } from "../graphLens/nativeObjectProjection";
import { SourceCitationEvidence } from "../planSurface/components/SourceCitationEvidence";
import { NativeObjectStatblock } from "../graphLens/NativeObjectStatblock";
import { assertionStatus, compactNodeLabel } from "./graphNodeExplorer";

import type { NativeGraphNode, NativeGraphEdge } from "./nativeGraphDemoApi";
import { nativeGraphPresentation } from "./nativeGraphPresentation";

/** Single owner of graph explorer chrome, identity, loading and evidence presentation. */
export function NativeGraphNodeExplorer({ node, revision, detail, labels, entityOnly = false, partial = false, navigationDisabled = false, onExplore, onFocus, onClose, onExitFocus, onBack, previousLabel, headingRef, mode = "managed", status = "ready", error, connections = [] }: {
  node: NativeGraphNode; revision: string; detail: NativeGraphEntity | null; labels: ReadonlyMap<string, string>;
  entityOnly?: boolean; partial?: boolean; navigationDisabled?: boolean; onExplore: (entityId: string) => void;
  onFocus: () => void; onClose: () => void; onExitFocus?: () => void; onBack?: () => void; previousLabel?: string;
  headingRef?: Ref<HTMLHeadingElement>; mode?: "managed" | "playground"; status?: "idle" | "loading" | "ready" | "unavailable" | "error"; error?: string | null; connections?: readonly NativeGraphEdge[];
}) {
  const presentation = nativeGraphPresentation(node);
  return <section className="native-demo-action-card native-demo-object-details" aria-labelledby="native-demo-selected-object-title">
    <header className="graph-node-explorer__navbar">
      <h2 ref={headingRef} tabIndex={-1} id="native-demo-selected-object-title">{compactNodeLabel(node)}</h2>
      <nav aria-label="Node explorer controls">
        {onBack ? <button type="button" disabled={navigationDisabled} onClick={onBack} aria-label={`Back to ${previousLabel ?? "previous object"}`} title={`Back to ${previousLabel ?? "previous object"}`}>← Back</button> : null}
        <button type="button" onClick={onFocus}>Focus</button>
        {onExitFocus ? <button type="button" onClick={onExitFocus}>Exit focus</button> : null}
        <button type="button" onClick={onClose} aria-label="Close details">Close</button>
      </nav>
    </header>
    <div className="graph-node-explorer__identity">
      <span className="native-demo-copy">{presentation.displayKind}</span>
      {presentation.recordedNames.length > 1 ? <details className="graph-node-explorer__names"><summary>Recorded names ({presentation.recordedNames.length})</summary><p>Display label only, not a preferred name or current title.</p><ul>{presentation.recordedNames.map((name) => <li key={name}>{name}</li>)}</ul></details> : null}
    </div>
    {mode === "managed" ? status === "loading" ? <p role="status">Loading this object from the loaded World revision…</p>
      : status === "ready" && detail ? <NodeDossier detail={detail} entityId={node.id} labels={labels} entityOnly={entityOnly} partial={partial} navigationDisabled={navigationDisabled} onExplore={onExplore} />
        : <p role={status === "error" ? "alert" : "status"}>{error ?? "Select this object to inspect its loaded World revision."}</p>
      : <section className="native-demo-object-details__connections" aria-labelledby="native-demo-selected-connections-title">
        <h3 id="native-demo-selected-connections-title">Connections in this loaded snapshot</h3>
        {connections.length ? <ul>{connections.map((edge) => {
          const outgoing = edge.source_id === node.id;
          const otherId = outgoing ? edge.target_id : edge.source_id;
          const otherName = labels.get(otherId) ?? "Unknown object in this snapshot";
          return <li key={edge.id}>{outgoing ? `${edge.predicate} → ${otherName}` : `${otherName} → ${edge.predicate} → ${compactNodeLabel(node)}`}</li>;
        })}</ul> : <p>No listed connections for this object in this loaded snapshot.</p>}
        {partial ? <p role="status">This graph read is partial, so additional connections may not be listed.</p> : null}
        <details><summary>Snapshot revision</summary><code>{revision}</code></details>
      </section>}
  </section>;
}

/** A read-only dossier over admitted records; no canonicalization or inferred biography. */
function NodeDossier({ detail, entityId, labels, entityOnly = false, partial = false, navigationDisabled = false, onExplore }: {
  detail: NativeGraphEntity; entityId: string; labels: ReadonlyMap<string, string>;
  entityOnly?: boolean; partial?: boolean; navigationDisabled?: boolean; onExplore: (entityId: string) => void;
}) {
  const model = projectNativeObject({kind: "admitted-native", entityId, pin: detail.scope}, detail, labels).dossier;
  const [statblocksOpen, setStatblocksOpen] = useState(false);
  if (!detail.entity.found) return <p>This object is unavailable in the selected revision.</p>;
  return <div className="native-node-dossier">
    <p className="graph-node-explorer__counts"><strong>{model.distinctNeighborCount} connected objects</strong> · {model.relationshipRecordCount} relationship records</p>
    {partial || detail.entity.completeness.status !== "complete" ? <p role="status" className="graph-node-explorer__notice">Partial view. These counts describe admitted records in the loaded revision, not the whole World.</p> : null}
    {model.commonStatus ? <p className="graph-node-explorer__status">Record status: {model.commonStatus}. Not a statement of current truth.</p> : <p className="graph-node-explorer__status">Record qualifications vary. Open evidence for each connection.</p>}
    <section aria-label="Connections">
      <h3>Connections</h3>
      {!model.relationshipRecordCount ? <p>No admitted connections in this view.</p> : null}
      {model.groups.map((group) => {
        const count = new Set(group.rows.map((row) => row.neighborId).filter((id) => id !== entityId)).size;
        return <details className="graph-node-explorer__group" key={group.id}>
        <summary>{group.title} <span className="graph-node-explorer__group-count">{count} {count === 1 ? "node" : "nodes"}</span></summary>
        <ul>{group.rows.map((row) => <li key={row.id}>
          <p className="graph-node-explorer__relationship">{row.text}</p>
          {!model.commonStatus ? <p className="graph-node-explorer__status">{[...new Set(row.assertions.map(assertionStatus))].join("; ")}</p> : null}
          {row.contexts.length ? <p className="graph-node-explorer__context">{row.contexts.join(" · ")}</p> : <p className="graph-node-explorer__context">Source episode not recorded</p>}
          {row.neighborId !== entityId && labels.has(row.neighborId) ? <button type="button" className="graph-node-explorer__link" disabled={navigationDisabled} onClick={() => onExplore(row.neighborId)}>Explore {labels.get(row.neighborId)}</button> : null}
          <Evidence records={row.assertions} detail={detail} entityOnly={entityOnly} commonStatus={model.commonStatus} />
        </li>)}</ul>
      </details>; })}
    </section>
    {model.summaries.length ? <section className="graph-node-explorer__summaries" aria-label="Source summaries">
      <h3>From the source material</h3>
      <p className="graph-node-explorer__context">Recorded summaries, not additional graph connections. Source episodes are not a fictional timeline or a current-state claim.</p>
      {model.summaries.map(({ assertion, text, contexts }) => <article key={assertion.assertion_id}>
        <p className="graph-node-explorer__context">{contexts.length ? contexts.join(" · ") : "Source episode not recorded"}</p>
        {!model.commonStatus ? <p className="graph-node-explorer__status">{assertionStatus(assertion)}</p> : null}
        <details><summary>{text.length > 140 ? `${text.slice(0, 140)}…` : text}</summary><p>{text}</p>
        <Evidence records={[assertion]} detail={detail} entityOnly={entityOnly} commonStatus={model.commonStatus} /></details>
      </article>)}
    </section> : null}
    {model.otherRecords.length ? <details className="graph-node-explorer__secondary"><summary>Other recorded information ({model.otherRecords.length})</summary>
      {model.otherRecords.map(({ assertion, text, contexts }) => <article key={assertion.assertion_id}><p>{text}</p><p className="graph-node-explorer__context">{contexts.join(" · ")}</p><Evidence records={[assertion]} detail={detail} entityOnly={entityOnly} commonStatus={model.commonStatus} /></article>)}
    </details> : null}
    {entityOnly ? <p className="graph-node-explorer__context">Source excerpts and linked statblocks are not available for this connection.</p> : <details className="graph-node-explorer__secondary" onToggle={(event) => setStatblocksOpen(event.currentTarget.open)}><summary>Linked statblocks</summary>{statblocksOpen ? <NativeObjectStatblock pin={detail.scope} entityId={entityId} /> : null}</details>}
    <details className="graph-node-explorer__secondary"><summary>Identity records and revision</summary>
      <p>World revision <code>{detail.scope.revision_id}</code></p><p>Object <code>{entityId}</code></p>
      <p>Names and classifications are preserved as recorded. The compact heading is a display label, not a canonical name.</p>
      {model.identityAssertions.map((assertion) => <Evidence key={assertion.assertion_id} records={[assertion]} detail={detail} entityOnly={entityOnly} commonStatus={null} />)}
      {!detail.entity.assertions.length ? <p>No admitted records for this object in this view.</p> : null}
    </details>
  </div>;
}

function Evidence({ records, detail, entityOnly, commonStatus }: { records: NativeAssertion[]; detail: NativeGraphEntity; entityOnly: boolean; commonStatus: string | null }) {
  const choices = nativeObjectEvidenceChoices(detail, records, entityOnly);
  return <details className="graph-node-explorer__evidence"><summary>Evidence and qualifications{records.length > 1 ? ` · ${records.length} records` : ""}</summary>
    {choices.length ? <><p className="graph-node-explorer__context">{choices.length} supporting {choices.length === 1 ? "source" : "sources"} · {records.length} {records.length === 1 ? "record" : "records"}</p><SourceCitationEvidence identity={JSON.stringify([detail.scope, records.map((a) => a.assertion_id)])} statements={[{ choices }]} /></> : <p className="graph-node-explorer__context">{entityOnly ? "Source excerpts are unavailable for this connection." : "No supporting excerpt is available in this view."}</p>}
    {records.map((assertion) => <section key={assertion.assertion_id} aria-label="Recorded assertion">
      {!commonStatus || assertionStatus(assertion) !== commonStatus ? <p>{assertionStatus(assertion)}</p> : null}
      <p><code>{assertion.predicate}</code></p>
      <details><summary>Exact record</summary><pre>{JSON.stringify(assertion, null, 2)}</pre></details>
    </section>)}
  </details>;
}
