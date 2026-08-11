import { useMemo, useState } from "react";

import { GraphLoadPanel } from "../graphLens/GraphLoadPanel";
import type { PlanGraphLensFocus, ReviewCampaignId } from "../graphLens/sessionCampaignContext";
import { useOptionalPlanGraphLens } from "../graphLens/WorldGraphLensContext";
import { useOptionalWorldGraphLensProjection } from "../graphLens/useWorldGraphLensProjection";
import {
  SurfaceContextPopover,
} from "../surfaceInteraction/contextHost";

export type WorldGraphChromeTone =
  | "ready"
  | "loading"
  | "warning"
  | "error"
  | "unavailable"
  | "not_loaded";

export interface WorldGraphChromePresentation {
  tone: WorldGraphChromeTone;
  /** Compact resting label, e.g. `C1+C2 · C2 · S25 · Ready`. */
  compactLabel: string;
  /** Slightly longer label when space allows. */
  fullLabel: string;
}

function shortCampaignIdToken(campaignId: string): string {
  const match = campaignId.match(/^longmont-c(\d+)$/i);
  if (match) return `C${match[1]}`;
  return campaignId.trim() || "World";
}

/**
 * Scope string from structured lens state — never reparse summaryLabel.
 * Examples: `C2`, `C2 · S25`, `C1+C2`, `C1+C2 · C2 · S25`.
 */
export function formatWorldGraphChromeScope(input: {
  selectedCampaignIds: readonly ReviewCampaignId[] | null | undefined;
  focus: PlanGraphLensFocus | null | undefined;
}): string {
  const selected = input.selectedCampaignIds ?? [];
  if (selected.length === 0) {
    return "World";
  }
  const campaignScope = selected.map(shortCampaignIdToken).join("+");
  const focus = input.focus;
  if (!focus) {
    return campaignScope;
  }
  const focusCampaign = shortCampaignIdToken(focus.campaignId);
  const session = `S${focus.sessionNumber}`;
  // Single-campaign focus on that same campaign: avoid repeating C2 · C2 · S25.
  if (selected.length === 1 && selected[0] === focus.campaignId) {
    return `${campaignScope} · ${session}`;
  }
  return `${campaignScope} · ${focusCampaign} · ${session}`;
}

/**
 * Pure presentation helper — keeps chrome wording out of GraphLoadPanel.
 * Lens selection/focus remain authoritative; do not reparse summaryLabel.
 */
export function presentWorldGraphChromeStatus(input: {
  hasProjectionContext: boolean;
  hasLensControls: boolean;
  projectionState: "loading" | "ready" | "error" | "unavailable" | null;
  projectionError: string | null;
  focusValidationStatus: string | null;
  selectedCampaignIds: readonly ReviewCampaignId[] | null;
  focus: PlanGraphLensFocus | null;
}): WorldGraphChromePresentation {
  if (!input.hasProjectionContext) {
    return {
      tone: "not_loaded",
      compactLabel: "World · Not loaded",
      fullLabel: "World · Not loaded",
    };
  }
  if (!input.hasLensControls) {
    return {
      tone: "unavailable",
      compactLabel: "World · Unavailable",
      fullLabel: "World · Unavailable",
    };
  }

  const scope = formatWorldGraphChromeScope({
    selectedCampaignIds: input.selectedCampaignIds,
    focus: input.focus,
  });

  if (input.projectionState === "loading" || input.focusValidationStatus === "pending") {
    return {
      tone: "loading",
      compactLabel: `${scope} · Loading…`,
      fullLabel: `World · ${scope} · Loading…`,
    };
  }
  if (input.projectionState === "error") {
    return {
      tone: "error",
      compactLabel: "World · Needs attention",
      fullLabel: input.projectionError?.trim()
        ? `World · Needs attention · ${input.projectionError.trim()}`
        : "World · Needs attention",
    };
  }
  if (
    input.projectionState === "unavailable"
    || input.focusValidationStatus === "unavailable"
  ) {
    return {
      tone: input.focusValidationStatus === "unavailable" ? "warning" : "unavailable",
      compactLabel:
        input.focusValidationStatus === "unavailable"
          ? "World · Needs attention"
          : "World · Unavailable",
      fullLabel:
        input.focusValidationStatus === "unavailable"
          ? "World · Needs attention"
          : "World · Unavailable",
    };
  }

  return {
    tone: "ready",
    compactLabel: `${scope} · Ready`,
    fullLabel: `World · ${scope} · Ready`,
  };
}

