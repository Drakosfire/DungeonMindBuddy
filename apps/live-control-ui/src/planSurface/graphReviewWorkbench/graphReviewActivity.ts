export type GraphReviewActivityPhase =
  | "catalog"
  | "warming"
  | "warm"
  | "loading-session";

export interface GraphReviewActivity {
  phase: GraphReviewActivityPhase;
  message: string;
  busy: boolean;
}

export type WarmupStatus = "idle" | "warming" | "ready" | "error";

function sessionNumberLabel(sessionId: string | null | undefined): string | null {
  if (!sessionId) return null;
  const match = sessionId.match(/^(?:session-)?(\d+)$/i);
  if (!match) return sessionId;
  return `Session ${match[1]}`;
}

export function formatGraphReviewActivityTarget(
  campaignLabel: string | null | undefined,
  sessionId: string | null | undefined,
): string {
  const session = sessionNumberLabel(sessionId);
  const campaign = campaignLabel?.trim() || null;
  if (campaign && session) return `${campaign} · ${session}`;
  if (session) return session;
  if (campaign) return campaign;
  return "draft";
}

/**
 * Pick the single highest-priority activity signal for the workbench chrome.
 * Busy phases outrank warm-ready; applied-session projection load outranks background warm-up.
 */
export function resolveGraphReviewActivity(options: {
  sessionsLoaded: boolean;
  hasAppliedLoad: boolean;
  warmupStatus: WarmupStatus;
  warmupTargetLabel: string | null;
  projectionStatus?: "idle" | "loading" | "ready" | "error" | "unavailable" | null;
  appliedTargetLabel?: string | null;
}): GraphReviewActivity | null {
  if (!options.sessionsLoaded) {
    return {
      phase: "catalog",
      message: "Loading sessions…",
      busy: true,
    };
  }

  if (options.hasAppliedLoad && options.projectionStatus === "loading") {
    const target = options.appliedTargetLabel?.trim() || "session";
    return {
      phase: "loading-session",
      message: `Loading ${target}…`,
      busy: true,
    };
  }

  if (!options.hasAppliedLoad && options.warmupStatus === "warming") {
    const target = options.warmupTargetLabel?.trim() || "draft";
    return {
      phase: "warming",
      message: `Warming ${target}…`,
      busy: true,
    };
  }

  if (!options.hasAppliedLoad && options.warmupStatus === "ready") {
    const target = options.warmupTargetLabel?.trim() || "draft";
    return {
      phase: "warm",
      message: `${target} ready`,
      busy: false,
    };
  }

  return null;
}
