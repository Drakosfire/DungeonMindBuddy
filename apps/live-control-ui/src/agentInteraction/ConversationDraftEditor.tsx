import { useEffect, useId, useRef, useState } from "react";
import {
  openConversationDraft,
  openConversationVariantApproval,
  openVariantReview,
  confirmVariantReview,
  correctVariantReview,
  type VariantTextReplacement,
  type VariantRuleField,
  type ConversationVariantReview,
  saveConversationDraft,
  type ConversationDraft,
  type ConversationDraftScope,
} from "../api/conversationDraftApi";

import type { BuildComposeBridge, PreparedBuildProposal } from "../buildSurface/buildComposeBridge";
import { savedConversationVariantHref } from "../statblocks/savedStatblockLocation";
import { StatblockRenderer } from "../statblocks/render/StatblockRenderer";

interface VariantPagePlacement {
  documentId: string;
  bridge: BuildComposeBridge;
}

interface ApprovalTarget {
  scope: ConversationDraftScope;
  reviewId: string;
  revision: number;
}

async function loadReviewedDraft(target: ApprovalTarget) {
  const draft = await openConversationDraft(target.scope);
  if (draft.revision !== target.revision || !draft.variant_review_ids?.includes(target.reviewId)) {
    throw new Error("The reviewed draft changed. Reopen the latest draft before saving.");
  }
  const data = await openVariantReview(target.scope, target.reviewId);
  if (data.revision !== target.revision) throw new Error("The statblock review changed.");
  return { draft, review: { id: target.reviewId, data } };
}

export function ConversationVariantApproval({ scope, placement }: {
  scope: ConversationDraftScope;
  placement?: VariantPagePlacement;
}) {
  const [opened, setOpened] = useState<(Awaited<ReturnType<typeof loadReviewedDraft>> & { target: ApprovalTarget }) | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function open() {
    setBusy(true);
    setError("");
    try {
      const target = await openConversationVariantApproval(scope);
      setOpened({ target, ...await loadReviewedDraft(target) });
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not find the reviewed variant.");
    } finally {
      setBusy(false);
    }
  }

  return opened ? <ConversationDraftEditor scope={opened.target.scope} placement={placement} initialReview={opened} /> :
    <section aria-label="Variant approval">
      <button type="button" disabled={busy} onClick={() => void open()}>Find reviewed statblock</button>
      {error && <p role="alert">{error}</p>}
    </section>;
}

function VariantCorrectionFields({ name, rules, busy, onStage, onDirty }: {
  name: string;
  rules: ConversationVariantReview["definition"]["rule_elements"];
  busy: boolean;
  onStage: (replacements: VariantTextReplacement[]) => void;
  onDirty: (dirty: boolean) => void;
}) {
  const [selected, setSelected] = useState(rules[0]?.key ?? "");
  const [edits, setEdits] = useState<Record<string, VariantTextReplacement>>({});
  const [revisedName, setRevisedName] = useState(name);
  const nameChanged = revisedName.trim() !== name;
  const dirty = nameChanged || Object.keys(edits).length > 0;
  useEffect(() => { onDirty(dirty); return () => onDirty(false); }, [dirty, onDirty]);
  const rule = rules.find(item => item.key === selected);
  const slots: [VariantRuleField, string, string | null | undefined][] = rule ? [
    ["rules_text", "Rule text", rule.rules_text],
    ["timing_text", "Timing", rule.activation.timing_text],
    ["condition_text", "Trigger condition", rule.activation.trigger?.condition_text],
  ] : [];
  return <details>
    <summary>Correct reviewed rules</summary>
    <label>Statblock name <input disabled={busy} value={revisedName}
      onChange={event => setRevisedName(event.target.value)} /></label>
    {rule && <label>Rule <select value={selected} disabled={busy} onChange={event => setSelected(event.target.value)}>
      {rules.map(item => <option key={item.key} value={item.key}>{item.name}</option>)}
    </select></label>}
    {slots.map(([field, label, value]) => {
      if (!rule || !value) return null;
      const key = rule.key + ":" + field;
      return <label key={key}>{label}
        <textarea disabled={busy} value={edits[key]?.with_text ?? value} onChange={event => {
          const revised = event.target.value;
          setEdits(previous => {
            const next = { ...previous };
            if (revised === value) delete next[key];
            else next[key] = { rule_key: rule.key, field, replace_exact: value, with_text: revised };
            return next;
          });
        }} />
      </label>;
    })}
    <button type="button"
      disabled={busy || !dirty || !revisedName.trim() || Object.values(edits).some(edit => !edit.with_text.trim())}
      onClick={() => onStage([
        ...(nameChanged ? [{field: "name" as const, replace_exact: name, with_text: revisedName}] : []),
        ...Object.values(edits),
      ])}>Stage corrected review</button>
    {dirty && <button type="button" disabled={busy} onClick={() => {
      setRevisedName(name);
      setEdits({});
    }}>Discard corrections</button>}
  </details>;
}