function WorldGraphConstellation({ tone }: { tone: WorldGraphChromeTone }) {
  const pulsing = tone === "loading";
  return (
    <svg
      className={`app-world-graph-status__glyph${pulsing ? " app-world-graph-status__glyph--pulse" : ""}`}
      viewBox="0 0 16 14"
      width="14"
      height="12"
      aria-hidden="true"
      focusable="false"
    >
      <line className="app-world-graph-status__edge" x1="8" y1="3" x2="3" y2="11" />
      <line className="app-world-graph-status__edge" x1="8" y1="3" x2="13" y2="11" />
      <line className="app-world-graph-status__edge" x1="3" y1="11" x2="13" y2="11" />
      <circle className="app-world-graph-status__node app-world-graph-status__node--a" cx="8" cy="3" r="2" />
      <circle className="app-world-graph-status__node app-world-graph-status__node--b" cx="3" cy="11" r="2" />
      <circle className="app-world-graph-status__node app-world-graph-status__node--c" cx="13" cy="11" r="2" />
    </svg>
  );
}

/**
 * Application-chrome World Graph status. Observes lens/projection; does not load.
 */
export function AppChromeWorldGraphStatus() {
  const [open, setOpen] = useState(false);
  const projection = useOptionalWorldGraphLensProjection();
  const lens = useOptionalPlanGraphLens();

  const presentation = useMemo(
    () =>
      presentWorldGraphChromeStatus({
        hasProjectionContext: projection != null,
        hasLensControls: lens != null,
        projectionState: projection?.projectionState ?? null,
        projectionError: projection?.projectionError ?? null,
        focusValidationStatus: lens?.focusValidationStatus ?? null,
        selectedCampaignIds: lens?.lens.selectedCampaignIds ?? null,
        focus: lens?.lens.focus ?? null,
      }),
    [lens, projection],
  );

  const trigger = (
    <button
      type="button"
      className={`app-world-graph-status__trigger app-world-graph-status__trigger--${presentation.tone}`}
      data-testid="app-chrome-world-graph-status"
      aria-expanded={open}
      aria-haspopup="dialog"
      title={presentation.fullLabel}
      onClick={() => setOpen((current) => !current)}
    >
      <WorldGraphConstellation tone={presentation.tone} />
      <span className="app-world-graph-status__label app-world-graph-status__label--full">
        {presentation.fullLabel}
      </span>
      <span className="app-world-graph-status__label app-world-graph-status__label--compact">
        {presentation.compactLabel}
      </span>
    </button>
  );

  return (
    <div className="app-world-graph-status" data-testid="app-chrome-world-graph">
      <SurfaceContextPopover
        open={open}
        onOpenChange={setOpen}
        trigger={trigger}
        title="World Graph"
        align="end"
      >
        {projection && lens ? (
          <>
            <p className="app-world-graph-status__detail" data-testid="app-world-graph-node-count">
              {presentation.tone === "ready"
                ? `${projection.nodeCount.toLocaleString()} node${projection.nodeCount === 1 ? "" : "s"}`
                : presentation.fullLabel}
            </p>
            <GraphLoadPanel
              projectionState={projection.projectionState}
              projectionError={projection.projectionError}
              nodeCount={projection.nodeCount}
            />
          </>
        ) : (
          <p className="app-world-graph-status__detail" role="status">
            {presentation.fullLabel}
          </p>
        )}
      </SurfaceContextPopover>
    </div>
  );
}
