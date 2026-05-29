import type { ArtifactReadResponse } from "../api/types";

function stringField(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function objectField(value: unknown): Record<string, unknown> | null {
  if (value == null || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

type EventArtifact = ArtifactReadResponse & { artifact_kind: "event" };
type RollTableArtifact = ArtifactReadResponse & { artifact_kind: "roll_table" };

export function EventArtifactRenderer({ artifact }: { artifact: EventArtifact }) {
  const row = artifact.payload.data ?? {};
  const eventType = stringField(row.event_type);
  const createdAt = stringField(row.created_at);
  const summary = stringField(row.summary);
  const latencyMode = stringField(row.latency_mode);
  const eventOrigin = stringField(row.event_origin);
  const inputText = stringField(row.input_text);
  const derivedFields = objectField(row.derived_fields);

  return (
    <section className="artifact-block" aria-label="Event artifact">
      <h3 className="artifact-title">{artifact.title}</h3>
      <dl className="artifact-fields">
        {eventType ? (
          <div>
            <dt>event_type</dt>
            <dd>{eventType}</dd>
          </div>
        ) : null}
        {createdAt ? (
          <div>
            <dt>created_at</dt>
            <dd>{createdAt}</dd>
          </div>
        ) : null}
        {latencyMode ? (
          <div>
            <dt>latency_mode</dt>
            <dd>{latencyMode}</dd>
          </div>
        ) : null}
        {eventOrigin ? (
          <div>
            <dt>origin</dt>
            <dd>{eventOrigin}</dd>
          </div>
        ) : null}
      </dl>

      {summary ? (
        <>
          <h4 className="artifact-subtitle">Summary</h4>
          <p className="artifact-summary">{summary}</p>
        </>
      ) : null}

      {inputText ? (
        <>
          <h4 className="artifact-subtitle">Input</h4>
          <pre className="artifact-pre">{inputText}</pre>
        </>
      ) : null}

      {derivedFields ? (
        <>
          <h4 className="artifact-subtitle">Derived fields</h4>
          <pre className="artifact-pre">{JSON.stringify(derivedFields, null, 2)}</pre>
        </>
      ) : null}
    </section>
  );
}

export function RollTableArtifactRenderer({ artifact }: { artifact: RollTableArtifact }) {
  const tableId = stringField(artifact.metadata.table_id);
  const dice = stringField(artifact.metadata.dice);
  const status = stringField(artifact.metadata.status);
  const defaultLatencyMode = stringField(artifact.metadata.default_latency_mode);
  const parsedSummary = objectField(artifact.metadata.parsed_summary);
  const markdown = stringField(artifact.payload.text) ?? "";

  return (
    <section className="artifact-block" aria-label="Roll table artifact">
      <h3 className="artifact-title">{artifact.title}</h3>
      <dl className="artifact-fields">
        {tableId ? (
          <div>
            <dt>table_id</dt>
            <dd>{tableId}</dd>
          </div>
        ) : null}
        {dice ? (
          <div>
            <dt>dice</dt>
            <dd>{dice}</dd>
          </div>
        ) : null}
        {status ? (
          <div>
            <dt>status</dt>
            <dd>{status}</dd>
          </div>
        ) : null}
        {defaultLatencyMode ? (
          <div>
            <dt>default_latency_mode</dt>
            <dd>{defaultLatencyMode}</dd>
          </div>
        ) : null}
      </dl>

      {parsedSummary ? (
        <>
          <h4 className="artifact-subtitle">Parsed summary</h4>
          <pre className="artifact-pre">{JSON.stringify(parsedSummary, null, 2)}</pre>
        </>
      ) : null}

      <h4 className="artifact-subtitle">Markdown</h4>
      <pre className="artifact-markdown">{markdown}</pre>
    </section>
  );
}
