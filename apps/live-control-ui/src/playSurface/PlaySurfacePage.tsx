import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";

import { usePublishAgentSurfaceContext } from "../agentInteraction/usePublishAgentSurfaceContext";
import { AppChrome } from "../chrome/AppChrome";
import { appendLensQueryToHref, useOptionalPlanGraphLens } from "../graphLens";
import { BeatsPanel } from "./beats";
import { mountPlayPrepPanel } from "./playPrepHost";
import {
  PLAY_PANEL_IDS,
  PLAY_PANELS,
  buildPlayPanelEmbedSrc,
  isPrepPlayPanel,
  playPanelFromPath,
  playPanelHref,
  type PlayPanelId,
} from "./playPanels";
import { PlayReferenceCapability } from "./reference/PlayReferenceCapability";
import "./playSurface.css";

export interface PlaySurfacePageProps {
  /** Initial panel from the route; thereafter tabs update via history without remounting App. */
  initialPanel?: PlayPanelId;
}

function PlaySurfacePublisher({ panel }: { panel: PlayPanelId }) {
  const def = PLAY_PANELS[panel];
  const lens = useOptionalPlanGraphLens();
  const campaignId = lens?.derived?.campaignId ?? null;

  usePublishAgentSurfaceContext(
    useMemo(
      () => ({
        surfaceId: `play:${panel}`,
        label: `Play · ${def.label}`,
        campaignId,
        documentId: null,
        sessionNumber: lens?.lens.focus?.sessionNumber ?? null,
        ambientSummary: `Play · ${def.label}`,
        sourceEnvelope: null,
      }),
      [campaignId, def.label, lens?.lens.focus?.sessionNumber, panel],
    ),
  );
  return <PlayReferenceCapability panelId={panel} />;
}

function resolvePlayPanel(fallback: PlayPanelId = "beats"): PlayPanelId {
  return playPanelFromPath(window.location.pathname) ?? fallback;
}

/**
 * Play surface: AppChrome + sub-tabs. Beats is a native React panel; other tabs
 * inline prep HTML from `/prep/*`.
 */
export function PlaySurfacePage({ initialPanel = "beats" }: PlaySurfacePageProps) {
  const lens = useOptionalPlanGraphLens();
  const [panel, setPanel] = useState<PlayPanelId>(() => resolvePlayPanel(initialPanel));
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(() => isPrepPlayPanel(resolvePlayPanel(initialPanel)));
  const hostRef = useRef<HTMLDivElement | null>(null);
  const campaignKey = (lens?.lens.selectedCampaignIds ?? []).join(",");
  const prepPanel = isPrepPlayPanel(panel);

  useEffect(() => {
    const syncFromLocation = () => {
      setPanel(resolvePlayPanel(initialPanel));
    };
    window.addEventListener("popstate", syncFromLocation);
    return () => window.removeEventListener("popstate", syncFromLocation);
  }, [initialPanel]);

  const embedSrc = useMemo(
    () =>
      buildPlayPanelEmbedSrc(
        panel,
        typeof window !== "undefined" ? window.location.search : "",
        lens?.lens.selectedCampaignIds ?? null,
      ),
    [campaignKey, lens?.lens.selectedCampaignIds, panel],
  );

  useEffect(() => {
    const host = hostRef.current;
    if (!prepPanel || !host || !embedSrc) {
      setLoading(false);
      setLoadError(null);
      if (host) host.innerHTML = "";
      return;
    }

    let cancelled = false;
    setLoading(true);
    setLoadError(null);

    mountPlayPrepPanel(host, embedSrc, panel)
      .then(() => {
        if (!cancelled) setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoading(false);
        setLoadError(err instanceof Error ? err.message : "Failed to load Play panel.");
      });

    return () => {
      cancelled = true;
      host.innerHTML = "";
    };
  }, [embedSrc, panel, prepPanel]);

  function onSelectPanel(event: MouseEvent<HTMLAnchorElement>, next: PlayPanelId) {
    if (
      event.defaultPrevented
      || event.button !== 0
      || event.metaKey
      || event.ctrlKey
      || event.shiftKey
      || event.altKey
    ) {
      return;
    }
    event.preventDefault();
    const href = appendLensQueryToHref(playPanelHref(next));
    if (`${window.location.pathname}${window.location.search}` !== href) {
      window.history.pushState({}, "", href);
    }
    setPanel(next);
  }

  return (
    <AppChrome activeRoute="play">
      <PlaySurfacePublisher panel={panel} />
      <main className="play-surface" data-testid="play-surface" data-play-panel={panel}>
        <nav className="play-surface__tabs" aria-label="Play tools">
          {PLAY_PANEL_IDS.map((id) => {
            const item = PLAY_PANELS[id];
            const href = appendLensQueryToHref(playPanelHref(id));
            const active = id === panel;
            return (
              <a
                key={id}
                href={href}
                className={active ? "play-surface__tab play-surface__tab--active" : "play-surface__tab"}
                aria-current={active ? "page" : undefined}
                onClick={(event) => onSelectPanel(event, id)}
              >
                {item.label}
              </a>
            );
          })}
        </nav>
        {prepPanel && loading ? <p className="play-surface__status">Loading…</p> : null}
        {prepPanel && loadError ? (
          <p className="play-surface__status play-surface__status--error" role="alert">
            {loadError}
          </p>
        ) : null}
        {panel === "beats" ? (
          <div
            key="play-native"
            className="play-surface__native"
            data-testid="play-surface-native"
          >
            <BeatsPanel />
          </div>
        ) : (
          <div
            key="play-host"
            ref={hostRef}
            className="play-surface__host prep-embed"
            data-testid="play-surface-host"
            data-play-surface-host={panel}
            data-play-embed-src={embedSrc ?? undefined}
            hidden={Boolean(loadError)}
          />
        )}
      </main>
    </AppChrome>
  );
}
