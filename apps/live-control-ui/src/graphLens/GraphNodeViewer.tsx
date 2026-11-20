import { useId, type ReactNode, type Ref } from "react";

import "./GraphNodeViewer.css";

export function GraphNodeViewer({ label, kind, partial, controls, dialog, headingRef, children }: {
  label: string;
  kind?: string;
  partial?: boolean;
  dialog?: boolean;
  controls?: ReactNode;
  headingRef?: Ref<HTMLHeadingElement>;
  children?: ReactNode;
}) {
  const titleId = useId();
  return <section className={dialog ? "graph-node-viewer--dialog native-demo-object-details" : "native-demo-action-card native-demo-object-details"} aria-labelledby={titleId}>
    <header className="graph-node-explorer__navbar">
      <h2 ref={headingRef} tabIndex={-1} id={titleId}>{label}</h2>
      {controls}
    </header>
    {(kind || partial) && <div className="graph-node-explorer__identity">
      {kind && <span className="native-demo-copy">{kind}</span>}
      {partial && <span role="status" className="graph-node-explorer__warning">Partial view</span>}
    </div>}
    {children}
  </section>;
}
