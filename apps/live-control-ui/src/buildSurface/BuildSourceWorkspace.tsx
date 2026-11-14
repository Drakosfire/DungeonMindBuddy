import type { ReactNode } from "react";
import "./BuildSourceWorkspace.css";

export function BuildSourceWorkspace({ children, source }: { children: ReactNode; source: ReactNode }) {
  return (
    <div className="build-source-workspace">
      <section aria-label="Artifact" className="build-source-workspace__pane" tabIndex={0}>{children}</section>
      <section aria-label="Source document" className="build-source-workspace__pane" tabIndex={0}>{source}</section>
    </div>
  );
}
