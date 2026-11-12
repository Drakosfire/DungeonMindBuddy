import { useState } from "react";
import { sameInspectionPin, type NativeAssertion, type NativeGraphEntity } from "../api/nativeGraphInspection";
import { inspectNativeGraph } from "../api/liveApi";
import { SourceCitationEvidence, type CitationChoice } from "../planSurface/components/SourceCitationEvidence";
import { NativeObjectStatblock } from "../graphLens/NativeObjectStatblock";
import { assertionStatus, buildNodeExplorer } from "./graphNodeExplorer";

/** A read-only dossier over admitted records; no canonicalization or inferred biography. */
export function GraphNodeExplorer({ detail, entityId, labels, entityOnly = false, partial = false, navigationDisabled = false, onExplore }: {
  detail: NativeGraphEntity; entityId: string; labels: ReadonlyMap<string, string>;
  entityOnly?: boolean; partial?: boolean; navigationDisabled?: boolean; onExplore: (entityId: string) => void;
}) {
  const model = buildNodeExplorer(detail, entityId, labels);
  const [statblocksOpen, setStatblocksOpen] = useState(false);
  if (!detail.entity.found) return <p>This object is unavailable in the selected revision.</p>;
  return <div className="graph-node-explorer">
    <p className="graph-node-explorer__counts"><strong>{model.distinctNeighborCount} connected objects</strong> · {model.relationshipRecordCount} relationship records</p>
    {partial || detail.entity.completeness.status !== "complete" ? <p role="status" className="graph-node-explorer__notice">Partial view. These counts describe admitted records in the loaded revision, not the whole World.</p> : null}
    {model.commonStatus ? <p className="graph-node-explorer__status">Record status: {model.commonStatus}. Not a statement of current truth.</p> : <p className="graph-node-explorer__status">Record qualifications vary. Open evidence for each connection.</p>}
    <section aria-label="Connections">
      <h3>Connections</h3>
      {!model.relationshipRecordCount ? <p>No admitted connections in this view.</p> : null}
      {model.groups.map((group) => <section className="graph-node-explorer__group" key={group.id} aria-label={group.title}>
        <h4>{group.title}</h4>
        <ul>{group.rows.map((row) => <li key={row.id}>
          <p className="graph-node-explorer__relationship">{row.text}</p>
          {!model.commonStatus ? <p className="graph-node-explorer__status">{[...new Set(row.assertions.map(assertionStatus))].join("; ")}</p> : null}
          {row.contexts.length ? <p className="graph-node-explorer__context">{row.contexts.join(" · ")}</p> : <p className="graph-node-explorer__context">Source episode not recorded</p>}
          {row.neighborId !== entityId && labels.has(row.neighborId) ? <button type="button" className="graph-node-explorer__link" disabled={navigationDisabled} onClick={() => onExplore(row.neighborId)}>Explore {labels.get(row.neighborId)}</button> : null}
          <Evidence records={row.assertions} detail={detail} entityOnly={entityOnly} commonStatus={model.commonStatus} />
        </li>)}</ul>
      </section>)}
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
  const seenEvidence = new Set<string>();
  const choices: CitationChoice[] = entityOnly ? [] : records.flatMap((assertion) => detail.entity.evidence
    .filter((evidence) => evidence.evidence_role === "support" && assertion.metadata.evidence_ref_ids.includes(evidence.evidence_ref_id))
    .filter((evidence) => { if (seenEvidence.has(evidence.evidence_ref_id)) return false; seenEvidence.add(evidence.evidence_ref_id); return true; })
    .map((evidence) => ({ key: evidence.evidence_ref_id, number: 0, title: "Supporting source · exact excerpt", label: "Read supporting source", kind: "passage" as const, load: async () => {
      const packet = await inspectNativeGraph(detail.scope, { kind: "source", assertion_id: assertion.assertion_id, evidence_ref_id: evidence.evidence_ref_id });
      if (packet.schema !== "dmb_native_graph_source_v1" || !sameInspectionPin(packet.scope, detail.scope)) throw new Error("Source unavailable");
      return packet.source.text;
    } })));
  choices.forEach((choice, index) => { choice.number = index + 1; });
  return <details className="graph-node-explorer__evidence"><summary>Evidence and qualifications{records.length > 1 ? ` · ${records.length} records` : ""}</summary>
    {choices.length ? <><p className="graph-node-explorer__context">{choices.length} supporting {choices.length === 1 ? "source" : "sources"} · {records.length} {records.length === 1 ? "record" : "records"}</p><SourceCitationEvidence identity={JSON.stringify([detail.scope, records.map((a) => a.assertion_id)])} statements={[{ choices }]} /></> : <p className="graph-node-explorer__context">{entityOnly ? "Source excerpts are unavailable for this connection." : "No supporting excerpt is available in this view."}</p>}
    {records.map((assertion) => <section key={assertion.assertion_id} aria-label="Recorded assertion">
      {!commonStatus || assertionStatus(assertion) !== commonStatus ? <p>{assertionStatus(assertion)}</p> : null}
      <p><code>{assertion.predicate}</code></p>
      <details><summary>Exact record</summary><pre>{JSON.stringify(assertion, null, 2)}</pre></details>
    </section>)}
  </details>;
}
