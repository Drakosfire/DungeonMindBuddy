import { useProjection } from "../projection/projectionContext";
import type { SurfaceConfig } from "../types";

interface PlanToolBarProps {
  config: SurfaceConfig;
}

export function PlanToolBar({ config }: PlanToolBarProps) {
  const { active, openTool } = useProjection();

  return (
    <section className="plan-toolbox-card" aria-label="Plan toolbox">
      <div className="plan-toolbox-copy">
        <p className="plan-surface-kicker">Toolbox</p>
        <h2>Planning tools</h2>
        <p>Open focused workflows beside the canvas. Tools stay out of the document until you choose them.</p>
      </div>
      <nav className="plan-tool-bar" aria-label="Plan tools">
        {config.tools.map((tool) => (
          <button
            key={tool.id}
            type="button"
            className={active?.kind === "tool" && active.key === tool.id ? "active" : undefined}
            aria-pressed={active?.kind === "tool" && active.key === tool.id}
            onClick={() => openTool(tool.id)}
          >
            <span>{tool.label}</span>
            <small>
              {tool.id === "ingest-recap"
                ? "Recap workflow"
                : tool.id === "recap"
                  ? "Graph-linked reader"
                : tool.id === "graph-preview"
                  ? "Graph evidence"
                  : "Workbench"}
            </small>
          </button>
        ))}
      </nav>
    </section>
  );
}
