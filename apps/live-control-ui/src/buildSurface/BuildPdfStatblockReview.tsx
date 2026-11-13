import { useEffect, useRef, useState } from "react";
import type { ThreatDraft } from "../api/types";
import type { SavedMechanicsVersionList } from "../statblocks/revision/savedMechanicsRevisionTypes";
import { authenticatedApiFetch, createThreatDraft, listSavedMechanicsVersions, LiveApiError } from "../api/liveApi";
import type { PdfLocator } from "../api/retainedPdfRegions";
import type { ValidationIssueV1 } from "../contracts/dungeonbuddy-statblocks-v1/client";
import { StatblockDefinitionEditor } from "../statblocks/editor/StatblockDefinitionEditor";
import { createEditorStateFromOutput, getLocalFingerprint, updateWorkingCopy, type EditableStatblockOutput, type StatblockEditorState } from "../statblocks/editor/statblockEditorState";
import "./BuildPdfStatblockReview.css";

type Review = {
  revision: number;
  definition: EditableStatblockOutput;
  regions: PdfLocator[];
};

export function BuildPdfStatblockReview({ worldId, reviewId }: { worldId: string; reviewId: string }) {
  const sourcePath = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources`;
  const reviewPath = `${sourcePath}/statblock-reviews/${encodeURIComponent(reviewId)}`;
  const [review, setReview] = useState<Review>();
  const [editor, setEditor] = useState<StatblockEditorState<EditableStatblockOutput>>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [validation, setValidation] = useState("");
  const [issues, setIssues] = useState<ValidationIssueV1[]>([]);
  const [region, setRegion] = useState<PdfLocator>();
  const [image, setImage] = useState("");
  const sourcePreviewRef = useRef<HTMLElement>(null);
  const [drafts, setDrafts] = useState<ThreatDraft[]>([]);
  const [draftId, setDraftId] = useState("");
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [acceptedLink, setAcceptedLink] = useState("");

  const [versions, setVersions] = useState<SavedMechanicsVersionList>();
  const [parentId, setParentId] = useState("");
  const selectedDraft = drafts.find(item => item.draft_id === draftId);
  const savedParents = versions ? [
    ...versions.operations.flatMap(operation => operation.state === "committed" && operation.result ? [operation.result] : []),
    versions.original,
  ] : [];

  const acceptanceKey = (id: string) =>
    `buddy:pdf-mechanics-accept:${worldId}:${reviewId}:${review?.revision}:${id}`;
  const [hasInitialAttempt, setHasInitialAttempt] = useState(false);

  async function chooseDraft(id: string) {
    setDraftId(id);
    setAcceptedLink("");
    setVersions(undefined);
    setParentId("");
    setError("");
    setHasInitialAttempt(Boolean(id && localStorage.getItem(acceptanceKey(id))));
    if (drafts.find(draft => draft.draft_id === id)?.workflow_state !== "mechanics_saved") return;
    setPending(true);
    try {
      const first = await listSavedMechanicsVersions(id, worldId);
      const operations = [...first.operations];
      let offset = first.next_offset;
      while (offset != null) {
        const next = await listSavedMechanicsVersions(id, worldId, offset);
        operations.push(...next.operations);
        offset = next.next_offset;
      }
      setVersions({ ...first, operations });
    } catch {
      setError("Could not load saved statblock versions.");
    } finally {
      setPending(false);
    }
  }

  async function appendMechanics() {
    const base = savedParents.find(locator => locator.revision_id === parentId);
    if (!base || !review || !editor || pending || getLocalFingerprint(editor) !== editor.baselineFingerprint) return;
    setPending(true);
    setError("");
    const key = `buddy:pdf-mechanics-append:${worldId}:${reviewId}:${review.revision}:${draftId}:${parentId}`;
    try {
      let payload = localStorage.getItem(key);
      if (!payload) {
        payload = JSON.stringify({ operation_id: crypto.randomUUID(), expected_revision: review.revision, base });
        localStorage.setItem(key, payload);
      }
      const { response } = await authenticatedApiFetch(
        `${reviewPath}/append/${encodeURIComponent(draftId)}`, { method: "POST", body: payload },
      );
      if (response.status === 409) {
        setError("The saved review or parent version changed. Reopen the review and check the parent version.");
        return;
      }
      if (!response.ok) throw new Error();
      const result = await response.json();
      if (result.state === "refused") {
        setError("This parent could not be used. Choose a current saved version.");
        return;
      }
      if (result.state !== "committed" || !result.result?.revision_id) throw new Error();
      setAcceptedLink(`/statblock?${new URLSearchParams({
        world: worldId, draft: draftId, revision: result.result.revision_id,
      })}`);
    } catch {
      setError("Could not confirm the new revision. Try again to recover the same operation.");
    } finally {
      setPending(false);
    }
  }

  const createKey = `buddy:pdf-creature-draft:${worldId}:${reviewId}`;
  const [createInFlight, setCreateInFlight] = useState(false);

  async function createDraft() {
    if (!review || !editor || pending || createInFlight) return;
    const name = review.definition.identity.name.trim();
    if (!name || getLocalFingerprint(editor) !== editor.baselineFingerprint) return;
    setPending(true);
    setCreateInFlight(true);
    setError("");
    try {
      if (!navigator.locks) {
        setError("This browser cannot safely coordinate draft creation across tabs.");
        return;
      }
      const reserved = await navigator.locks.request(createKey, () => {
        if (localStorage.getItem(createKey)) return false;
        localStorage.setItem(createKey, "pending");
        return true;
      });
      if (!reserved) {
        setError("Check the creature draft list for the previous creation attempt.");
        return;
      }
      const draft = await createThreatDraft({
        scope_mode: "world", world_id: worldId, campaign_id: null, name,
        description: name, threat_kind: "creature", intended_roles: [], tags: [],
        generation_intent: {
          ruleset: review.definition.ruleset, must_include: [], must_avoid: [],
        },
        encounter_context: { terrain_notes: [] },
        graph_context_snapshot: { graph_revision_id: null, selected_node_ids: [], admitted_source_anchor_ids: [] },
        created_by: "gm",
      });
      if (draft.schema !== "dmb_threat_draft_v2" || draft.world_id !== worldId) throw new Error();
      localStorage.setItem(createKey, draft.draft_id);
      setDrafts(current => [...current.filter(item => item.draft_id !== draft.draft_id), draft]);
      setDraftId(draft.draft_id);
      setVersions(undefined);
      setParentId("");
      setHasInitialAttempt(false);
      setAcceptedLink("");
      setAcceptOpen(true);
    } catch (cause) {
      if (cause instanceof LiveApiError && [401, 403, 404, 422].includes(cause.status)) {
        localStorage.removeItem(createKey);
        setError(cause.message);
        return;
      }
      setError("Could not confirm draft creation. Check the creature draft list before creating another.");
    } finally {
      setCreateInFlight(false);
      setPending(false);
    }
  }

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
    const key = acceptanceKey(draftId);
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
      setHasInitialAttempt(false);
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
      {review && <>
          {review.regions.map((locator, index) => (
            <button type="button" key={index} onClick={() => { setError(""); setRegion(locator); }}>
              Open source region {index + 1} · Page {locator.page}
            </button>
          ))}
          {image && region && <figure ref={sourcePreviewRef} className="pdf-statblock-review__source-preview"
            aria-label={`Source evidence · Page ${region.page}`}>
            <figcaption>Source evidence · Page {region.page}</figcaption>
            <img src={image} alt={`Exact PDF region on page ${region.page}`}
              onLoad={() => sourcePreviewRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })} />
          </figure>}
      </>}
      {editor && !editor.workingCopy.movement && <form onSubmit={event => {
        event.preventDefault();
        const speed = new FormData(event.currentTarget).get("walkSpeed");
        if (typeof speed !== "string" || !/^\d+$/.test(speed) || !Number.isSafeInteger(Number(speed))) return;
        setEditor(updateWorkingCopy(editor, current => ({ ...current, movement: { modes: [{
          key: "walk", mode: "walk" as const, distance: { unit: "feet" as const, value: Number(speed) },
        }] } })));
        setSaved(false);
      }}>
        <p>Movement is unspecified. You can save the review now or enter a speed to validate mechanics.</p>
        <label>Walking speed (feet)
          <input name="walkSpeed" type="number" min="0" step="1" required />
        </label>
        <button type="submit">Set walking speed</button>
      </form>}
      {review && editor && <>
        <fieldset disabled={pending}>
          <button type="button" disabled={!editor.workingCopy.movement} onClick={() => void validate()}>Validate mechanics</button>
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
          <button type="button" disabled={!editor.workingCopy.movement || createInFlight || getLocalFingerprint(editor) !== editor.baselineFingerprint}
            onClick={() => void createDraft()}>Create creature draft from review</button>
          {!acceptOpen && <button type="button" disabled={!editor.workingCopy.movement} onClick={() => void openAcceptance()}>Choose creature draft</button>}
          {acceptOpen && <>
            <label>Creature draft
              <select value={draftId} onChange={event => void chooseDraft(event.target.value)}>
                <option value="">Select a draft</option>
                {drafts.map(draft => <option key={draft.draft_id} value={draft.draft_id}>{draft.name}</option>)}
              </select>
            </label>
            {selectedDraft?.workflow_state === "mechanics_saved" ? <>
              <label>Parent statblock version
                <select value={parentId} onChange={event => { setParentId(event.target.value); setAcceptedLink(""); }}>
                  <option value="">Select a saved version</option>
                  {savedParents.map(locator => <option key={locator.revision_id} value={locator.revision_id}>
                    {locator.revision_id}{locator.revision_id === versions?.original.revision_id ? " (original)" : ""}
                  </option>)}
                </select>
              </label>
              <button type="button" disabled={!parentId || getLocalFingerprint(editor) !== editor.baselineFingerprint}
                onClick={() => void appendMechanics()}>Append mechanics revision</button>
            </> : null}
            {(selectedDraft?.workflow_state !== "mechanics_saved" || hasInitialAttempt) &&
              <button type="button" disabled={!draftId || getLocalFingerprint(editor) !== editor.baselineFingerprint}
              onClick={() => void acceptMechanics()}>{selectedDraft?.workflow_state === "mechanics_saved" ? "Recover initial acceptance" : "Accept mechanics"}</button>}
            {acceptedLink && <a href={acceptedLink}>Open accepted statblock</a>}
          </>}
          <StatblockDefinitionEditor output={review.definition} editorState={editor}
            onEditorStateChange={state => { setEditor(state); setSaved(false); setValidation(""); setIssues([]); }}
            recoveryHint="Save the review draft to keep your edits." />
        </fieldset>
      </>}
    </section>
  );
}
