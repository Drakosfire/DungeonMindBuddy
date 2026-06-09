import { useCallback, useEffect, useState } from "react";

import {
  getStatblockWorkbenchDraft,
  getStatblockWorkbenchSample,
  listStatblockWorkbenchDrafts,
  postStatblockWorkbenchCommand,
  storeStatblockWorkbenchDraft,
} from "../../api/liveApi";
import type {
  ListStatblockDraftsResponse,
  StatblockCombatDefaults,
  StatblockDraftArtifactView,
  StatblockWorkbenchAction,
  StatblockWorkbenchCommandType,
  StoredStatblockDraftSummary,
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
  if (command === "statblock.draft.generate") return "Running mock generate command…";
  if (command === "statblock.draft.render") return "Running mock render command…";
  return null;
}

function formatLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function displayValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
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

function StatusRail({ artifact, commandStatus }: { artifact: StatblockDraftArtifactView; commandStatus: string }) {
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

function StoredDraftsList({
  drafts,
  loading,
  error,
  pendingLoadId,
  onLoadDraft,
}: {
  drafts: StoredStatblockDraftSummary[];
  loading: boolean;
  error: string | null;
  pendingLoadId: string | null;
  onLoadDraft: (artifactId: string) => void;
}) {
  return (
    <section className="statblock-section">
      <h3>Stored drafts</h3>
      {loading ? <p className="module-muted">Loading stored drafts…</p> : null}
      {error ? <p className="statblock-command-error" role="alert">Unable to load stored drafts: {error}</p> : null}
      {!loading && drafts.length === 0 ? <p className="module-muted">No stored statblock drafts yet.</p> : null}
      {drafts.length ? (
        <div className="statblock-stored-draft-list">
          {drafts.map((draft) => (
            <article key={draft.artifact_id} className="statblock-stored-draft-card">
              <div>
                <h4>{draft.title}</h4>
                <p className="module-muted">
                  Review: {draft.review_status} · Storage: {draft.storage_status} · Corpus: {draft.corpus_status}
                </p>
                <p className="module-muted">Updated {draft.updated_at}; stored {draft.stored_at}</p>
                <code>{draft.storage_path}</code>
              </div>
              <button
                type="button"
                onClick={() => onLoadDraft(draft.artifact_id)}
                disabled={pendingLoadId !== null}
              >
                {pendingLoadId === draft.artifact_id ? "Loading…" : "Load"}
              </button>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ReadyWorkbench({
  response,
  pendingCommand,
  commandError,
  storeError,
  storeMessage,
  storedDrafts,
  storedDraftsLoading,
  storedDraftsError,
  pendingStore,
  pendingLoadId,
  onRunCommand,
  onStoreDraft,
  onLoadDraft,
}: {
  response: WorkbenchState;
  pendingCommand: PendingCommand;
  commandError: string | null;
  storeError: string | null;
  storeMessage: string | null;
  storedDrafts: StoredStatblockDraftSummary[];
  storedDraftsLoading: boolean;
  storedDraftsError: string | null;
  pendingStore: boolean;
  pendingLoadId: string | null;
  onRunCommand: (commandType: StatblockWorkbenchCommandType) => void;
  onStoreDraft: () => void;
  onLoadDraft: (artifactId: string) => void;
}) {
  const artifact = response.artifact;
  const futureActions = response.available_actions.filter((action) => action.action_id !== "store_draft");
  const storeDisabled = pendingCommand !== null || pendingStore || artifact.storage_status === "stored_draft";

  return (
    <div className="module-panel statblock-workbench" data-module-id="statblock_workbench">
      <header className="statblock-workbench-header">
        <div>
          <p className="eyebrow">Mock / non-corpus draft lane</p>
          <h2 className="module-title">Statblock Workbench</h2>
          <p className="module-muted">
            Lifecycle preview for <strong>{artifact.title}</strong>; drafts may be stored under the live session, but corpus, ingestion, and combat mutation remain disabled.
          </p>
        </div>
        <span className="badge">{response.mode}</span>
      </header>

      <section className="statblock-command-row" aria-label="Mock statblock commands">
        <button type="button" onClick={() => onRunCommand("statblock.draft.generate")} disabled={pendingCommand !== null || pendingStore}>
          Generate mock draft
        </button>
        <button type="button" onClick={() => onRunCommand("statblock.draft.render")} disabled={pendingCommand !== null || pendingStore}>
          Render mock draft
        </button>
        {pendingLabel(pendingCommand) ? <span className="statblock-command-status" role="status">{pendingLabel(pendingCommand)}</span> : null}
      </section>
      {commandError ? <p className="statblock-command-error" role="alert">Unable to run Workbench command: {commandError}</p> : null}

      <section className="statblock-section statblock-storage-section">
        <h3>Draft storage</h3>
        <button type="button" onClick={onStoreDraft} disabled={storeDisabled}>
          {pendingStore ? "Storing draft…" : "Store draft"}
        </button>
        <p className="module-muted">Stores the current artifact as a file-backed non-corpus draft only.</p>
        {artifact.storage_status === "stored_draft" ? (
          <p className="module-muted">Stored as non-corpus draft: <code>statblock_drafts/{artifact.artifact_id}.json</code></p>
        ) : null}
        {storeMessage ? <p className="statblock-command-status" role="status">{storeMessage}</p> : null}
        {storeError ? <p className="statblock-command-error" role="alert">Unable to store draft: {storeError}</p> : null}
      </section>

      <StatusRail artifact={artifact} commandStatus={response.command_status} />

      <StoredDraftsList drafts={storedDrafts} loading={storedDraftsLoading} error={storedDraftsError} pendingLoadId={pendingLoadId} onLoadDraft={onLoadDraft} />

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
        ) : <p className="module-muted">No warnings returned by the sample artifact.</p>}
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
          {futureActions.map((action) => {
            const disabledReason = action.disabled_reason ?? "Disabled in this draft-storage PR; future PRs will add handlers.";
            return (
              <div key={action.action_id} className="statblock-action-card">
                <button type="button" disabled aria-disabled="true">{action.label}</button>
                <small>{disabledReason}</small>
              </div>
            );
          })}
        </div>
      </section>

      {response.diagnostics.length ? (
        <section className="statblock-section">
          <h3>Diagnostics</h3>
          <ul className="module-list">{response.diagnostics.map((diagnostic) => <li key={diagnostic}>{diagnostic}</li>)}</ul>
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
  const [pendingStore, setPendingStore] = useState(false);
  const [storeError, setStoreError] = useState<string | null>(null);
  const [storeMessage, setStoreMessage] = useState<string | null>(null);
  const [storedDrafts, setStoredDrafts] = useState<StoredStatblockDraftSummary[]>([]);
  const [storedDraftsLoading, setStoredDraftsLoading] = useState(true);
  const [storedDraftsError, setStoredDraftsError] = useState<string | null>(null);
  const [pendingLoadId, setPendingLoadId] = useState<string | null>(null);

  const refreshStoredDrafts = useCallback(() => {
    setStoredDraftsLoading(true);
    setStoredDraftsError(null);
    return listStatblockWorkbenchDrafts()
      .then((listResponse: ListStatblockDraftsResponse) => setStoredDrafts(listResponse.drafts))
      .catch((err: unknown) => setStoredDraftsError(err instanceof Error ? err.message : String(err)))
      .finally(() => setStoredDraftsLoading(false));
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([getStatblockWorkbenchSample(), listStatblockWorkbenchDrafts()])
      .then(([sample, draftList]) => {
        if (active) {
          setResponse(sample);
          setStoredDrafts(draftList.drafts);
        }
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (active) {
          setLoading(false);
          setStoredDraftsLoading(false);
        }
      });
    return () => { active = false; };
  }, []);

  const runCommand = (commandType: StatblockWorkbenchCommandType) => {
    setPendingCommand(commandType);
    setCommandError(null);
    setStoreMessage(null);
    postStatblockWorkbenchCommand({
      command_type: commandType,
      requested_by: "human",
      breadcrumbs: [{
        label: "surface:statblock_workbench",
        source: "live_control_ui",
        metadata: { trigger: commandType === "statblock.draft.generate" ? "generate_mock_draft" : "render_mock_statblock" },
      }],
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
      .catch((err: unknown) => setCommandError(err instanceof Error ? err.message : String(err)))
      .finally(() => setPendingCommand(null));
  };

  const storeCurrentDraft = () => {
    if (!response?.artifact) return;
    setPendingStore(true);
    setStoreError(null);
    setStoreMessage(null);
    storeStatblockWorkbenchDraft({ artifact: response.artifact, source: "workbench" })
      .then((storeResponse) => {
        setResponse((current) => current ? { ...current, artifact: storeResponse.record.artifact, command_status: "stored" } : current);
        setStoreMessage(`Stored as non-corpus draft: ${storeResponse.record.storage_path}`);
        return refreshStoredDrafts();
      })
      .catch((err: unknown) => setStoreError(err instanceof Error ? err.message : String(err)))
      .finally(() => setPendingStore(false));
  };

  const loadStoredDraft = (artifactId: string) => {
    setPendingLoadId(artifactId);
    setStoreError(null);
    setStoreMessage(null);
    getStatblockWorkbenchDraft(artifactId)
      .then((readResponse) => {
        setResponse((current) => current ? { ...current, artifact: readResponse.record.artifact, command_status: "loaded_stored_draft" } : {
          schema_version: readResponse.schema_version,
          mode: "stored_draft",
          artifact: readResponse.record.artifact,
          command_status: "loaded_stored_draft",
          diagnostics: ["loaded stored non-corpus draft artifact"],
          available_actions: [],
        });
        setStoreMessage(`Loaded non-corpus draft: ${readResponse.record.storage_path}`);
      })
      .catch((err: unknown) => setStoreError(err instanceof Error ? err.message : String(err)))
      .finally(() => setPendingLoadId(null));
  };

  if (loading) {
    return <div className="module-panel statblock-workbench" data-module-id="statblock_workbench"><h2 className="module-title">Statblock Workbench</h2><p className="module-muted">Loading read-only sample artifact…</p></div>;
  }
  if (error) {
    return <div className="module-panel statblock-workbench" data-module-id="statblock_workbench"><h2 className="module-title">Statblock Workbench</h2><p className="module-error">Unable to load sample statblock artifact: {error}</p></div>;
  }
  if (!response) {
    return <div className="module-panel statblock-workbench" data-module-id="statblock_workbench"><h2 className="module-title">Statblock Workbench</h2><p className="module-muted">No sample artifact returned.</p></div>;
  }

  return (
    <ReadyWorkbench
      response={response}
      pendingCommand={pendingCommand}
      commandError={commandError}
      storeError={storeError}
      storeMessage={storeMessage}
      storedDrafts={storedDrafts}
      storedDraftsLoading={storedDraftsLoading}
      storedDraftsError={storedDraftsError}
      pendingStore={pendingStore}
      pendingLoadId={pendingLoadId}
      onRunCommand={runCommand}
      onStoreDraft={storeCurrentDraft}
      onLoadDraft={loadStoredDraft}
    />
  );
}
