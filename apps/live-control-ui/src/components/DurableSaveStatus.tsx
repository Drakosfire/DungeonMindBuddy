import "./DurableSaveStatus.css";

export type DurableSaveState = "checking" | "saving" | "unsaved" | "saved" | "draft" | "needs-attention";

const LABELS: Record<DurableSaveState, string> = {
  checking: "Checking save status",
  saving: "Saving",
  unsaved: "Unsaved changes",
  saved: "Saved",
  draft: "Draft on this device",
  "needs-attention": "Save needs attention",
};

function parsedTimestamp(value: string | null): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatTimestamp(value: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(value);
}

export function DurableSaveStatus({
  state,
  savedAt,
}: {
  state: DurableSaveState;
  savedAt: string | null;
}) {
  const timestamp = parsedTimestamp(savedAt);
  const label = state === "saved" && !timestamp ? "Saved time unavailable" : LABELS[state];
  const showLastSaved = state !== "saved" && timestamp !== null;

  return (
    <span className="durable-save-status" role="status" data-save-state={state}>
      <span className="durable-save-status__label">{label}</span>
      {timestamp ? (
        <time className="durable-save-status__time" dateTime={timestamp.toISOString()}>
          {showLastSaved ? "Last saved " : ""}{formatTimestamp(timestamp)}
        </time>
      ) : null}
    </span>
  );
}
