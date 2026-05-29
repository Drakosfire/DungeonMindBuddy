import type { ProjectionCapability } from "../api/types";

interface CapabilityListProps {
  capabilities: ProjectionCapability[];
}

export function CapabilityList({ capabilities }: CapabilityListProps) {
  if (capabilities.length === 0) {
    return (
      <section className="capability-list" aria-label="Future capabilities">
        <h3 className="artifact-title">Future capabilities</h3>
        <p className="module-muted">No capabilities were returned for this target.</p>
      </section>
    );
  }

  return (
    <section className="capability-list" aria-label="Future capabilities">
      <h3 className="artifact-title">Future capabilities</h3>
      <ul className="capability-items">
        {capabilities.map((capability) => (
          <li
            key={`${capability.command_type}:${capability.lane}`}
            className="capability-item"
            data-enabled={capability.enabled ? "true" : "false"}
          >
            <p className="capability-label">
              <span className="badge muted">disabled</span> {capability.label}
            </p>
            <p className="module-muted">
              command: <code>{capability.command_type}</code> · lane: <code>{capability.lane}</code> · risk:{" "}
              <code>{capability.risk_level}</code>
            </p>
            {capability.disabled_reason ? (
              <p className="module-muted">
                reason: <span>{capability.disabled_reason}</span>
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
