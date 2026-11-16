import { nodeOverviewRelationship } from "./nodeOverviewRelationship";
import { NodeOverview } from "./NodeOverview";
import { useState } from "react";
import type { NativeAssertion, NativeGraphEntity } from "../api/nativeGraphInspection";
import { SourceCitationEvidence } from "../planSurface/components/SourceCitationEvidence";
import { NativeObjectStatblock } from "./NativeObjectStatblock";
import { assertionStatus, type NodeExplorerModel } from "./nodeExplorerModel";
import { nativeObjectEvidenceChoices } from "./nativeObjectEvidence";

/** A read-only dossier over admitted records; no canonicalization or inferred biography. */
export function NodeDossier({ model, detail, entityId, nodeLabel, showStatblocks, labels, entityOnly = false, sourceReads = false, navigationDisabled = false, inlineHost, onInlineOpened, eagerStatblocks = false, onExplore }: {
  model: NodeExplorerModel; detail: NativeGraphEntity; entityId: string; nodeLabel?: string; showStatblocks: boolean; labels: ReadonlyMap<string, string>;
  entityOnly?: boolean; sourceReads?: boolean; partial?: boolean; navigationDisabled?: boolean; eagerStatblocks?: boolean; inlineHost?: HTMLElement; onInlineOpened?: () => void; onExplore?: (entityId: string) => void;
}) {
  const [statblocksOpen, setStatblocksOpen] = useState(false);
  if (!detail.entity.found) return <p>This object is unavailable in the selected revision.</p>;
  const label = nodeLabel ?? labels.get(entityId);
  const summaries = model.summaries
    .map(record => ({ ...record, text: record.text.trim().replace(/^[-*]\s+/, "") }))
    .filter(record => record.text && !record.text.includes("\n"))
    .sort((a, b) => Number(Boolean(label && b.text.startsWith(label))) - Number(Boolean(label && a.text.startsWith(label))))
    .slice(0, 2);
  const related = model.groups
    .flatMap(group => group.rows)
    .flatMap(row => {
      const neighbor = labels.get(row.neighborId);
      if (row.direction === "self" || !neighbor) return [];
      const subject = nodeLabel ?? labels.get(entityId) ?? "This object";
      const text = row.direction === "outgoing"
        ? nodeOverviewRelationship(row.predicate, subject, neighbor)
        : nodeOverviewRelationship(row.predicate, neighbor, subject);
      return text ? [{ text, contexts: row.contexts, records: row.assertions }] : [];
    })
    .slice(0, summaries.length ? 1 : 3);
  const overview = [
    ...summaries.map(({ assertion, text, contexts }) => ({
      text, contexts, records: [assertion],
    })),
    ...related,
  ];
  const excerptsUnavailable = entityOnly && !sourceReads;
  let citationNumber = 0;
  const statements = overview.map(({ text, contexts, records }) => {
    const choices = nativeObjectEvidenceChoices(detail, records, excerptsUnavailable);
    const qualifications = [...new Set(records.map(assertionStatus))];
    const metadata = [...contexts, ...qualifications].join(" · ");
    const sentence = /[.!?]$/.test(text.trim()) ? text.trim() : `${text.trim()}.`;
    const uncertain = records.some(({ metadata }) =>
      metadata.epistemic_basis === "speculative" || metadata.standing === "disputed"
      || metadata.claim_mode === "dungeonbuddy.claim:belief");
    return {
      text: uncertain ? `One uncertain account says “${sentence}”` : sentence,
      choices: (choices.length ? choices : [{
        key: JSON.stringify(records.map(record => record.assertion_id)),
        title: metadata,
        label: "Read exact graph record",
        kind: "section" as const,
        load: async () => ({ title: metadata, content: JSON.stringify(records, null, 2) }),
      }]).map(choice => ({ ...choice, title: `${choice.title} · ${metadata}`, number: ++citationNumber })),
    };
  });
  return <div className="native-node-dossier">
    <NodeOverview>{statements.length ? <SourceCitationEvidence inlineProse
      identity={JSON.stringify([detail.scope, entityId, overview.map(item => item.records.map(record => record.assertion_id))])}
      statements={statements} /> : undefined}</NodeOverview>
    <section aria-label="Connections">
      <h3>Connections</h3>
      {!model.relationshipRecordCount ? <p>No admitted connections in this view.</p> : null}
      {model.groups.map((group) => {
        const count = new Set(group.rows.map((row) => row.neighborId).filter((id) => id !== entityId)).size;
        return <details className="graph-node-explorer__group" key={group.id}>
        <summary>{group.title} <span className="graph-node-explorer__group-count">{count} {count === 1 ? "node" : "nodes"}</span></summary>
        <ul>{group.rows.map((row) => <li key={row.id}>
          <p className="graph-node-explorer__relationship">{row.text}</p>
          <p className="graph-node-explorer__status">{[...new Set(row.assertions.map(assertionStatus))].join("; ")}</p>
          {row.contexts.length ? <p className="graph-node-explorer__context">{row.contexts.join(" · ")}</p> : <p className="graph-node-explorer__context">Source episode not recorded</p>}
          {onExplore && row.neighborId !== entityId && labels.has(row.neighborId) ? <button type="button" className="graph-node-explorer__link" disabled={navigationDisabled} onClick={() => onExplore(row.neighborId)}>Explore {labels.get(row.neighborId)}</button> : null}
          <Evidence records={row.assertions} detail={detail} entityOnly={entityOnly && !sourceReads} commonStatus={model.commonStatus} />
        </li>)}</ul>
      </details>; })}
    </section>
    {model.summaries.length ? <section className="graph-node-explorer__summaries" aria-label="Source summaries">
      <h3>From the source material</h3>
      <p className="graph-node-explorer__context">Recorded summaries, not additional graph connections. Source episodes are not a fictional timeline or a current-state claim.</p>
      {model.summaries.map(({ assertion, text, contexts }) => <article key={assertion.assertion_id}>
        <p className="graph-node-explorer__context">{contexts.length ? contexts.join(" · ") : "Source episode not recorded"}</p>
        <p className="graph-node-explorer__status">{assertionStatus(assertion)}</p>
        <details><summary>{text.length > 140 ? `${text.slice(0, 140)}…` : text}</summary><p>{text}</p>
        <Evidence records={[assertion]} detail={detail} entityOnly={entityOnly && !sourceReads} commonStatus={model.commonStatus} /></details>
      </article>)}
    </section> : null}
    {model.otherRecords.length ? <details className="graph-node-explorer__secondary"><summary>Other recorded information ({model.otherRecords.length})</summary>
      {model.otherRecords.map(({ assertion, text, contexts }) => <article key={assertion.assertion_id}><p>{text}</p><p className="graph-node-explorer__context">{contexts.join(" · ")}</p><Evidence records={[assertion]} detail={detail} entityOnly={entityOnly && !sourceReads} commonStatus={model.commonStatus} /></article>)}
    </details> : null}
    {showStatblocks && <details className="graph-node-explorer__secondary" onToggle={(event) => setStatblocksOpen(event.currentTarget.open)}><summary>Linked statblocks</summary>{statblocksOpen || eagerStatblocks ? <NativeObjectStatblock pin={detail.scope} entityId={entityId} inlineHost={inlineHost} onInlineOpened={onInlineOpened} /> : null}</details>}
    <details className="graph-node-explorer__secondary"><summary>Identity records and revision</summary>
      <p>World revision <code>{detail.scope.revision_id}</code></p><p>Object <code>{entityId}</code></p>
      <p>Names and classifications are preserved as recorded. The compact heading is a display label, not a canonical name.</p>
      {model.identityAssertions.map((assertion) => <article key={assertion.assertion_id}>
        {assertion.value.kind === "literal" && typeof assertion.value.value === "string" &&
          <p>{labels.get(entityId) ?? entityId} · {assertion.predicate.split(":").at(-1)}: {assertion.value.value}</p>}
        <Evidence records={[assertion]} detail={detail} entityOnly={entityOnly && !sourceReads} commonStatus={null} />
      </article>)}
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
