import { useEffect, useState } from "react";

import { getArtifact, getCapabilities, postCommand } from "../api/liveApi";
import type {
  ArtifactReadResponse,
  CapabilityReadResponse,
  ProjectionCommand,
  ProjectionTargetType,
  ProjectionWriteResult,
} from "../api/types";
import { EventArtifactRenderer, RollTableArtifactRenderer } from "./ArtifactRenderers";
import { CapabilityList } from "./CapabilityList";
import { formatTargetType, type PaneTarget } from "./targetTypes";

export type InspectorPaneState =
  | { status: "closed" }
  | { status: "open"; target: PaneTarget | null };

interface InspectorPaneProps {
  state: InspectorPaneState;
  onClose: () => void;
  onCommandAccepted?: (result: ProjectionWriteResult) => Promise<void> | void;
}

type InspectorReadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; artifact: ArtifactReadResponse; capabilities: CapabilityReadResponse }
  | { status: "error"; message: string }
  | { status: "unsupported"; message: string };

function isReadableTargetType(
  targetType: ProjectionTargetType,
): targetType is "event" | "roll_table" {
  return targetType === "event" || targetType === "roll_table";
}

export function InspectorPane({ state, onClose, onCommandAccepted }: InspectorPaneProps) {
  const [readState, setReadState] = useState<InspectorReadState>({ status: "idle" });

  useEffect(() => {
    if (state.status === "closed" || state.target == null) {
      setReadState({ status: "idle" });
      return;
    }
    const target = state.target;

    if (!isReadableTargetType(target.target_type)) {
      setReadState({
        status: "unsupported",
        message: "Read renderer not implemented for this target type yet.",
      });
      return;
    }

    let cancelled = false;
    async function loadSelectedTarget() {
      setReadState({ status: "loading" });
      try {
        const [artifact, capabilities] = await Promise.all([
          getArtifact({
            target_type: target.target_type,
            target_id: target.target_id,
          }),
          getCapabilities({
            target_type: target.target_type,
            target_id: target.target_id,
          }),
        ]);
        if (!cancelled) {
          setReadState({ status: "ready", artifact, capabilities });
        }
      } catch (error: unknown) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Failed to load artifact.";
          setReadState({ status: "error", message });
        }
      }
    }
    void loadSelectedTarget();

    return () => {
      cancelled = true;
    };
  }, [state]);

  async function handleSubmitCommand(command: ProjectionCommand): Promise<ProjectionWriteResult> {
    return postCommand(command);
  }

  async function handleCommandAccepted(result: ProjectionWriteResult): Promise<void> {
    if (state.status !== "open" || state.target == null || !isReadableTargetType(state.target.target_type)) {
      return;
    }
    const [artifact, capabilities] = await Promise.all([
      getArtifact({
        target_type: state.target.target_type,
        target_id: state.target.target_id,
      }),
      getCapabilities({
        target_type: state.target.target_type,
        target_id: state.target.target_id,
      }),
    ]);
    setReadState({ status: "ready", artifact, capabilities });
    await onCommandAccepted?.(result);
  }

  if (state.status === "closed") {
    return null;
  }

  return (
    <aside className="inspector-pane" aria-label="Inspector pane">
      <header className="inspector-pane-header">
        <h2>Inspector</h2>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </header>
      {state.target == null ? (
        <p className="module-muted">Select a timeline ref or record event to inspect.</p>
      ) : (
        <div className="inspector-pane-target">
          <p className="inspector-pane-title">
            {formatTargetType(state.target.target_type)} · {state.target.label}
          </p>
          <ul className="inspector-pane-metadata">
            <li>
              <span className="inspector-key">source:</span> {state.target.source_status}
            </li>
            {state.target.role ? (
              <li>
                <span className="inspector-key">role:</span> {state.target.role}
              </li>
            ) : null}
            <li>
              <span className="inspector-key">id:</span> {state.target.target_id}
            </li>
            {state.target.origin ? (
              <li>
                <span className="inspector-key">origin:</span> {state.target.origin.module_id}
                {state.target.origin.row_id ? ` / ${state.target.origin.row_id}` : ""}
              </li>
            ) : null}
          </ul>
          {readState.status === "loading" ? (
            <p className="module-muted">Loading artifact…</p>
          ) : null}
          {readState.status === "unsupported" ? (
            <p className="module-muted">{readState.message}</p>
          ) : null}
          {readState.status === "error" ? <p className="module-error">{readState.message}</p> : null}
          {readState.status === "ready" ? (
            <>
              {readState.artifact.artifact_kind === "event" ? (
                <EventArtifactRenderer
                  artifact={readState.artifact as ArtifactReadResponse & { artifact_kind: "event" }}
                />
              ) : readState.artifact.artifact_kind === "roll_table" ? (
                <RollTableArtifactRenderer
                  artifact={readState.artifact as ArtifactReadResponse & { artifact_kind: "roll_table" }}
                />
              ) : (
                <p className="module-muted">No read renderer is available for this target type yet.</p>
              )}
              <CapabilityList
                target={readState.artifact.target}
                capabilities={readState.capabilities.capabilities}
                onSubmitCommand={handleSubmitCommand}
                onCommandAccepted={handleCommandAccepted}
              />
              <p className="module-muted">
                provenance: {readState.artifact.provenance.source_role ?? "unknown"}
                {readState.artifact.provenance.source_path
                  ? ` / ${readState.artifact.provenance.source_path}`
                  : ""}
              </p>
              {readState.artifact.file_state_token ? (
                <p className="module-muted">
                  state token: <code>{readState.artifact.file_state_token}</code>
                </p>
              ) : null}
            </>
          ) : null}
        </div>
      )}
    </aside>
  );
}
