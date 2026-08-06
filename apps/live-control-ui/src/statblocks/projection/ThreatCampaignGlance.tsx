import { buildStatblockViewModel } from "../render/statblockViewModel";
import type { ThreatSheetBindingViewModel, ThreatSheetLoadStatus } from "./threatSheetViewModel";

export function humanizeThreatLabel(value: string | null | undefined, fallback: string): string {
  const raw = String(value ?? "").trim();
  if (!raw) return fallback;
  return raw
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

export function mechanicsGlanceCue(availableCount: number, bindingCount: number): string {
  if (availableCount === 1) return "Exact mechanics ready";
  if (availableCount > 1) {
    return `${availableCount} exact bindings — expand to review each`;
  }
  if (bindingCount === 0) return "No mechanics binding yet";
  return "Mechanics binding unavailable";
}

/** Prefer graph summary, then exact revision flavor description, then flavor summary. */
export function resolveThreatGlanceDescription(
  graphSummary: string | null | undefined,
  binding: ThreatSheetBindingViewModel | null | undefined,
): string | null {
  const fromGraph = String(graphSummary ?? "").trim();
  if (fromGraph) return fromGraph;
  const flavor = binding?.revision?.definition?.flavor_text;
  const fromDescription = String(flavor?.description ?? "").trim();
  if (fromDescription) return fromDescription;
  const fromFlavorSummary = String(flavor?.summary ?? "").trim();
  if (fromFlavorSummary) return fromFlavorSummary;
  return null;
}

export function resolveThreatGlanceMeta(
  threatKind: string | null | undefined,
  intendedRole: string | null | undefined,
  binding: ThreatSheetBindingViewModel | null | undefined,
): string | null {
  if (binding?.revision) {
    const identityLine = buildStatblockViewModel(binding.revision, "summary").identityLine?.trim();
    if (identityLine) return identityLine;
  }

  const kind = humanizeThreatLabel(threatKind, "");
  const role = intendedRole ? humanizeThreatLabel(intendedRole, "") : "";
  const parts: string[] = [];
  if (kind && kind.toLowerCase() !== "threat") parts.push(kind);
  if (role && role.toLowerCase() !== "threat" && role.toLowerCase() !== kind.toLowerCase()) {
    parts.push(role);
  }
  return parts.length ? parts.join(" · ") : null;
}

export function CompactCoreStats({ binding }: { binding: ThreatSheetBindingViewModel }) {
  if (!binding.revision) return null;
  const view = buildStatblockViewModel(binding.revision, "summary");
  return (
    <dl className="threat-sheet-projection__core-stats" aria-label="Compact mechanics summary">
      <div>
        <dt>AC</dt>
        <dd>{view.armorClassSummary}</dd>
      </div>
      <div>
        <dt>HP</dt>
        <dd>{view.hitPointsSummary}</dd>
      </div>
      <div>
        <dt>Speed</dt>
        <dd>{view.speedSummary}</dd>
      </div>
      <div>
        <dt>CR</dt>
        <dd>{view.challengeSummary}</dd>
      </div>
    </dl>
  );
}

export interface ThreatCampaignGlanceProps {
  label: string;
  threatKind?: string | null;
  intendedRole?: string | null;
  summary?: string | null;
  loadStatus?: ThreatSheetLoadStatus | "idle";
  compactBinding?: ThreatSheetBindingViewModel | null;
  availableCount?: number;
  bindingCount?: number;
  /** hover = CSS tooltip; sheet = Plan projection glance body */
  variant?: "hover" | "sheet";
}

/**
 * Campaign-facing Threat glance shared by chip hover and Plan projection glance.
 * Mechanical values appear only when an exact trusted binding is supplied.
 */
export function ThreatCampaignGlance({
  label,
  threatKind = null,
  intendedRole = null,
  summary = null,
  loadStatus = "idle",
  compactBinding = null,
  availableCount = 0,
  bindingCount = 0,
  variant = "sheet",
}: ThreatCampaignGlanceProps) {
  const meta = resolveThreatGlanceMeta(threatKind, intendedRole, compactBinding);
  const description = resolveThreatGlanceDescription(summary, compactBinding);
  const showReadyCue = loadStatus === "ready" && !compactBinding;

  return (
    <div
      className={`threat-campaign-glance threat-campaign-glance--${variant}`}
      data-testid="threat-campaign-glance"
      data-variant={variant}
    >
      <header className="threat-sheet-projection__header">
        <h3 className="threat-sheet-projection__title">{label}</h3>
        {meta ? <p className="threat-sheet-projection__meta">{meta}</p> : null}
        {description ? (
          <p className="threat-sheet-projection__summary">{description}</p>
        ) : loadStatus === "loading" || loadStatus === "idle" ? null : (
          <p className="threat-sheet-projection__summary threat-sheet-projection__summary--empty">
            No description available yet.
          </p>
        )}
      </header>

      {loadStatus === "loading" ? (
        <p className="threat-sheet-projection__status threat-sheet-projection__status--loading" role="status">
          Loading exact mechanics…
        </p>
      ) : null}

      {compactBinding ? <CompactCoreStats binding={compactBinding} /> : null}

      {showReadyCue ? (
        <p className="threat-sheet-projection__mechanics-cue" role="status">
          {mechanicsGlanceCue(availableCount, bindingCount)}
        </p>
      ) : null}

      {variant === "hover" && loadStatus === "idle" && !compactBinding ? (
        <p className="threat-sheet-projection__mechanics-cue">Click to open exact mechanics</p>
      ) : null}
    </div>
  );
}
