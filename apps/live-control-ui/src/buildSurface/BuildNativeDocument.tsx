import { useEffect, useState } from "react";
import { WorldPlanAgentAnswer } from "../planSurface/components/WorldPlanAgentAnswer";
import { readBuildNativeDocument } from "./buildNativeDocuments";

export function BuildNativeDocument({ worldId, revisionId }: { worldId: string; revisionId: string }) {
  const [document, setDocument] = useState<{ title: string; markdown: string }>();
  const [error, setError] = useState("");
  useEffect(() => {
    const request = new AbortController();
    readBuildNativeDocument(worldId, revisionId, request.signal).then(
      result => { if (!request.signal.aborted) setDocument(result); },
      failure => {
        if (!request.signal.aborted) setError(failure instanceof Error ? failure.message : "Could not open document.");
      },
    );
    return () => request.abort();
  }, [worldId, revisionId]);

  if (error) return <p role="alert">{error}</p>;
  if (!document) return <p role="status">Opening document…</p>;
  return <article className="build-pdf-workspace" aria-label={document.title}>
    <h1>{document.title}</h1>
    <WorldPlanAgentAnswer answer={document.markdown} />
  </article>;
}
