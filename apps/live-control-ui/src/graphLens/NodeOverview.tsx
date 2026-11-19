import type { ReactNode } from "react";

export function NodeOverview({ children, replay = false }: { children?: ReactNode; replay?: boolean }) {
  const title = replay ? "What Buddy learned" : "Overview";
  return <section className="graph-node-overview" aria-label={title}>
    <h3>{title}</h3>
    {children ?? <p>There is too little recorded evidence to summarize this object.</p>}
  </section>;
}
