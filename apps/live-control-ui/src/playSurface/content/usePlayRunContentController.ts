import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getWorldPlayRunContent, getWorldPlayRunContentCommand, putWorldPlayRunContentCommand } from "../../api/playRunContentApi";
import { LiveApiError } from "../../api/liveApi";
import type { PlayRunContent, PlayRunContentCommitRequest, PlayRunContentReceipt } from "../playRunContentTypes";
import {
  hasPlayRunContentJournal,
  readPlayRunContentJournalRaw,
  removePlayRunContentJournalIfUnchanged,
  validatePlayRunContentJournal,
  writePlayRunContentJournal,
  type PendingPlayRunContentCommand,
  type PlayRunContentIdentity,
  type PlayRunContentJournal,
} from "./playRunContentJournal";
import { samePlayRunContentOrigin, validatePlayRunContentReceipt } from "./playRunContentProtocol";

export type PlayRunContentSaveState = "saved" | "dirty" | "saving" | "recovering" | "unknown" | "conflict" | "invalid" | "rejected" | "storage-error";

export interface PlayRunContentControllerState {
  accepted: PlayRunContent;
  draftMarkdown: string;
  draftGeneration: number;
  saveState: PlayRunContentSaveState;
  message: string | null;
  latestRemote: PlayRunContent | null;
  serializationIssues: string[];
  savedAt: string | null;
  editorRevision: number;
}

export interface PlayRunContentController {
  state: PlayRunContentControllerState;
  hasUnsubmittedContent: boolean;
  changeDraft: (markdown: string, issues?: string[]) => void;
  retryRecovery: () => void;
  reviewLatest: () => void;
  useLatestDiscardingDraft: () => void;
  keepDraftOnLatest: () => void;
  resetDraftFromAccepted: () => void;
}

const DEBOUNCE_MS = 650;
const uuid = (): string => crypto.randomUUID();
const isUnknownTransport = (error: unknown): boolean => !(error instanceof LiveApiError) || error.status === 0 || error.status >= 500;

export function playRunContentIdentity(content: PlayRunContent): PlayRunContentIdentity {
  return { worldId: content.world_id, runId: content.run_id, origin: content.origin };
}

export function hasUnsubmittedPlayRunContent(content: PlayRunContent): boolean {
  try { return hasPlayRunContentJournal(playRunContentIdentity(content)); }
  catch { return true; }
}

function initialState(content: PlayRunContent, raw: string | null, storageFailed: boolean): PlayRunContentControllerState {
  return {
    accepted: content,
    draftMarkdown: content.markdown,
    draftGeneration: 0,
    saveState: storageFailed ? "storage-error" : raw === null ? "saved" : "recovering",
    message: storageFailed ? "Browser storage is unavailable. Draft recovery cannot be guaranteed." : null,
    latestRemote: null,
    serializationIssues: [],
    savedAt: raw === null ? content.committed_at : null,
    editorRevision: 0,
  };
}

function acceptedFromReceipt(base: PlayRunContent, receipt: PlayRunContentReceipt, markdown: string): PlayRunContent {
  return {
    ...base,
    source: "edition",
    edition_revision: receipt.accepted_edition_revision,
    edition_revision_id: receipt.accepted_edition_revision_id,
    markdown,
    content_sha256: receipt.accepted_content_sha256,
    committed_at: receipt.committed_at,
    observed_run_revision: receipt.observed_run_revision,
  };
}

function requestFor(accepted: PlayRunContent, markdown: string): PlayRunContentCommitRequest {
  return {
    schema_version: "dmb_world_play_run_content_commit_v1",
    expected_origin: accepted.origin,
    expected_edition_revision: accepted.edition_revision,
    expected_content_sha256: accepted.content_sha256,
    markdown,
  };
}

function sameBase(a: PlayRunContent, b: PlayRunContent): boolean {
  return a.edition_revision === b.edition_revision && a.content_sha256 === b.content_sha256
    && samePlayRunContentOrigin(a.origin, b.origin);
}

