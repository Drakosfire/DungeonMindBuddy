import { useEffect, useState } from "react";

import {
  getStatblockWorkbenchSample,
  postStatblockWorkbenchCommand,
} from "../../api/liveApi";
import type {
  StatblockCombatDefaults,
  StatblockDraftArtifactView,
  StatblockWorkbenchAction,
  StatblockWorkbenchCommandType,
} from "../../api/types";

interface WorkbenchState {
  schema_version: string;
  mode: string;
  artifact: StatblockDraftArtifactView;
  command_status: string;
  diagnostics: string[];
  available_actions: StatblockWorkbenchAction[];
}

type PendingCommand = StatblockWorkbenchCommandType | null;

function pendingLabel(command: PendingCommand): string | null {
  if (command === "statblock.draft.generate") {
    return "Running mock generate command…";
  }
  if (command === "statblock.draft.render") {
    return "Running mock render command…";
  }
  return null;
}

function formatLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function displayValue(value: unknown): string {
  if (value == null || value === "") {
    return "—";
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "—";
  }
  return String(value);
}

function JsonDetails({ title, value }: { title: string; value: unknown }) {
  return (
    <details className="statblock-json-details">
      <summary>{title}</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}

function CombatDefaults({ defaults }: { defaults: StatblockCombatDefaults }) {
  const rows: Array<[string, unknown]> = [
    ["name", defaults.name],
    ["armor_class", defaults.armor_class],
    ["hit_points", defaults.hit_points],
    ["initiative_bonus", defaults.initiative_bonus],
    ["passive_perception", defaults.passive_perception],
    ["speed", defaults.speed_summary ?? defaults.speed],
    ["senses", defaults.senses_summary],
    ["primary_actions", defaults.primary_actions],
    ["suggested_tactics", defaults.suggested_tactics],
    ["legendary_actions", defaults.legendary_actions],
  ];

  return (
    <dl className="statblock-defaults-grid">
      {rows.map(([key, value]) => (
        <div key={key} className="statblock-default-row">
          <dt>{formatLabel(key)}</dt>
          <dd>{displayValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function StatusRail({
  artifact,
  commandStatus,
}: {
  artifact: StatblockDraftArtifactView;
  commandStatus: string;
}) {
  const statuses = [
    ["Command", commandStatus],
    ["Lifecycle", artifact.lifecycle_state],
    ["Review", artifact.review_status],
    ["Storage", artifact.storage_status],
    ["Corpus", artifact.corpus_status],
    ["Created by", artifact.created_by],
  ];

  return (
    <dl className="statblock-status-grid" aria-label="Statblock lifecycle statuses">
      {statuses.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ReadyWorkbench({
  response,
  pendingCommand,
  commandError,
  onRunCommand,
}: {
  response: WorkbenchState;
  pendingCommand: PendingCommand;
  commandError: string | null;
  onRunCommand: (commandType: StatblockWorkbenchCommandType) => void;
}) {
  const artifact = response.artifact;

  return (
    <div className="module-panel statblock-workbench" data-module-id="statblock_workbench">
      <header className="statblock-workbench-header">
        <div>
          <p className="eyebrow">Sample / mock / read-only</p>
          <h2 className="module-title">Statblock Workbench</h2>
          <p className="module-muted">
            Lifecycle preview for <strong>{artifact.title}</strong>; no storage, corpus,
            ingestion, or combat mutation occurs in this PR.
          </p>
        </div>
        <span className="badge">{response.mode}</span>
      </header>

      <section className="statblock-command-row" aria-label="Mock statblock commands">
        <button
          type="button"
          onClick={() => onRunCommand("statblock.draft.generate")}
          disabled={pendingCommand !== null}
        >
          Generate mock draft
        </button>
        <button
          type="button"
          onClick={() => onRunCommand("statblock.draft.render")}
          disabled={pendingCommand !== null}
        >
          Render mock draft
        </button>
        {pendingLabel(pendingCommand) ? (
          <span className="statblock-command-status" role="status">
            {pendingLabel(pendingCommand)}
          </span>
        ) : null}
      </section>
      {commandError ? (
        <p className="statblock-command-error" role="alert">
          Unable to run Workbench command: {commandError}
        </p>
      ) : null}

      <StatusRail artifact={artifact} commandStatus={response.command_status} />

      <section className="statblock-section">
        <h3>Markdown preview</h3>
        <pre className="statblock-markdown-preview">{artifact.markdown}</pre>
      </section>

      <section className="statblock-section">
        <h3>Combat defaults</h3>
        <CombatDefaults defaults={artifact.combat_defaults} />
      </section>

      <section className="statblock-section">
        <h3>Warnings needing DM review</h3>
        {artifact.warnings.length ? (
          <ul className="statblock-warning-list">
            {artifact.warnings.map((warning, index) => (
              <li key={`${warning.code ?? "warning"}-${index}`}>
                <span className="badge warning">{warning.severity ?? "warning"}</span>
                {warning.code ? <code>{warning.code}</code> : null}
                <span>{warning.message}</span>
                {warning.path ? <span className="module-muted">Path: {warning.path}</span> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="module-muted">No warnings returned by the sample artifact.</p>
        )}
      </section>

      <section className="statblock-section">
        <h3>Breadcrumbs</h3>
        <ul className="statblock-breadcrumb-list">
          {artifact.breadcrumbs.map((breadcrumb) => (
            <li key={`${breadcrumb.label}-${breadcrumb.source ?? "source"}`}>
              <span>{breadcrumb.label}</span>
              {breadcrumb.source ? <small>{breadcrumb.source}</small> : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="statblock-section statblock-split-section">
        <JsonDetails title="Provenance" value={artifact.provenance} />
        <JsonDetails title="Source refs" value={artifact.source_refs} />
        <JsonDetails title="Structured statblock" value={artifact.structured_statblock} />
      </section>

      <section className="statblock-section">
        <h3>Future actions</h3>
        <div className="statblock-action-row">
          {response.available_actions.map((action) => {
            const disabledReason =
              action.disabled_reason ??
              "Disabled in read-only sample mode; future PRs will add handlers.";
            return (
              <div key={action.action_id} className="statblock-action-card">
                <button type="button" disabled aria-disabled="true">
                  {action.label}
                </button>
                <small>{disabledReason}</small>
              </div>
            );
          })}
        </div>
      </section>

      {response.diagnostics.length ? (
        <section className="statblock-section">
          <h3>Diagnostics</h3>
          <ul className="module-list">
            {response.diagnostics.map((diagnostic) => (
              <li key={diagnostic}>{diagnostic}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

export function StatblockWorkbenchModule() {
  const [response, setResponse] = useState<WorkbenchState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingCommand, setPendingCommand] = useState<PendingCommand>(null);
  const [commandError, setCommandError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getStatblockWorkbenchSample()
      .then((sample) => {
        if (active) {
          setResponse(sample);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const runCommand = (commandType: StatblockWorkbenchCommandType) => {
    setPendingCommand(commandType);
    setCommandError(null);
    postStatblockWorkbenchCommand({
      command_type: commandType,
      requested_by: "human",
      breadcrumbs: [
        {
          label: "surface:statblock_workbench",
          source: "live_control_ui",
          metadata: {
            trigger:
              commandType === "statblock.draft.generate"
                ? "generate_mock_draft"
                : "render_mock_statblock",
          },
        },
      ],
      as_artifact: true,
    })
      .then((commandResponse) => {
        if (commandResponse.artifact) {
          setResponse({
            schema_version: commandResponse.schema_version,
            mode: commandResponse.mode,
            artifact: commandResponse.artifact,
            command_status: commandResponse.command_status,
            diagnostics: commandResponse.diagnostics,
            available_actions: commandResponse.available_actions,
          });
        } else {
          setCommandError("Command completed without a draft artifact.");
        }
      })
      .catch((err: unknown) => {
        setCommandError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        setPendingCommand(null);
      });
  };

  if (loading) {
    return (
      <div className="module-panel statblock-workbench" data-module-id="statblock_workbench">
        <h2 className="module-title">Statblock Workbench</h2>
        <p className="module-muted">Loading read-only sample artifact…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="module-panel statblock-workbench" data-module-id="statblock_workbench">
        <h2 className="module-title">Statblock Workbench</h2>
        <p className="module-error">Unable to load sample statblock artifact: {error}</p>
      </div>
    );
  }

  if (!response) {
    return (
      <div className="module-panel statblock-workbench" data-module-id="statblock_workbench">
        <h2 className="module-title">Statblock Workbench</h2>
        <p className="module-muted">No sample artifact returned.</p>
      </div>
    );
  }

  return (
    <ReadyWorkbench
      response={response}
      pendingCommand={pendingCommand}
      commandError={commandError}
      onRunCommand={runCommand}
    />
  );
}
