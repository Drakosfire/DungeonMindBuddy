import type { GraphObjectRelationshipViewModel } from "../graphObjectCard";
import type { OfConksMapOverlay, OfConksMapPin } from "./ofConksMapOverlays";
import { mapOverlayPinForNode } from "./ofConksMapOverlays";
import type { OfConksNodeMedia } from "./ofConksNodeMedia";

export type PlayMapOverlaySectionProps = {
  media: OfConksNodeMedia;
  overlay: OfConksMapOverlay;
  /** Current sheet node — highlights matching pin. */
  activeNodeId?: string | null;
  onSelectPin?: (pin: OfConksMapPin) => void;
  disabled?: boolean;
};

function pinAsRelationship(pin: OfConksMapPin): GraphObjectRelationshipViewModel {
  return {
    id: `map-pin:${pin.id}`,
    label: pin.label,
    targetId: pin.nodeId,
    predicate: "located_at",
    direction: "related",
  };
}

/**
 * Prototype Map section: bitmap + percentage coordinate pins that open graph nodes.
 */
export function PlayMapOverlaySection({
  media,
  overlay,
  activeNodeId = null,
  onSelectPin,
  disabled = false,
}: PlayMapOverlaySectionProps) {
  const activePin = activeNodeId ? mapOverlayPinForNode(overlay, activeNodeId) : null;

  return (
    <section
      className="play-object-sheet__section play-map-overlay"
      aria-label="Map"
      data-testid="play-map-overlay"
      data-map-file={overlay.mediaFile}
    >
      <h5>Map</h5>
      <p className="play-map-overlay__subtitle">{overlay.title}</p>
      <div className="play-map-overlay__stage">
        <img
          className="play-map-overlay__image"
          src={media.src}
          alt={media.alt}
          loading="lazy"
        />
        <ul className="play-map-overlay__pins" aria-label="Map pins">
          {overlay.pins.map((pin) => {
            const selected = activePin?.id === pin.id;
            const label =
              pin.areaNumber != null ? `${pin.areaNumber}. ${pin.label}` : pin.label;
            return (
              <li
                key={pin.id}
                className="play-map-overlay__pin-slot"
                style={{ left: `${pin.xPct}%`, top: `${pin.yPct}%` }}
              >
                <button
                  type="button"
                  className={
                    selected
                      ? "play-map-overlay__pin play-map-overlay__pin--active"
                      : "play-map-overlay__pin"
                  }
                  disabled={disabled || !onSelectPin}
                  aria-label={`Open ${label}`}
                  aria-current={selected ? "true" : undefined}
                  title={label}
                  onClick={() => onSelectPin?.(pin)}
                >
                  <span className="play-map-overlay__pin-dot" aria-hidden="true">
                    {pin.areaNumber ?? "•"}
                  </span>
                  <span className="play-map-overlay__pin-label">{pin.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
      {media.caption ? <p className="play-map-overlay__caption">{media.caption}</p> : null}
      <ul className="play-map-overlay__legend" aria-label="Map legend">
        {overlay.pins.map((pin) => (
          <li key={`legend-${pin.id}`}>
            <button
              type="button"
              className={
                activePin?.id === pin.id
                  ? "play-map-overlay__legend-btn play-map-overlay__legend-btn--active"
                  : "play-map-overlay__legend-btn"
              }
              disabled={disabled || !onSelectPin}
              onClick={() => onSelectPin?.(pin)}
            >
              {pin.areaNumber != null ? `${pin.areaNumber}. ` : ""}
              {pin.label}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function openPinAsRelationship(
  pin: OfConksMapPin,
  onSelectRelationship?: (relationship: GraphObjectRelationshipViewModel) => void,
): void {
  onSelectRelationship?.(pinAsRelationship(pin));
}
