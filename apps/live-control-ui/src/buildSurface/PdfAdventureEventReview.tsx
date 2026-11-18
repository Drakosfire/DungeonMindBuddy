import { useState } from "react";
import { authenticatedApiFetch } from "../api/liveApi";
import type { PdfLocator } from "../api/retainedPdfRegions";

type Draft = { operation_id: string; region: PdfLocator; name: string; description: string };
type Prepared = { draft: Draft; prepared: Record<string, unknown>; token: string };
type Receipt = { node_id: string; published_revision_id: string };

function editableOcr(text: string): string {
  return text.replace(/<\|ref\|>[^\n]*?<\|\/ref\|>\s*<\|det\|>[\s\S]*?<\|\/det\|>/g, "").trim();
}

export function PdfAdventureEventReview({ worldId, locator, text }: {
  worldId: string;
  locator: PdfLocator;
  text: string;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState(() => editableOcr(text));
  const [prepared, setPrepared] = useState<Prepared>();
  const [receipt, setReceipt] = useState<Receipt>();
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [error, setError] = useState("");
  const path = `/api/live/worlds/${encodeURIComponent(worldId)}/pdf-adventure-events`;

  async function submit() {
    const action = prepared ? "confirm" : "prepare";
    const body = prepared ?? {
      operation_id: crypto.randomUUID(), region: locator,
      name: name.trim(), description: description.trim(),
    };
    setError("");
    setPending(true);
    let received = false;
    try {
      const { response } = await authenticatedApiFetch(`${path}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const result = await response.json();
      received = true;
      if (!response.ok) {
        if (prepared && (response.status >= 500 || result.detail?.retry_original_packet)) {
          setUncertain(true);
        }
        throw new Error(result.detail?.message ?? "Buddy could not complete the Event review.");
      }
      if (prepared) {
        if (typeof result.node_id !== "string" || typeof result.published_revision_id !== "string") {
          setUncertain(true);
          throw new Error("The publication receipt could not be verified. Retry this confirmation.");
        }
        setReceipt(result);
        setUncertain(false);
      } else {
        if (typeof result.token !== "string" || !result.prepared || !result.draft) {
          throw new Error("Buddy did not return an Event review.");
        }
        setPrepared(result);
      }
    } catch (failure) {
      if (prepared && !received) setUncertain(true);
      setError(failure instanceof Error ? failure.message : "Event review failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <details>
      <summary>Save as adventure Event</summary>
      {receipt ? <p role="status">Published as prep · {receipt.node_id}</p> : (
        <div>
          <label>Event name
            <input value={prepared?.draft.name ?? name} maxLength={240}
              readOnly={pending || !!prepared} onChange={event => setName(event.target.value)} />
          </label>
          <label>Event text
            <textarea value={prepared?.draft.description ?? description} rows={8} maxLength={16000}
              readOnly={pending || !!prepared} onChange={event => setDescription(event.target.value)} />
          </label>
          <p>Source PDF · page {locator.page}</p>
          {prepared && <p>Review the text above before publishing it as adventure prep.</p>}
          <button type="button" disabled={pending || !name.trim() || !description.trim()} onClick={() => void submit()}>
            {prepared ? uncertain ? "Retry confirmation" : "Publish Event" : "Review Event"}
          </button>
          {prepared && !uncertain && <button type="button" disabled={pending} onClick={() => {
            setPrepared(undefined);
            setError("");
          }}>Edit draft</button>}
          {error && <p role="alert">{error}</p>}
        </div>
      )}
    </details>
  );
}
