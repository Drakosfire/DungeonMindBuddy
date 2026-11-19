import type { ReactNode } from "react";
import "./BuildSourceWorkspace.css";

export function BuildSourceWorkspace({ children, source, sourceHidden = false }: { children: ReactNode; source: ReactNode; sourceHidden?: boolean }) {
  return (
    <div className="build-source-workspace" data-source-hidden={sourceHidden}>
      <section aria-label="Artifact" className="build-source-workspace__pane" tabIndex={0}>{children}</section>
      <section hidden={sourceHidden} aria-label="Source document" className="build-source-workspace__pane" tabIndex={0}>{source}</section>
    </div>
  );
}
