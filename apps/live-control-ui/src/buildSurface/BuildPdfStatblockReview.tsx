import { buildSavedStatblockHref } from "../statblocks/savedStatblockLocation";
import { useHostedAuthStatus } from "../auth/HostedAuthGate";
import { createPortal } from "react-dom";
import { PdfPages } from "./BuildPdfPreview";
import { BuildSourceWorkspace } from "./BuildSourceWorkspace";
import { publishPdfStatblock } from "./publishPdfStatblock";
import { useEffect, useState } from "react";
import type { ThreatDraft } from "../api/types";
import type { SavedMechanicsVersionList } from "../statblocks/revision/savedMechanicsRevisionTypes";
import { authenticatedApiFetch, getThreatDraft, listSavedMechanicsVersions } from "../api/liveApi";
import type { PdfLocator } from "../api/retainedPdfRegions";
import type { ValidationIssueV1 } from "../contracts/dungeonbuddy-statblocks-v1/client";
import { StatblockRenderer } from "../statblocks/render/StatblockRenderer";
import { StatblockDefinitionEditor } from "../statblocks/editor/StatblockDefinitionEditor";
import { createEditorStateFromOutput, getLocalFingerprint, readHitPointsMax, setHitPointsMax, setRuleElementRulesText, updateWorkingCopy, type EditableStatblockOutput, type StatblockEditorState } from "../statblocks/editor/statblockEditorState";
import "./BuildPdfStatblockReview.css";

type Review = {
  revision: number;
  definition: EditableStatblockOutput;
  regions: PdfLocator[];
  artwork?: { jpeg_base64: string };
};

