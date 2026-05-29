import type {
  ProjectionCapability,
  ProjectionCommand,
  ProjectionTarget,
  ProjectionWriteResult,
} from "../api/types";
import { AppendObservationAction } from "./AppendObservationAction";

interface CapabilityListProps {
  target: ProjectionTarget;
  capabilities: ProjectionCapability[];
  onSubmitCommand?: (command: ProjectionCommand) => Promise<ProjectionWriteResult>;
  onCommandAccepted?: (result: ProjectionWriteResult) => Promise<void> | void;
}

function isAppendObservationCapability(capability: ProjectionCapability): boolean {
  return (
    capability.enabled &&
    capability.command_type === "append_observation" &&
    capability.lane === "observed_play"
  );
}

export function CapabilityList({
  target,
  capabilities,
  onSubmitCommand,
  onCommandAccepted,
}: CapabilityListProps) {
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
              <span className={`badge ${capability.enabled ? "locked" : "muted"}`}>
                {capability.enabled ? "enabled" : "disabled"}
              </span>{" "}
              {capability.label}
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
            {isAppendObservationCapability(capability) && onSubmitCommand ? (
              <AppendObservationAction
                target={target}
                capability={capability}
                onSubmitCommand={onSubmitCommand}
                onAccepted={onCommandAccepted}
              />
            ) : null}
            {capability.enabled && !isAppendObservationCapability(capability) ? (
              <p className="module-muted">Action not supported in this pane version.</p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
