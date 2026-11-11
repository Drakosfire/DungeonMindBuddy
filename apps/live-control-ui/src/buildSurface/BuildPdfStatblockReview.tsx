import { useEffect, useState } from "react";
import { authenticatedApiFetch } from "../api/liveApi";
import type { PdfLocator } from "../api/retainedPdfRegions";
import type { StatblockDefinitionV1_Output, ValidationIssueV1 } from "../contracts/dungeonbuddy-statblocks-v1/client";
import { StatblockDefinitionEditor } from "../statblocks/editor/StatblockDefinitionEditor";
import { createEditorStateFromOutput, type StatblockEditorState } from "../statblocks/editor/statblockEditorState";

type Review = {
  revision: number;
  definition: StatblockDefinitionV1_Output;
  regions: PdfLocator[];
};

export function BuildPdfStatblockReview({ worldId, reviewId }: { worldId: string; reviewId: string }) {
  const sourcePath = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources`;
  const reviewPath = `${sourcePath}/statblock-reviews/${encodeURIComponent(reviewId)}`;
  const [review, setReview] = useState<Review>();
  const [editor, setEditor] = useState<StatblockEditorState>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [validation, setValidation] = useState("");
  const [issues, setIssues] = useState<ValidationIssueV1[]>([]);
  const [region, setRegion] = useState<PdfLocator>();
  const [image, setImage] = useState("");

  useEffect(() => {
    const abort = new AbortController();
    void (async () => {
      try {
        const { response } = await authenticatedApiFetch(reviewPath, { signal: abort.signal });
        if (!response.ok) throw new Error();
        const result: Review = await response.json();
        if (abort.signal.aborted) return;
        setEditor(createEditorStateFromOutput(result.definition));
        setReview(result);
      } catch {
        if (!abort.signal.aborted) setError("Could not open the statblock review.");
      }
    })();
    return () => abort.abort();
  }, [reviewPath]);

  useEffect(() => {
    if (!region) return;
    const abort = new AbortController();
    let url: string | undefined;
    setImage("");
    void (async () => {
      try {
        const { response } = await authenticatedApiFetch(sourcePath + "/open?render=true", {
          method: "POST", body: JSON.stringify(region), signal: abort.signal,
        });
        if (!response.ok) throw new Error();
        const blob = await response.blob();
        if (abort.signal.aborted) return;
        url = URL.createObjectURL(blob);
        setImage(url);
      } catch {
        if (!abort.signal.aborted) setError("Could not open the exact PDF region.");
      }
    })();
    return () => {
      abort.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [region, sourcePath]);

  async function validate() {
    if (!review || !editor || pending) return;
    setPending(true);
    setError("");
    setValidation("");
    setIssues([]);
    try {
      const { response } = await authenticatedApiFetch(sourcePath + "/statblock:validate", {
        method: "POST",
        body: JSON.stringify({ definition: editor.workingCopy, regions: review.regions }),
      });
      if (!response.ok) throw new Error();
      const { validation: result } = await response.json();
      const receipt = result?.validation_receipt;
      if (result?.outcome !== "success" || !receipt) throw new Error();
      setIssues(receipt.issues ?? []);
      if (receipt.status === "valid") {
        setValidation("Mechanics validated.");
      } else if (receipt.status === "warnings") {
        setValidation("Mechanics validated with warnings.");
      } else {
        setError("The mechanics did not pass validation.");
      }
    } catch {
      setError("Could not validate the review draft.");
    } finally {
      setPending(false);
    }
  }

  async function save() {
    if (!review || !editor || pending) return;
    setPending(true);
    setSaved(false);
    setError("");
    try {
      const { response } = await authenticatedApiFetch(reviewPath, {
        method: "PUT",
        body: JSON.stringify({
          expected_revision: review.revision, definition: editor.workingCopy, regions: review.regions,
        }),
      });
      if (response.status === 409) {
        setError("This review changed elsewhere. Copy your edits before reloading.");
        return;
      }
      if (!response.ok) throw new Error();
      const result: Review = await response.json();
      setEditor(createEditorStateFromOutput(result.definition));
      setReview(result);
      setSaved(true);
    } catch {
      setError("Could not save the review draft.");
    } finally {
      setPending(false);
    }
  }

  return (
    <section aria-label="PDF statblock review">
      <h1>PDF statblock review</h1>
      {error && <p role="alert">{error}</p>}
      {!review && !error && <p role="status">Opening review…</p>}
      {review && editor && <>
        <fieldset disabled={pending}>
          <button type="button" onClick={() => void validate()}>Validate mechanics</button>
          {validation && <span role="status">{validation}</span>}
          {issues.length > 0 && <ul aria-label="Mechanics validation issues">
            {issues.map((issue, index) => (
              <li key={index}>
                <strong>{issue.severity}</strong> {issue.message}
                {issue.field_path && <div><code>{issue.field_path}</code></div>}
                {issue.suggested_resolution && <div>{issue.suggested_resolution}</div>}
              </li>
            ))}
          </ul>}
          <button type="button" onClick={() => void save()}>Save review draft</button>
          {saved && <span role="status">Draft saved</span>}
          {review.regions.map((locator, index) => (
            <button type="button" key={index} onClick={() => { setError(""); setRegion(locator); }}>
              Open source region {index + 1} · Page {locator.page}
            </button>
          ))}
          {image && region && <img src={image} alt={`Exact PDF region on page ${region.page}`} />}
          <StatblockDefinitionEditor output={review.definition} editorState={editor}
            onEditorStateChange={state => { setEditor(state); setSaved(false); setValidation(""); setIssues([]); }}
            recoveryHint="Save the review draft to keep your edits." />
        </fieldset>
      </>}
    </section>
  );
}