export function ConversationDraftEditor({ scope, placement, initialReview }: {
  scope: ConversationDraftScope;
  placement?: VariantPagePlacement;
  initialReview?: Awaited<ReturnType<typeof loadReviewedDraft>> & { target: ApprovalTarget };
}) {
  const id = useId();
  const [correctionDirty, setCorrectionDirty] = useState(false);
  const [approvalTarget, setApprovalTarget] = useState(initialReview?.target);
  const [draft, setDraft] = useState<ConversationDraft | null>(initialReview?.draft ?? null);
  const [markdown, setMarkdown] = useState(initialReview?.draft.markdown ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [review, setReview] = useState<{ id: string; data: ConversationVariantReview } | null>(initialReview?.review ?? null);
  const [savedVariant, setSavedVariant] = useState(initialReview?.review.data.saved === true);

  const pendingPlacement = useRef<{ href: string; prepared: PreparedBuildProposal } | null>(null);
  const [linkedHref, setLinkedHref] = useState<string | null>(null);

  async function saveVariantLink(reviewId: string) {
    if (!placement?.bridge.placeSavedVariantLink) return;
    const variant = { ...scope, reviewId };
    const href = savedConversationVariantHref(variant);
    const { bridge, documentId } = placement;
    setBusy(true);
    setError("");
    try {
      const pending = pendingPlacement.current;
      if (pending && pending.href !== href) {
        throw new Error("Finish saving the previous variant link first.");
      }
      let prepared = pending?.prepared;
      if (!prepared) {
        const captured = await bridge.capture();
        if (captured.basis.document_id !== documentId || captured.basis.world_id !== scope.worldId) {
          throw new Error("Open the original Build page before linking the variant.");
        }
        prepared = await bridge.placeSavedVariantLink!(captured, variant);
        pendingPlacement.current = { href, prepared };
      }
      await bridge.saveProposal(
        prepared.captured.basis, prepared.afterEditorSha256, prepared.afterDraftSha256,
      );
      pendingPlacement.current = null;
      setLinkedHref(href);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not save the variant link.");
    } finally {
      setBusy(false);
    }
  }

  async function inspectVariant(reviewId: string) {
    setBusy(true);
    setError("");
    setSavedVariant(false);
    setReview(null);
    try {
      const data = await openVariantReview(scope, reviewId);
      if (data.revision !== draft?.revision) throw new Error("Reopen the latest draft before reviewing.");
      setReview({ id: reviewId, data });
      setSavedVariant(data.saved === true);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not open the variant review.");
    } finally {
      setBusy(false);
    }
  }

  async function correctVariant(replacements: VariantTextReplacement[]) {
    if (!draft || !review || savedVariant || markdown !== draft.markdown) return;
    setBusy(true);
    setError("");
    try {
      const corrected = await correctVariantReview(scope, review.id, draft.revision, replacements);
      setReview(null);
      const target = { scope, reviewId: corrected.review_id, revision: corrected.revision };
      if (approvalTarget) setApprovalTarget(target);
      const next = await loadReviewedDraft(target);
      setDraft(next.draft);
      setMarkdown(next.draft.markdown);
      setReview(next.review);
      setSavedVariant(next.review.data.saved === true);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not stage the corrected review.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmVariant() {
    if (!draft || !review || correctionDirty || markdown !== draft.markdown) return;
    setBusy(true);
    setError("");
    try {
      await confirmVariantReview(scope, review.id);
      setSavedVariant(true);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not save the variant.");
    } finally {
      setBusy(false);
    }
  }

  async function open(reopenProducer = false) {
    setReview(null);
    setSavedVariant(false);
    setBusy(true);
    setError("");
    try {
      if (approvalTarget && !reopenProducer) {
        const latest = await loadReviewedDraft(approvalTarget);
        setDraft(latest.draft);
        setMarkdown(latest.draft.markdown);
        setReview(latest.review);
        setSavedVariant(latest.review.data.saved === true);
      } else {
        const latest = await openConversationDraft(scope);
        if (reopenProducer) setApprovalTarget(undefined);
        setDraft(latest);
        setMarkdown(latest.markdown);
      }
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not open the draft.");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!draft) return;
    setReview(null);
    setSavedVariant(false);
    setBusy(true);
    setError("");
    try {
      const saved = await saveConversationDraft(scope, draft.revision, markdown);
      setDraft(saved);
      setMarkdown(saved.markdown);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not save the draft.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Conversation draft">
      {draft ? (
        <>
          <label htmlFor={id}>Draft Markdown</label>
          <textarea id={id} value={markdown} disabled={busy} onChange={event => setMarkdown(event.target.value)} />
          <button type="button" disabled={busy || markdown === draft.markdown} onClick={() => void save()}>
            Save draft
          </button>
          {!approvalTarget && markdown === draft.markdown && draft.variant_review_ids?.map(reviewId => (
            <button key={reviewId} type="button" disabled={busy} onClick={() => void inspectVariant(reviewId)}>
              Review statblock variant
            </button>
          ))}
          {review && markdown === draft.markdown && (
            <section aria-label="Statblock variant review">
              <StatblockRenderer chrome="campaign" draft={{
                definition: review.data.definition,
                hitPoints: summary => summary,
                ruleEditor: () => null,
              }} />
              {!savedVariant &&
                <VariantCorrectionFields key={review.id} name={review.data.definition.identity.name} rules={review.data.definition.rule_elements ?? []}
                  busy={busy} onDirty={setCorrectionDirty} onStage={replacements => void correctVariant(replacements)} />}
              <button type="button" disabled={busy || savedVariant || correctionDirty} onClick={() => void confirmVariant()}>
                Confirm and save as new statblock
              </button>
              {savedVariant && <>
                <p role="status">Statblock variant saved.</p>
                <a href={savedConversationVariantHref({ ...scope, reviewId: review.id })}>Open saved variant</a>
                {placement?.bridge.placeSavedVariantLink && <button type="button" disabled={busy || linkedHref === savedConversationVariantHref({ ...scope, reviewId: review.id })}
                  onClick={() => void saveVariantLink(review.id)}>
                  Insert at cursor and save page
                </button>}
                {linkedHref === savedConversationVariantHref({ ...scope, reviewId: review.id }) &&
                  <p role="status">Variant link verified on the saved page.</p>}
              </>}
            </section>
          )}
          {error && (
            <button type="button" disabled={busy} onClick={() => void open(Boolean(approvalTarget))}>
              {approvalTarget ? "Open latest draft for review" : "Discard local edits and reopen"}
            </button>
          )}
        </>
      ) : (
        <button type="button" disabled={busy} onClick={() => void open()}>
          Open draft
        </button>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
