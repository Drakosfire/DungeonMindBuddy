import type { SurfaceConfig } from "../types";

interface PlanNavBarProps {
  config: SurfaceConfig;
}

export function PlanNavBar({ config }: PlanNavBarProps) {
  return (
    <header className="plan-nav-bar">
      <div>
        <p className="plan-surface-kicker">{config.label}</p>
        <h1 className="plan-nav-title">{config.context.headerLabel}</h1>
        <p className="plan-nav-subtitle">
          Intentional planning surface. Use Live Play as the static command-board baseline.
        </p>
      </div>
      <nav className="plan-nav-links" aria-label="Plan surface navigation">
        <a href="/plan" aria-current="page">
          Plan
        </a>
        <a href="/evals/c2_live_prep/mireward-prep/live-play.html">Live Play</a>
        <a href="/surface">Live Control</a>
        <a href="/tiptap-callout-spike?doc=north-gate-session-runbook">Edit Runbook</a>
        <a href="/">Index</a>
      </nav>
    </header>
  );
}