export function BuildPdfStatblockReview({ worldId, reviewId, toolbarHost }: { worldId: string; reviewId: string; toolbarHost?: HTMLElement | null }) {
  const auth = useHostedAuthStatus();
  const sourcePath = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources`;
  const reviewPath = `${sourcePath}/statblock-reviews/${encodeURIComponent(reviewId)}`;
  const [review, setReview] = useState<Review>();
  const [editor, setEditor] = useState<StatblockEditorState<EditableStatblockOutput>>();
  const [navigationHost, setNavigationHost] = useState<HTMLDivElement | null>(null);
  const [sourceHidden, setSourceHidden] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [developerTools, setDeveloperTools] = useState(false);
  const [saved, setSaved] = useState(false);
  const [validation, setValidation] = useState("");
  const [issues, setIssues] = useState<ValidationIssueV1[]>([]);
  const [region, setRegion] = useState<PdfLocator>();
  const [regionSelection, setRegionSelection] = useState(0);
  const [source, setSource] = useState<{ key: string; file: File }>();
  const [sourceError, setSourceError] = useState("");
  const sourceKey = region && JSON.stringify([region.source_revision_id, region.content_sha256]);
  const [drafts, setDrafts] = useState<ThreatDraft[]>([]);
  const [draftId, setDraftId] = useState("");
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [publishedLink, setPublishedLink] = useState("");
  const published = Boolean(publishedLink);
  const [acceptedLink, setAcceptedLink] = useState("");

  const [versions, setVersions] = useState<SavedMechanicsVersionList>();
  const [parentId, setParentId] = useState("");
  const mechanicsResolved = Boolean(editor?.workingCopy.movement && editor.workingCopy.ruleset)
    && editor?.workingCopy.challenge.proficiency_bonus != null;
  const selectedDraft = drafts.find(item => item.draft_id === draftId);
  const savedParents = versions ? [
    ...versions.operations.flatMap(operation => operation.state === "committed" && operation.result ? [operation.result] : []),
    versions.original,
  ] : [];

  const acceptanceKey = (id: string) =>
    `buddy:pdf-mechanics-accept:${worldId}:${reviewId}:${review?.revision}:${id}`;
  const [hasInitialAttempt, setHasInitialAttempt] = useState(false);

  async function chooseDraft(id: string, selected = drafts.find(draft => draft.draft_id === id)) {
    setDraftId(id);
    setAcceptedLink("");
    setVersions(undefined);
    setParentId("");
    setError("");
    setHasInitialAttempt(Boolean(id && localStorage.getItem(acceptanceKey(id))));
    if (selected?.workflow_state !== "mechanics_saved") return;
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

  const returnToBuild = new URL(window.location.href);
  returnToBuild.searchParams.delete("pdfReview");
  const createKey = `buddy:pdf-creature-draft:${worldId}:${reviewId}`;
  const [createInFlight, setCreateInFlight] = useState(false);

  async function getOrCreateReviewDraft(revision: number): Promise<{ draft_id: string; version: number }> {
    const { response } = await authenticatedApiFetch(
      `${reviewPath}/creature-draft?expected_revision=${revision}`,
      { method: "POST" },
    );
    if (!response.ok) {
      const failure = await response.json().catch(() => null);
      throw new Error(typeof failure?.detail === "string" ? failure.detail :
        failure?.detail?.code === "pdf_statblock_review_conflict" ? "This review changed. Reopen it before creating a creature." :
        "Could not create the creature draft. Check the source confirmation and try again.");
    }
    const result = await response.json();
    if (typeof result.draft_id !== "string" || !result.draft_id || !Number.isSafeInteger(result.version) || result.version < 1) {
      throw new Error("The review returned an invalid draft reference.");
    }
    return { draft_id: result.draft_id, version: result.version };
  }

  async function recoverDraft(revision: number) {
    const previousDraft = localStorage.getItem(createKey);
    if (previousDraft === "pending") {
      throw new Error("Choose the previously created creature draft before continuing.");
    }
    const id = previousDraft ?? (await getOrCreateReviewDraft(revision)).draft_id;
    const draft = await getThreatDraft(id);
    if (draft.schema !== "dmb_threat_draft_v2" || draft.world_id !== worldId || draft.draft_id !== id) throw new Error();
    return draft;
  }

  async function createDraft() {
    if (!review || !editor || pending || createInFlight) return;
    const name = review.definition.identity.name.trim();
    if (!name || getLocalFingerprint(editor) !== editor.baselineFingerprint) return;
    setPending(true);
    setCreateInFlight(true);
    setError("");
    try {
      const draft = await recoverDraft(review.revision);
      if (draft.workflow_state === "mechanics_saved") {
        setDrafts(current => [...current.filter(item => item.draft_id !== draft.draft_id), draft]);
        setAcceptOpen(true);
        await chooseDraft(draft.draft_id, draft);
        return;
      }
      setDrafts(current => [...current.filter(item => item.draft_id !== draft.draft_id), draft]);
      setDraftId(draft.draft_id);
      setVersions(undefined);
      setParentId("");
      setHasInitialAttempt(false);
      setAcceptedLink("");
      setAcceptOpen(true);
    } catch (cause) {
      setError(cause instanceof Error && cause.message ? cause.message :
        "Could not confirm draft creation. Try again to recover the same draft.");
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

  async function acceptMechanics(publish = false) {
    if (!review || !editor || pending || getLocalFingerprint(editor) !== editor.baselineFingerprint) return;
    setPending(true);
    setError("");
    try {
      const draft = publish ? await getOrCreateReviewDraft(review.revision)
        : drafts.find(item => item.draft_id === draftId);
      if (!draft) return;
      const key = acceptanceKey(draft.draft_id);
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
        `${reviewPath}/accept/${encodeURIComponent(draft.draft_id)}`, { method: "POST", body: payload },
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
      const link = `/statblock?${new URLSearchParams({
        world: worldId, draft: draft.draft_id, revision: result.locator.revision_id,
      })}`;
      if (publish) {
        if (auth.status === "authenticated") {
          const { response: publication } = await authenticatedApiFetch(
            `${reviewPath}/publication?expected_revision=${review.revision}`, { method: "POST" },
          );
          const published = await publication.json().catch(() => null);
          if (!publication.ok) throw new Error(typeof published?.detail === "string"
            ? published.detail : "Publication stopped. Retry Publish to resume.");
          if (published?.draft_id !== draft.draft_id || published?.revision_id !== result.locator.revision_id) {
            throw new Error("Publication returned a different saved revision.");
          }
        } else {
          const current = await getOrCreateReviewDraft(review.revision);
          if (current.draft_id !== draft.draft_id) throw new Error("The review draft changed during publication.");
          await publishPdfStatblock(worldId, draft.draft_id, current.version, result.locator);
        }
        setPublishedLink(auth.status === "authenticated" ? buildSavedStatblockHref({
          worldId, draftId: draft.draft_id, revisionId: result.locator.revision_id, sourceReviewId: reviewId,
        }) : link);
      } else {
        setAcceptedLink(link);
      }
    } catch (failure) {
      setError(publish
        ? (failure instanceof Error ? failure.message : "Publication stopped. Retry Publish to resume.")
        : "Could not confirm mechanics acceptance. Try again to recover the same operation.");
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
        setRegion(result.regions[0]);
      } catch {
        if (!abort.signal.aborted) setError("Could not open the statblock review.");
      }
    })();
    return () => abort.abort();
  }, [reviewPath]);

  useEffect(() => {
    const abort = new AbortController();
    void (async () => {
      try {
        const { response } = await authenticatedApiFetch(`${reviewPath}/publication`, { signal: abort.signal });
        if (!response.ok) return;
        const result = await response.json();
        if (!abort.signal.aborted && result?.draft_id && result.revision_id) {
          const link = `/statblock?${new URLSearchParams({
            world: worldId, draft: result.draft_id, revision: result.revision_id,
          })}`;
          setPublishedLink(current => current || (auth.status === "authenticated" ? buildSavedStatblockHref({
            worldId, draftId: result.draft_id, revisionId: result.revision_id, sourceReviewId: reviewId,
          }) : link));
        }
      } catch {
        // Publication can still be resumed when status lookup is unavailable.
      }
    })();
    return () => abort.abort();
  }, [reviewPath, worldId, reviewId, auth.status]);

  useEffect(() => {
    if (!region || !sourceKey || source?.key === sourceKey) return;
    const abort = new AbortController();
    setSourceError("");
    void (async () => {
      try {
        const { response } = await authenticatedApiFetch(sourcePath + "/open", {
          method: "POST", body: JSON.stringify(region), signal: abort.signal,
        });
        if (!response.ok) throw new Error();
        const file = new File([await response.blob()], "Source PDF", { type: "application/pdf" });
        if (!abort.signal.aborted) setSource({ key: sourceKey, file });
      } catch {
        if (!abort.signal.aborted) setSourceError("Could not open the retained PDF.");
      }
    })();
    return () => abort.abort();
  }, [region, sourceKey, source, sourcePath]);

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

  useEffect(() => {
    if (!editor || !review || published || pending) return;
    const abort = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const { response } = await authenticatedApiFetch("/api/live/statblock-definitions:validate", {
          method: "POST",
          signal: abort.signal,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ definition: editor.workingCopy }),
        });
        if (!response.ok) return;
        const result = await response.json();
        if (!abort.signal.aborted && result?.outcome === "success" && result.validation_receipt) {
          setIssues(result.validation_receipt.issues ?? []);
        }
      } catch {
        // Publish validates the saved revision even when background validation is unavailable.
      }
    }, 450);
    return () => {
      window.clearTimeout(timer);
      abort.abort();
    };
  }, [editor, review, published, pending]);

  const publishBlockers = editor && review ? [
    ...(getLocalFingerprint(editor) !== editor.baselineFingerprint ? ["Save your edits."] : []),
    ...issues.filter(issue => issue.severity === "error"),
  ] : [];

  function issueTarget(path: string | null | undefined) {
    const match = /^rule_elements\[(\d+)\]/.exec(path ?? "");
    const rule = match && editor?.workingCopy.rule_elements[Number(match[1])];
    if (rule) return `pdf-review-rule-${rule.key}`;
    if (path === "challenge.proficiency_bonus") return "pdf-review-proficiency";
    if (path?.startsWith("vitality.hit_points")) return "pdf-review-hp";
    return "pdf-review-fields";
  }

  function focusIssue(target: string, path?: string | null, code?: string) {
    const timing = path?.endsWith(".activation") || path?.endsWith(".activation.timing_text");
    const timingControl = timing && document.getElementById(target)?.querySelector<HTMLElement>("[data-lair-timing]");
    const manualControl = code === "LEGENDARY_RESOURCE_REQUIRED" &&
      document.getElementById(target)?.querySelector<HTMLElement>("[data-legendary-manual]");
    const referenceControl = Array.from(
      document.getElementById(target)?.querySelectorAll<HTMLElement>("[data-reference-path]") ?? [],
    ).find(control => control.dataset.referencePath === path);
    const structuredRule = target.startsWith("pdf-review-rule-") && !path?.endsWith(".rules_text") && !timingControl && !manualControl && !referenceControl;
    if (structuredRule) target = target.replace("pdf-review-rule-", "pdf-review-validation-rule-");
    const element = document.getElementById(target);
    if (!element) return;
    for (let parent: HTMLElement | null = element; parent; parent = parent.parentElement) {
      if (parent instanceof HTMLDetailsElement) parent.open = true;
    }
    const control = referenceControl || manualControl || timingControl || (element.querySelector<HTMLElement>("input, textarea, summary") ?? element);
    control.focus();
    control.scrollIntoView?.({ block: "nearest" });
  }

  function fieldIssues(target: string) {
    const messages = issues.filter(issue => issueTarget(issue.field_path) === target);
    return messages.length > 0 && <ul aria-label="Validation messages">
      {messages.map((issue, index) => <li key={index}>{issue.message}</li>)}
    </ul>;
  }

  function commitEdit(state: StatblockEditorState<EditableStatblockOutput>) {
    setEditor(state);
    setSaved(false);
    setValidation("");
    setIssues([]);
  }

  const toolbar = (
      <header className="pdf-statblock-review__toolbar">
        <h1>PDF statblock review</h1>
        <button type="button" disabled={pending} onClick={() => {
          const dirty = editor && getLocalFingerprint(editor) !== editor.baselineFingerprint;
          if (!dirty || window.confirm("Leave without saving your statblock edits?")) {
            window.location.assign(returnToBuild.href);
          }
        }}>Back to Build</button>
        <button type="button" aria-expanded={!sourceHidden} onClick={() => setSourceHidden(hidden => !hidden)}>
          {sourceHidden ? "Show PDF" : "Hide PDF"}
        </button>
        {editor && <button type="button" disabled={pending} onClick={() => void save()}>Save review draft</button>}
        {saved && <span role="status">Draft saved</span>}
        {editor && review && <button type="button" disabled={pending || published || publishBlockers.length > 0}
          onClick={() => void acceptMechanics(true)}>Publish</button>}
        {published && <>
          <span role="status">Creature and statblock published</span>
          <a href={publishedLink}>Open published statblock</a>
        </>}
      {!published && publishBlockers.length > 0 && <details className="pdf-statblock-review__blockers">
        <summary>Publication blockers ({publishBlockers.length})</summary>
        <ul aria-label="What blocks publication">
        {publishBlockers.map((blocker, index) => <li key={index}>
          {typeof blocker === "string" ? blocker :
            <button type="button" onClick={event => {
              const disclosure = event.currentTarget.closest("details");
              if (disclosure) disclosure.open = false;
              focusIssue(issueTarget(blocker.field_path), blocker.field_path, blocker.code);
            }}>
              {blocker.message}
            </button>}
        </li>)}
        </ul>
      </details>}
        <div className="pdf-statblock-review__source-tools" role="group" aria-label="PDF tools" hidden={sourceHidden}>
          {(review?.regions.length ?? 0) > 0 && <select aria-label="Source region" defaultValue=""
            onChange={event => {
              const locator = review?.regions[Number(event.currentTarget.value)];
              if (!locator) return;
              setRegion({ ...locator });
              setRegionSelection(current => current + 1);
              event.currentTarget.value = "";
            }}>
            <option value="">Source region</option>
            {review?.regions.map((locator, index) => (
              <option key={index} value={index}>Region {index + 1} · Page {locator.page}</option>
            ))}
          </select>}
          <div className="pdf-statblock-review__source-tools" ref={setNavigationHost} />
        </div>
      </header>
  );

  return (
    <section className="pdf-statblock-review" aria-label="PDF statblock review">
      {toolbarHost ? createPortal(toolbar, toolbarHost) : toolbar}
      {error && <p role="alert">{error}</p>}
      {!review && !error && <p role="status">Opening review…</p>}
      <BuildSourceWorkspace sourceHidden={sourceHidden} source={<>
        {sourceError ? <p role="alert">{sourceError}</p>
          : region && source && source.key === sourceKey
            ? <PdfPages key={regionSelection} file={source.file} restored={region} readOnly navigationHost={navigationHost} />
            : region && <p role="status">Opening source PDF…</p>}
      </>}>
      {editor && !editor.workingCopy.movement && <form onSubmit={event => {
        event.preventDefault();
        if (pending) return;
        const speed = new FormData(event.currentTarget).get("walkSpeed");
        if (typeof speed !== "string" || !/^\d+$/.test(speed) || !Number.isSafeInteger(Number(speed))) return;
        setEditor(updateWorkingCopy(editor, current => ({ ...current, movement: { modes: [{
          key: "walk", mode: "walk" as const, distance: { unit: "feet" as const, value: Number(speed) },
        }] } })));
        setSaved(false);
        setIssues([]);
        setValidation("");
      }}>
        <p>Movement is unspecified. You can publish with movement unspecified.</p>
        <label>Walking speed (feet)
          <input disabled={pending} name="walkSpeed" type="number" min="0" step="1" required />
        </label>
        <button disabled={pending} type="submit">Set walking speed</button>
      </form>}
      {review && editor && <>
        <StatblockRenderer chrome="campaign" draft={{
          definition: editor.workingCopy,
          portrait: review.artwork && <figure className="statblock-renderer-portrait">
            <img src={`data:image/jpeg;base64,${review.artwork.jpeg_base64}`}
              alt={`Artwork of ${editor.workingCopy.identity.name} from the source PDF`} />
          </figure>,
          hitPoints: summary => <details id="pdf-review-hp">
            <summary>{summary}</summary>
            <form onSubmit={event => {
              event.preventDefault();
              const input = event.currentTarget.elements.namedItem("maximum");
              if (pending || !(input instanceof HTMLInputElement)) return;
              const value = input.valueAsNumber;
              if (Number.isSafeInteger(value) && value > 0) commitEdit(setHitPointsMax(editor, value));
            }}>
              <label>Maximum hit points
                <input key={readHitPointsMax(editor.workingCopy.vitality.hit_points)}
                  name="maximum" type="number" min="1" max={Number.MAX_SAFE_INTEGER}
                  step="1" required disabled={pending}
                  defaultValue={readHitPointsMax(editor.workingCopy.vitality.hit_points)} />
              </label>
              <button type="submit" disabled={pending}>Apply hit points</button>
            </form>
            {fieldIssues("pdf-review-hp")}
          </details>,
          ruleEditor: (key, name) => <>
            <details id={`pdf-review-rule-${key}`}>
            <summary>Edit {name}</summary>
            <label>{name} rules text
              <textarea disabled={pending}
                value={editor.workingCopy.rule_elements.find(element => element.key === key)?.rules_text ?? ""}
                onChange={event => commitEdit(setRuleElementRulesText(editor, key, event.currentTarget.value))} />
            </label>
              {editor.workingCopy.rule_elements.find(element => element.key === key)?.activation.kind === "lair_initiative" &&
                <label>{name} initiative timing
                  <input data-lair-timing disabled={pending}
                    value={editor.workingCopy.rule_elements.find(element => element.key === key)?.activation.timing_text ?? ""}
                    onChange={event => {
                      const value = event.currentTarget.value;
                      const timing = value.trim() ? value : null;
                      commitEdit(updateWorkingCopy(editor, current => ({
                        ...current,
                        rule_elements: current.rule_elements.map(element => element.key === key
                          ? { ...element, activation: { ...element.activation, timing_text: timing } }
                          : element),
                      })));
                    }} />
                </label>}
              {issues.some(issue => issue.code === "LEGENDARY_RESOURCE_REQUIRED" &&
                issueTarget(issue.field_path) === `pdf-review-rule-${key}`) &&
                <button type="button" data-legendary-manual disabled={pending} onClick={() => {
                  if (!window.confirm(`Use ${name} as a manual rule? This keeps its printed text and replaces its automated mechanics and costs.`)) return;
                  commitEdit(updateWorkingCopy(editor, current => ({
                    ...current,
                    rule_elements: current.rule_elements.map(element => element.key === key
                      ? { ...element, mechanic: { kind: "human_adjudicated" }, automation_support: "manual",
                        costs: [], usage: { kind: "manual", uses: null, resource_key: null } }
                      : element),
                  })));
                }}>Use {name} as a manual rule</button>}
              {issues.filter(issue => issueTarget(issue.field_path) === `pdf-review-rule-${key}`).map(issue => {
                const phase = /^rule_elements\[\d+\]\.mechanic\.effects\[(\d+)\]\.phase_key$/.exec(issue.field_path ?? "");
                const sequence = /^rule_elements\[\d+\]\.mechanic\.sequences\[(\d+)\]\.element_key$/.exec(issue.field_path ?? "");
                if (issue.code === "UNKNOWN_PHASE_REFERENCE" && phase) return <button key={issue.field_path}
                  type="button" data-reference-path={issue.field_path} disabled={pending} onClick={() => {
                    if (!window.confirm("Remove the unresolved phase effect? The rule text will be kept.")) return;
                    commitEdit(updateWorkingCopy(editor, current => ({
                      ...current,
                      rule_elements: current.rule_elements.map(element => {
                        if (element.key !== key || !("effects" in element.mechanic)) return element;
                        return { ...element, mechanic: { ...element.mechanic,
                          effects: element.mechanic.effects?.filter((_, index) => index !== Number(phase[1])) } };
                      }),
                    })));
                  }}>Remove unresolved phase effect from {name}</button>;
                if (issue.code !== "UNKNOWN_MULTIATTACK_ELEMENT" || !sequence) return null;
                return <label key={issue.field_path}>Replacement rule for {name}
                  <select data-reference-path={issue.field_path} disabled={pending} value="" onChange={event => {
                    const replacement = event.currentTarget.value;
                    commitEdit(updateWorkingCopy(editor, current => ({
                      ...current,
                      rule_elements: current.rule_elements.map(element => {
                        if (element.key !== key || !("sequences" in element.mechanic)) return element;
                        return { ...element, mechanic: { ...element.mechanic,
                          sequences: element.mechanic.sequences.map((entry, index) =>
                            index === Number(sequence[1]) ? { ...entry, element_key: replacement } : entry) } };
                      }),
                    })));
                  }}>
                    <option value="" disabled>Select a rule</option>
                    {editor.workingCopy.rule_elements.filter(element =>
                      element.key !== key && !("sequences" in element.mechanic)).map(element =>
                        <option key={element.key} value={element.key}>{element.name}</option>)}
                  </select>
                </label>;
              })}
            </details>
            <div id={`pdf-review-validation-rule-${key}`} tabIndex={-1}>
              {fieldIssues(`pdf-review-rule-${key}`)}
              {issues.some(issue => issueTarget(issue.field_path) === `pdf-review-rule-${key}` &&
                !issue.field_path?.endsWith(".rules_text")) &&
                <p>These messages concern structured mechanics. <button type="button" onClick={() => focusIssue("pdf-review-fields")}>Open more statblock fields</button></p>}
            </div>
          </>,
        }} />
        <details>
          <summary id="pdf-review-fields">More statblock fields</summary>
        <fieldset disabled={pending}>
          <label>D&D edition
            <select value={editor.workingCopy.ruleset?.edition ?? ""} onChange={event => {
              const edition = event.currentTarget.value;
              if (edition !== "" && edition !== "2014" && edition !== "2024") return;
              setEditor(updateWorkingCopy(editor, current => ({
                ...current, ruleset: edition ? { ...current.ruleset, system: "dnd5e", edition } : null,
              })));
              setSaved(false);
              setValidation("");
              setIssues([]);
            }}>
              <option value="">Unspecified in source</option>
              <option value="2014">2014</option>
              <option value="2024">2024</option>
            </select>
          </label>
          <label>Proficiency bonus
            <input id="pdf-review-proficiency" type="number" min="0" step="1" placeholder="0"
              aria-invalid={issues.some(issue => issue.field_path === "challenge.proficiency_bonus" && issue.severity === "error")}
              value={editor.workingCopy.challenge.proficiency_bonus ?? ""}
              onChange={event => {
                const value = event.currentTarget.valueAsNumber;
                if (event.currentTarget.value !== "" && (!Number.isSafeInteger(value) || value < 0)) return;
                setEditor(updateWorkingCopy(editor, current => ({
                  ...current, challenge: { ...current.challenge, proficiency_bonus: Number.isNaN(value) ? null : value },
                })));
                setSaved(false);
                setValidation("");
                setIssues([]);
              }} />
          </label>
          {fieldIssues("pdf-review-proficiency")}
          {issues.some(issue => issueTarget(issue.field_path) === "pdf-review-fields") && <ul aria-label="Mechanics validation issues">
            {issues.filter(issue => issueTarget(issue.field_path) === "pdf-review-fields").map((issue, index) => (
              <li key={index}>
                <strong>{issue.severity}</strong> {issue.message}
                {issue.field_path && <div><code>{issue.field_path}</code></div>}
                {issue.suggested_resolution && <div>{issue.suggested_resolution}</div>}
              </li>
            ))}
          </ul>}
          {editor.workingCopy.movement && <button type="button" onClick={() => {
            setEditor(updateWorkingCopy(editor, current => ({ ...current, movement: null })));
            setSaved(false);
            setValidation("");
            setIssues([]);
          }}>Mark movement unspecified</button>}
          {auth.status !== "authenticated" && <button type="button" aria-expanded={developerTools}
            onClick={() => setDeveloperTools(!developerTools)}>Developer tools</button>}
          {auth.status !== "authenticated" && developerTools && <section aria-label="Developer tools">
            <button type="button" disabled={!mechanicsResolved} onClick={() => void validate()}>Validate mechanics</button>
            {validation && <span role="status">{validation}</span>}
            <button type="button" disabled={!mechanicsResolved || createInFlight || getLocalFingerprint(editor) !== editor.baselineFingerprint}
              onClick={() => void createDraft()}>Create creature draft from review</button>
            {!acceptOpen && <button type="button" disabled={!mechanicsResolved} onClick={() => void openAcceptance()}>Choose creature draft</button>}
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
                <button type="button" disabled={!mechanicsResolved || !parentId || getLocalFingerprint(editor) !== editor.baselineFingerprint}
                  onClick={() => void appendMechanics()}>Append mechanics revision</button>
              </> : null}
              {(selectedDraft?.workflow_state !== "mechanics_saved" || hasInitialAttempt) &&
                <button type="button" disabled={!mechanicsResolved || !draftId || getLocalFingerprint(editor) !== editor.baselineFingerprint}
                onClick={() => void acceptMechanics()}>{selectedDraft?.workflow_state === "mechanics_saved" ? "Recover initial acceptance" : "Accept mechanics"}</button>}
              {acceptedLink && <a href={acceptedLink}>Open accepted statblock</a>}
            </>}
          </section>}
          <StatblockDefinitionEditor editRuleMechanics output={review.definition} editorState={editor}
            onEditorStateChange={commitEdit}
            recoveryHint="Save the review draft to keep your edits." />
        </fieldset>
        </details>
      </>}
      </BuildSourceWorkspace>
    </section>
  );
}