export function usePlayRunContentController(
  initialContent: PlayRunContent,
  onAcceptedContent: (content: PlayRunContent) => void,
  onUnsubmittedChange: (hasUnsubmitted: boolean) => void,
): PlayRunContentController {
  const identity = useMemo(() => playRunContentIdentity(initialContent), [initialContent.world_id, initialContent.run_id,
    initialContent.origin.playable_artifact_id, initialContent.origin.playable_revision,
    initialContent.origin.playable_work_revision_id, initialContent.origin.playable_content_sha256]);
  const initialRawRef = useRef<string | null | undefined>(undefined);
  const storageFailedRef = useRef(false);
  if (initialRawRef.current === undefined) {
    try { initialRawRef.current = readPlayRunContentJournalRaw(identity); }
    catch { initialRawRef.current = null; storageFailedRef.current = true; }
  }
  const [state, setState] = useState(() => initialState(initialContent, initialRawRef.current ?? null, storageFailedRef.current));
  const stateRef = useRef(state);
  const journalRawRef = useRef(initialRawRef.current ?? null);
  const pendingRef = useRef<PendingPlayRunContentCommand | null>(null);
  const inFlightRef = useRef(false);
  const activeRef = useRef(true);
  const recoveryStartedRef = useRef(false);
  const timerRef = useRef<number | null>(null);

  const publish = useCallback((next: PlayRunContentControllerState) => {
    stateRef.current = next;
    if (activeRef.current) setState(next);
    const unsubmitted = next.saveState !== "saved" || next.draftMarkdown !== next.accepted.markdown || pendingRef.current !== null;
    if (activeRef.current) onUnsubmittedChange(unsubmitted);
  }, [onUnsubmittedChange]);

  const journalFor = useCallback((next: PlayRunContentControllerState, pending: PendingPlayRunContentCommand | null): PlayRunContentJournal => ({
    schema_version: "dmb_play_run_content_journal_v1",
    identity,
    accepted: next.accepted,
    draft_markdown: next.draftMarkdown,
    draft_generation: next.draftGeneration,
    pending,
  }), [identity]);

  const persist = useCallback((next: PlayRunContentControllerState, pending: PendingPlayRunContentCommand | null): boolean => {
    try {
      const currentRaw = readPlayRunContentJournalRaw(identity);
      if (currentRaw !== journalRawRef.current) {
        throw new Error("Another open Play tab changed this session-copy recovery journal.");
      }
      if (next.draftMarkdown === next.accepted.markdown && pending === null) {
        if (currentRaw !== null && !removePlayRunContentJournalIfUnchanged(identity, currentRaw)) {
          throw new Error("Another open Play tab changed this session copy while clearing recovery data.");
        }
        journalRawRef.current = null;
        pendingRef.current = null;
        return true;
      }
      journalRawRef.current = writePlayRunContentJournal(identity, journalFor(next, pending));
      pendingRef.current = pending;
      return true;
    } catch (error) {
      publish({ ...next, saveState: "storage-error", message: error instanceof Error ? error.message : "Browser storage could not save session-copy recovery data." });
      return false;
    }
  }, [identity, journalFor, publish]);

  const applyAcknowledgedReceipt = useCallback(async (receipt: PlayRunContentReceipt, pending: PendingPlayRunContentCommand) => {
    if (!activeRef.current) return;
    const current = stateRef.current;
    const receiptContent = acceptedFromReceipt(current.accepted, receipt, pending.request.markdown);
    let latest = receiptContent;
    try {
      const read = await getWorldPlayRunContent(identity.runId, identity.worldId);
      if (!samePlayRunContentOrigin(read.origin, identity.origin)) throw new TypeError("Latest session copy returned a different original pin.");
      if (read.edition_revision >= receipt.accepted_edition_revision) latest = read;
    } catch {
      // The validated receipt is durable confirmation even if the follow-up read is unavailable.
    }
    if (!activeRef.current) return;
    const freshest = stateRef.current;
    const newerRemote = latest.edition_revision > receipt.accepted_edition_revision;
    const sameDraft = freshest.draftGeneration === pending.draftGeneration && freshest.draftMarkdown === pending.request.markdown;
    const next: PlayRunContentControllerState = {
      ...freshest,
      accepted: latest,
      savedAt: receipt.committed_at,
      latestRemote: newerRemote ? latest : null,
      saveState: newerRemote ? "conflict" : sameDraft ? "saved" : freshest.serializationIssues.length ? "invalid" : "dirty",
      message: newerRemote
        ? "A later session-copy revision exists. Review it before saving again."
        : sameDraft ? null : freshest.serializationIssues.length ? "Fix the Markdown that could not be saved safely." : null,
    };
    if (!persist(next, null)) return;
    if (sameDraft && !newerRemote) {
      const serialized = journalRawRef.current;
      if (serialized !== null) {
        try { removePlayRunContentJournalIfUnchanged(identity, serialized); journalRawRef.current = null; } catch { /* status below remains server-confirmed */ }
      }
    }
    publish(next);
    onAcceptedContent(latest);
  }, [identity, onAcceptedContent, persist, publish]);

  const markKnownFailure = useCallback(async (error: unknown, pending: PendingPlayRunContentCommand, base: PlayRunContent) => {
    if (!activeRef.current) return;
    const current = stateRef.current;
    const isConflict = error instanceof LiveApiError && error.status === 409;
    const isInvalid = error instanceof LiveApiError && error.status === 422;
    const isTooLarge = error instanceof LiveApiError && error.status === 413;
    if (isUnknownTransport(error) || !(isConflict || isInvalid || isTooLarge)) {
      const next = { ...current, saveState: "unknown" as const, message: "The save result is uncertain. Check the same command before another save." };
      if (!persist(next, pending)) return;
      publish(next);
      return;
    }
    const next = {
      ...current,
      saveState: isConflict ? "conflict" as const : isTooLarge ? "rejected" as const : "invalid" as const,
      message: error instanceof Error ? error.message : isConflict ? "The saved session changed elsewhere." : "The server rejected this session copy.",
      latestRemote: isConflict ? null : current.latestRemote,
    };
    pendingRef.current = null;
    if (!persist(next, null)) return;
    publish(next);
    if (isConflict) {
      try {
        const latest = await getWorldPlayRunContent(identity.runId, identity.worldId);
        if (activeRef.current && samePlayRunContentOrigin(latest.origin, base.origin)) {
          const conflict = { ...stateRef.current, saveState: "conflict" as const, latestRemote: latest };
          if (!persist(conflict, null)) return;
          publish(conflict);
        }
      } catch { /* Keep the explicit conflict state and draft visible for manual review. */ }
    }
  }, [identity, persist, publish]);

  const verifyAndApply = useCallback(async (raw: unknown, pending: PendingPlayRunContentCommand, accepted: PlayRunContent) => {
    const receipt = await validatePlayRunContentReceipt(raw, {
      worldId: identity.worldId,
      runId: identity.runId,
      commandId: pending.commandId,
      origin: identity.origin,
      request: pending.request,
    });
    if (!samePlayRunContentOrigin(receipt.origin, accepted.origin)) throw new TypeError("Save receipt original pin changed during the command.");
    await applyAcknowledgedReceipt(receipt, pending);
  }, [applyAcknowledgedReceipt, identity]);

  const reconcilePending = useCallback(async (pending: PendingPlayRunContentCommand, base: PlayRunContent) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    try {
      let raw: unknown;
      try {
        raw = await getWorldPlayRunContentCommand(identity.runId, identity.worldId, pending.commandId);
      } catch (error) {
        if (!(error instanceof LiveApiError) || error.status !== 404) throw error;
        raw = await putWorldPlayRunContentCommand(identity.runId, identity.worldId, pending.commandId, pending.request);
      }
      await verifyAndApply(raw, pending, base);
    } catch (error) {
      if (!activeRef.current) return;
      if (error instanceof LiveApiError && (error.status === 409 || error.status === 413 || error.status === 422)) {
        await markKnownFailure(error, pending, base);
        return;
      }
      const current = stateRef.current;
      const next = { ...current, saveState: "unknown" as const, message: error instanceof Error ? error.message : "The original save command is still unconfirmed." };
      if (!persist(next, pending)) return;
      publish(next);
    } finally { inFlightRef.current = false; }
  }, [identity, markKnownFailure, persist, publish, verifyAndApply]);

  const sendPending = useCallback(async (pending: PendingPlayRunContentCommand, base: PlayRunContent) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    try {
      const raw = await putWorldPlayRunContentCommand(identity.runId, identity.worldId, pending.commandId, pending.request);
      await verifyAndApply(raw, pending, base);
    } catch (error) {
      if (activeRef.current && error instanceof LiveApiError && (error.status === 409 || error.status === 413 || error.status === 422)) {
        await markKnownFailure(error, pending, base);
      } else if (activeRef.current) {
        const current = stateRef.current;
        const next = { ...current, saveState: "unknown" as const, message: "The save result is uncertain. Check the same command before another save." };
        if (!persist(next, pending)) return;
        publish(next);
      }
    } finally { inFlightRef.current = false; }
  }, [identity, markKnownFailure, persist, publish, verifyAndApply]);

  useEffect(() => {
    activeRef.current = true;
    return () => {
      activeRef.current = false;
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, []);

  useEffect(() => {
    const raw = initialRawRef.current;
    if (storageFailedRef.current || recoveryStartedRef.current) return;
    if (raw == null) return;
    recoveryStartedRef.current = true;
    let cancelled = false;
    void (async () => {
      try {
        const journal = await validatePlayRunContentJournal(raw, identity);
        if (cancelled || !activeRef.current) return;
        if (journal.pending) {
          const recovered = { ...stateRef.current, accepted: journal.accepted, draftMarkdown: journal.draft_markdown, draftGeneration: journal.draft_generation,
            editorRevision: journal.draft_markdown === stateRef.current.draftMarkdown ? stateRef.current.editorRevision : stateRef.current.editorRevision + 1,
            saveState: "recovering" as const, message: "Checking the exact saved command and restoring its draft." };
          journalRawRef.current = raw;
          pendingRef.current = journal.pending;
          publish(recovered);
          void reconcilePending(journal.pending, journal.accepted);
          return;
        }
        if (!sameBase(journal.accepted, initialContent)) {
          const conflict = { ...stateRef.current, draftMarkdown: journal.draft_markdown, draftGeneration: journal.draft_generation, editorRevision: stateRef.current.editorRevision + 1, saveState: "conflict" as const, latestRemote: initialContent, message: "A newer saved session copy exists. Review it before continuing this draft." };
          journalRawRef.current = raw;
          publish(conflict);
          return;
        }
        const recovered = { ...stateRef.current, accepted: journal.accepted, draftMarkdown: journal.draft_markdown, draftGeneration: journal.draft_generation,
          editorRevision: journal.draft_markdown === stateRef.current.draftMarkdown ? stateRef.current.editorRevision : stateRef.current.editorRevision + 1,
          saveState: journal.draft_markdown === journal.accepted.markdown ? "saved" as const : "dirty" as const,
          message: journal.draft_markdown === journal.accepted.markdown ? null : "Unsaved session-copy draft restored." };
        journalRawRef.current = raw;
        if (recovered.saveState === "saved") removePlayRunContentJournalIfUnchanged(identity, raw);
        publish(recovered);
      } catch (error) {
        if (!cancelled && activeRef.current) publish({ ...stateRef.current, saveState: "storage-error", message: error instanceof Error ? error.message : "Saved session-copy recovery could not be validated." });
      }
    })();
    return () => { cancelled = true; recoveryStartedRef.current = false; };
  }, [identity, initialContent, publish, reconcilePending]);

  useEffect(() => {
    if (state.saveState !== "dirty" || state.serializationIssues.length || pendingRef.current || inFlightRef.current) return;
    if (state.draftMarkdown === state.accepted.markdown) {
      const next = { ...state, saveState: "saved" as const, message: null, savedAt: state.accepted.committed_at };
      if (persist(next, null)) publish(next);
      return;
    }
    timerRef.current = window.setTimeout(() => {
      if (!activeRef.current || inFlightRef.current) return;
      const current = stateRef.current;
      if (current.saveState !== "dirty" || current.serializationIssues.length || pendingRef.current) return;
      const request = requestFor(current.accepted, current.draftMarkdown);
      const pending: PendingPlayRunContentCommand = { commandId: uuid(), draftGeneration: current.draftGeneration, request };
      const frozen = { ...current, saveState: "saving" as const, message: "Saving this session copy…" };
      if (!persist(frozen, pending)) return;
      publish(frozen);
      void sendPending(pending, current.accepted);
    }, DEBOUNCE_MS);
    return () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
      timerRef.current = null;
    };
  }, [identity, persist, publish, sendPending, state]);

  const changeDraft = useCallback((markdown: string, issues: string[] = []) => {
    const current = stateRef.current;
    if (markdown === current.draftMarkdown && JSON.stringify(issues) === JSON.stringify(current.serializationIssues)) return;
    const next = { ...current, draftMarkdown: markdown, draftGeneration: current.draftGeneration + 1,
      saveState: issues.length ? "invalid" as const
        : pendingRef.current ? current.saveState
          : current.saveState === "conflict" || current.saveState === "unknown" ? current.saveState : "dirty" as const,
      serializationIssues: issues,
      message: issues.length ? "This edit cannot be represented safely as Markdown." : null };
    if (!persist(next, pendingRef.current)) return;
    publish(next);
  }, [persist, publish]);

  const retryRecovery = useCallback(() => {
    const pending = pendingRef.current;
    if (pending) void reconcilePending(pending, stateRef.current.accepted);
  }, [reconcilePending]);

  const reviewLatest = useCallback(() => {
    const current = stateRef.current;
    publish({ ...current, saveState: "recovering", message: "Loading the latest saved session copy for review." });
    void getWorldPlayRunContent(identity.runId, identity.worldId).then(latest => {
      if (!activeRef.current) return;
      if (!samePlayRunContentOrigin(latest.origin, identity.origin)) throw new TypeError("Latest session copy belongs to another pinned source.");
      publish({ ...stateRef.current, saveState: "conflict", latestRemote: latest, message: "Review both versions, then choose which draft to continue." });
    }).catch(error => {
      if (activeRef.current) publish({ ...stateRef.current, saveState: "conflict", message: error instanceof Error ? error.message : "Latest session copy could not be loaded." });
    });
  }, [identity, publish]);

  const chooseLatest = useCallback((keepDraft: boolean) => {
    const current = stateRef.current;
    const latest = current.latestRemote;
    if (!latest) return;
    const next = keepDraft
      ? { ...current, accepted: latest, saveState: current.draftMarkdown === latest.markdown ? "saved" as const : "dirty" as const, latestRemote: null, message: keepDraft && current.draftMarkdown !== latest.markdown ? "Latest version reviewed. Your draft will save against that version." : null }
      : { ...current, accepted: latest, draftMarkdown: latest.markdown, draftGeneration: current.draftGeneration + 1, editorRevision: current.editorRevision + 1, saveState: "saved" as const, latestRemote: null, message: null, serializationIssues: [], savedAt: latest.committed_at };
    if (!persist(next, null)) return;
    publish(next);
    onAcceptedContent(latest);
  }, [onAcceptedContent, persist, publish]);

  const resetDraftFromAccepted = useCallback(() => {
    const current = stateRef.current;
    const next = { ...current, draftMarkdown: current.accepted.markdown, draftGeneration: current.draftGeneration + 1,
      editorRevision: current.editorRevision + 1,
      saveState: pendingRef.current ? current.saveState : "saved" as const, latestRemote: null, message: null, serializationIssues: [], savedAt: current.accepted.committed_at };
    if (!persist(next, pendingRef.current)) return;
    publish(next);
  }, [persist, publish]);

  return {
    state,
    hasUnsubmittedContent: state.saveState !== "saved" || state.draftMarkdown !== state.accepted.markdown || pendingRef.current !== null,
    changeDraft,
    retryRecovery,
    reviewLatest,
    useLatestDiscardingDraft: () => chooseLatest(false),
    keepDraftOnLatest: () => chooseLatest(true),
    resetDraftFromAccepted,
  };
}
