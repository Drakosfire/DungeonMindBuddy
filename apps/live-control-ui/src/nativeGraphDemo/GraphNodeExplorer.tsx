import { NodeDossier } from "../graphLens/NodeDossier";
import { GraphNodeViewer } from "../graphLens/GraphNodeViewer";
import { useRef, useEffect, type Ref } from "react";
import { type NativeGraphEntity } from "../api/nativeGraphInspection";
import { projectNativeObject } from "../graphLens/nativeObjectProjection";
import { compactNodeLabel } from "./graphNodeExplorerModel";

import type { NativeGraphNode, NativeGraphEdge } from "./nativeGraphDemoApi";
import { nativeGraphPresentation } from "./nativeGraphPresentation";

/** Single owner of graph explorer chrome, identity, loading and evidence presentation. */
export function NativeGraphNodeExplorer({ node, revision, detail, labels, entityOnly = false, sourceReads = false, partial = false, navigationDisabled = false, onExplore, onFocus, onClose, onExitFocus, onBack, previousLabel, headingRef, mode = "managed", status = "ready", error, connections = [] }: {
  node: NativeGraphNode; revision: string; detail: NativeGraphEntity | null; labels: ReadonlyMap<string, string>;
  entityOnly?: boolean; sourceReads?: boolean; partial?: boolean; navigationDisabled?: boolean; onExplore: (entityId: string) => void;
  onFocus: () => void; onClose: () => void; onExitFocus?: () => void; onBack?: () => void; previousLabel?: string;
  headingRef?: Ref<HTMLHeadingElement>; mode?: "managed" | "playground"; status?: "idle" | "loading" | "ready" | "unavailable" | "error"; error?: string | null; connections?: readonly NativeGraphEdge[];
}) {
  const presentation = nativeGraphPresentation(node);
  const menuRef = useRef<HTMLDetailsElement>(null);
  const menuTriggerRef = useRef<HTMLElement>(null);
  useEffect(() => { if (menuRef.current) menuRef.current.open = false; }, [node.id, revision]);
  const model = mode === "managed" && status === "ready" && detail?.entity.found
    ? projectNativeObject({ kind: "admitted-native", entityId: node.id, pin: detail.scope }, detail, labels).dossier : null;
  const isPartial = partial || (detail?.entity.completeness.status !== undefined && detail.entity.completeness.status !== "complete");
  return <GraphNodeViewer label={compactNodeLabel(node)}
    kind={presentation.displayKind === "character (role unspecified)" ? "character" : presentation.displayKind}
    partial={isPartial} headingRef={headingRef} controls={
      <nav aria-label="Node explorer controls">
        {onBack ? <button type="button" disabled={navigationDisabled} onClick={onBack} aria-label={`Back to ${previousLabel ?? "previous object"}`} title={`Back to ${previousLabel ?? "previous object"}`}>← Back</button> : null}
        <button type="button" onClick={onFocus} aria-label="Focus" title="Focus this node"><svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="12" r="6"/><path d="M12 2v5m0 10v5M2 12h5m10 0h5"/></svg></button>

        <details ref={menuRef} className="graph-node-explorer__menu" onKeyDown={(event) => {
          if (event.key === "Escape" && menuRef.current?.open) { event.preventDefault(); event.stopPropagation(); menuRef.current.open = false; menuTriggerRef.current?.focus(); }
        }}>
          <summary ref={menuTriggerRef} aria-label="Node information and actions" title="Node information and actions"><span aria-hidden="true">☰</span></summary>
          <div className="graph-node-explorer__menu-content">
            {onExitFocus ? <button type="button" onClick={() => { if (menuRef.current) menuRef.current.open = false; menuTriggerRef.current?.focus(); onExitFocus(); }}>Exit focus</button> : null}
            <p>{presentation.displayKind}</p>
            {presentation.recordedNames.length > 1 ? <details className="graph-node-explorer__names"><summary>Recorded names ({presentation.recordedNames.length})</summary><p>Display label only, not a preferred name or current title.</p><ul>{presentation.recordedNames.map((name) => <li key={name}>{name}</li>)}</ul></details> : null}
            {model ? <>
              <p className="graph-node-explorer__counts"><strong>{model.distinctNeighborCount} connected objects</strong> · {model.relationshipRecordCount} relationship records</p>
              {isPartial ? <p>Partial view. These counts describe admitted records in the loaded revision, not the whole World.</p> : null}
              <p>{model.commonStatus ? `Record status: ${model.commonStatus}. Not a statement of current truth.` : "Record qualifications vary. Open evidence for each connection."}</p>
            </> : null}
            {entityOnly ? <p>{sourceReads ? "Linked statblocks are unavailable for this connection." : "Source excerpts and linked statblocks are not available for this connection."}</p> : null}
            <details><summary>Snapshot revision</summary><code>{revision}</code></details>
          </div>
        </details>
        <button type="button" onClick={onClose} aria-label="Close details" title="Close details"><span aria-hidden="true">×</span></button>
      </nav>}>
    {mode === "managed" ? status === "loading" ? <p role="status">Loading this object from the loaded World revision…</p>
      : status === "ready" && detail && !detail.entity.found ? <p>This object is unavailable in the selected revision.</p>
      : status === "ready" && detail && model ? <NodeDossier nodeLabel={compactNodeLabel(node)} model={model} detail={detail} entityId={node.id} showStatblocks={!entityOnly && presentation.displayKind !== "event"} labels={labels} entityOnly={entityOnly} sourceReads={sourceReads} navigationDisabled={navigationDisabled} onExplore={onExplore} />
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
  </GraphNodeViewer>;
}
