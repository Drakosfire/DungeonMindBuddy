import { useEffect, useState } from "react";
import type { ThreatDraft } from "../api/types";
import { authenticatedApiFetch } from "../api/liveApi";
import type { PdfLocator } from "../api/retainedPdfRegions";
import type { StatblockDefinitionV1_Output, ValidationIssueV1 } from "../contracts/dungeonbuddy-statblocks-v1/client";
import { StatblockDefinitionEditor } from "../statblocks/editor/StatblockDefinitionEditor";
import { createEditorStateFromOutput, getLocalFingerprint, type StatblockEditorState } from "../statblocks/editor/statblockEditorState";

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
  const [drafts, setDrafts] = useState<ThreatDraft[]>([]);
  const [draftId, setDraftId] = useState("");
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [acceptedLink, setAcceptedLink] = useState("");

  async function openAcceptance() {
    setPending(true);
    setError("");
    try {
      const { response } = await authenticatedApiFetch(
        `/api/live/threat-drafts?world_id=${encodeURIComponent(worldId)}`,
      );
      if (!response.ok) throw new Error();
      const { drafts: worldDrafts } = await response.json();
      setDrafts(worldDrafts);
      setAcceptOpen(true);
    } catch {
      setError("Could not load the World’s creature drafts.");
    } finally {
      setPending(false);
    }
  }

  async function acceptMechanics() {
    const draft = drafts.find(item => item.draft_id === draftId);
    if (!draft || !review || !editor || pending || getLocalFingerprint(editor) !== editor.baselineFingerprint) return;
    setPending(true);
    setError("");
    const key = `buddy:pdf-mechanics-accept:${worldId}:${reviewId}:${review.revision}:${draftId}`;
    try {
      let payload = localStorage.getItem(key);
      if (!payload) {
        const { response } = await authenticatedApiFetch(
          `${reviewPath}/validate?expected_revision=${review.revision}`, { method: "POST" },
        );
        if (response.status === 409) {
          setError("This review changed elsewhere. Reload before accepting mechanics.");
          return;
        }
        if (!response.ok) throw new Error();
        const { validation: result } = await response.json();
        const receipt = result?.validation_receipt;
        if (result?.outcome !== "success" || !receipt) throw new Error();
        setIssues(receipt.issues ?? []);
        if (receipt.status === "invalid" || receipt.issues?.some((issue: ValidationIssueV1) => issue.severity === "error")) {
          setError("Correct the validation issues before accepting mechanics.");
          return;
        }
        payload = JSON.stringify({
          operation_id: crypto.randomUUID(), expected_draft_version: draft.version,
          expected_revision: review.revision, validation_receipt: receipt,
          validation_definition_digest: result.definition_digest,
        });
        localStorage.setItem(key, payload);
      }
      const { response } = await authenticatedApiFetch(
        `${reviewPath}/accept/${encodeURIComponent(draftId)}`, { method: "POST", body: payload },
      );
      if (response.status === 409) {
        setError("The saved review or acceptance changed. Reopen the review to check its current state.");
        return;
      }
      if (!response.ok) throw new Error();
      const result = await response.json();
      if (result.result_label === "acceptance_blocked" && result.message === "expected draft version mismatch") {
        localStorage.removeItem(key);
        await openAcceptance();
        setError("The creature draft changed before acceptance. Review your draft selection and try again.");
        return;
      }
      if (result.result_label !== "mechanics_saved" || !result.locator?.revision_id) {
        setError(result.message || "Mechanics acceptance is unresolved. Select Accept mechanics again to check the same operation.");
        return;
      }
      setAcceptedLink(`/statblock?${new URLSearchParams({
        world: worldId, draft: draftId, revision: result.locator.revision_id,
      })}`);
    } catch {
      setError("Could not confirm mechanics acceptance. Try again to recover the same operation.");
    } finally {
      setPending(false);
    }
  }

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
      const unchanged = getLocalFingerprint(editor) === editor.baselineFingerprint;
      const { response } = unchanged
        ? await authenticatedApiFetch(`${reviewPath}/validate?expected_revision=${review.revision}`, { method: "POST" })
        : await authenticatedApiFetch(sourcePath + "/statblock:validate", {
          method: "POST",
          body: JSON.stringify({ definition: editor.workingCopy, regions: review.regions }),
        });
      if (unchanged && response.status === 409) {
        setError("This review changed elsewhere. Reload it before validating the saved revision.");
        return;
      }
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
          {!acceptOpen && <button type="button" onClick={() => void openAcceptance()}>Choose creature draft</button>}
          {acceptOpen && <>
            <label>Creature draft
              <select value={draftId} onChange={event => { setDraftId(event.target.value); setAcceptedLink(""); }}>
                <option value="">Select a draft</option>
                {drafts.map(draft => <option key={draft.draft_id} value={draft.draft_id}>{draft.name}</option>)}
              </select>
            </label>
            <button type="button" disabled={!draftId || getLocalFingerprint(editor) !== editor.baselineFingerprint}
              onClick={() => void acceptMechanics()}>Accept mechanics</button>
            {acceptedLink && <a href={acceptedLink}>Open accepted statblock</a>}
          </>}
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
