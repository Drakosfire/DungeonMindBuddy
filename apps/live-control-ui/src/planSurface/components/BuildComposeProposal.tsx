import { useEffect, useRef, useState } from 'react';
import { composeBuildProposal, getBuildProposal, getBuildProposalPrompt, listBuildProposals, reportBuildInsertion,
  type BuildProposalRecord } from '../../api/buildDocumentProposalApi';
import { getWorldAgentConversationHistory, postWorldAgentNewConversation } from '../../api/liveApi';
import type { WorldAgentConversationHistoryResponse } from '../../api/types';
import type { BuildComposeBridge, CapturedBuildInsertion } from '../../buildSurface/buildComposeBridge';
import { admitMarkdownInsertion } from '../../documentEditing/markdownInsertion';
import { WorldPlanAgentAnswer } from './WorldPlanAgentAnswer';
import { ResponseEvidenceTabs } from './BuddyPromptInspector';
import { PreparedRequestInspector } from './PreparedRequestInspector';
import './BuildComposeProposal.css';

export function useBuildCompose({ worldId, history, bridge, enabled, onHistory }: {
  worldId: string; history: WorldAgentConversationHistoryResponse | null; bridge: BuildComposeBridge | null;
  enabled: boolean; onHistory: (history: WorldAgentConversationHistoryResponse) => void;
}) {
  const scope = enabled ? `${worldId}:${history?.conversation_id ?? ''}` : '';
  const generation = useRef({ scope, epoch: 0 });
  if (generation.current.scope !== scope) generation.current = { scope, epoch: generation.current.epoch + 1 };
  const current = useRef({ scope, epoch: generation.current.epoch, worldId, history, bridge, enabled, onHistory });
  current.current = { scope, epoch: generation.current.epoch, worldId, history, bridge, enabled, onHistory };
  const [records, setRecords] = useState<{ scope: string; values: BuildProposalRecord[] }>({ scope: '', values: [] });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const running = useRef(false);
  const captures = useRef(new Map<string, CapturedBuildInsertion>());
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    setError(null);
    if (!enabled || !history?.conversation_id) return;
    const controller = new AbortController(); let active = true;
    listBuildProposals(worldId, history.conversation_id, controller.signal)
      .then(values => { if (active) setRecords(previous => ({ scope,
        values: [...values, ...(previous.scope === scope ? previous.values.filter(item => !values.some(saved => saved.action_id === item.action_id)) : [])]
          .sort((a, b) => a.created_at.localeCompare(b.created_at)) })); })
      .catch(() => { if (active) setError('Earlier page proposals could not be loaded.'); });
    return () => { active = false; controller.abort(); };
  }, [scope, worldId, enabled, history?.conversation_id]);
  function put(record: BuildProposalRecord, ownerScope: string, epoch = current.current.epoch, previousScope?: string) {
    if (mounted.current && ((current.current.scope === ownerScope && current.current.epoch === epoch)
      || (previousScope !== undefined && current.current.scope === previousScope && current.current.epoch === epoch - 1))) setRecords(previous => ({ scope: ownerScope,
      values: [...(previous.scope === ownerScope ? previous.values.filter(item => item.action_id !== record.action_id) : []), record]
        .sort((a, b) => a.created_at.localeCompare(b.created_at)) }));
  }
  async function submit(instruction: string): Promise<boolean> {
    const start = current.current;
    if (running.current || !start.enabled || !start.bridge || !start.history) return false;
    running.current = true; setBusy(true); setError(null);
    let action: string | null = null; let ownerScope = start.scope; let epoch = start.epoch;
    try {
      const captured = await start.bridge.capture();
      let pointer = start.history;
      if (!pointer.conversation_id) {
        const created = await postWorldAgentNewConversation(start.worldId, { schema: 'dmb_agent_new_conversation_v1',
          command_id: crypto.randomUUID(), expected_pointer_revision: pointer.pointer_revision, expected_active_conversation_id: null });
        pointer = await getWorldAgentConversationHistory(start.worldId);
        if (created.world_id !== start.worldId || pointer.world_id !== start.worldId
          || pointer.conversation_id !== created.conversation_id || pointer.active_conversation_id !== created.conversation_id
          || pointer.pointer_revision !== created.pointer_revision) throw new Error('The active conversation changed. Try again.');
        if (!mounted.current || current.current.scope !== start.scope || current.current.epoch !== start.epoch) return false;
        start.onHistory(pointer);
        ownerScope = `${start.worldId}:${pointer.conversation_id}`;
        epoch = start.epoch + 1;
      }
      if (!pointer.conversation_id || pointer.conversation_id !== pointer.active_conversation_id) throw new Error('Open the current World conversation first.');
      action = crypto.randomUUID();
      captures.current.set(action, captured);
      const result = await composeBuildProposal({ idempotency_key: action, conversation_id: pointer.conversation_id,
        expected_pointer_revision: pointer.pointer_revision, basis: captured.basis, instruction, draft_markdown: captured.draftMarkdown });
      if (result.proposal) admitMarkdownInsertion(result.proposal.replacement_markdown);
      put(result, ownerScope, epoch, ownerScope === start.scope ? undefined : start.scope);
      return true;
    } catch (reason) {
      if (action) {
        try { put(await getBuildProposal(start.worldId, action), ownerScope, epoch, ownerScope === start.scope ? undefined : start.scope); } catch { /* Never replay an uncertain provider request. */ }
      }
      if (mounted.current && ((current.current.scope === ownerScope && current.current.epoch === epoch) || (current.current.scope === start.scope && current.current.epoch === start.epoch))) setError(reason instanceof Error ? reason.message : 'The proposal outcome is unknown.');
      return false;
    } finally { running.current = false; if (mounted.current) setBusy(false); }
  }
  async function insert(record: BuildProposalRecord) {
    const start = current.current; const captured = captures.current.get(record.action_id);
    if (!captured || !start.bridge || record.inserted_in_draft || !record.proposal
      || start.history?.active_conversation_id !== record.reservation.conversation_id
      || start.history.pointer_revision !== record.reservation.expected_pointer_revision) return;
    try {
      start.bridge.insert(captured, record.proposal.replacement_markdown);
      captures.current.delete(record.action_id);
      put({ ...record, inserted_in_draft: true }, start.scope);
      try { put(await reportBuildInsertion(start.worldId, record), start.scope); }
      catch { setError('Inserted into your draft. Its history receipt could not be updated; save the page normally.'); }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'This proposal cannot be inserted here.'); }
  }
  return { busy, error, submit,
    items: records.scope === scope ? records.values.map(record => ({ key: record.action_id, afterSequence: record.after_turn_sequence,
      element: <BuildComposeProposal key={record.action_id} record={record}
        canInsert={captures.current.has(record.action_id) && Boolean(bridge)
          && history?.active_conversation_id === record.reservation.conversation_id
          && history.pointer_revision === record.reservation.expected_pointer_revision} onInsert={() => { void insert(record); }} /> })) : [] };
}

function BuildPrompt({ record }: { record: BuildProposalRecord }) {
  const [payload, setPayload] = useState<string | null>(null); const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    if (!record.authorization?.evidence_id) return;
    getBuildProposalPrompt(record.reservation.basis.world_id, record.action_id, controller.signal).then(value => {
      const auth = record.authorization!;
      if (value.schema !== 'dmb_build_proposal_prompt_v1' || value.world_id !== record.reservation.basis.world_id
        || value.action_id !== record.action_id || value.reference.evidence_id !== auth.evidence_id
        || value.reference.provider_attempt_id !== auth.provider_attempt_id || value.reference.payload_sha256 !== auth.payload_sha256
        || value.reference.payload_utf8_bytes !== auth.payload_utf8_bytes) throw new Error('binding');
      const body = JSON.parse(value.payload_json);
      if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('envelope');
      if (active) setPayload(value.payload_json);
    }).catch(() => { if (active) setError(true); });
    return () => { active = false; controller.abort(); };
  }, [record]);
  return !record.authorization?.evidence_id ? <p>No complete request was captured for this proposal.</p>
    : error ? <p role="alert">The captured request is unavailable.</p>
    : payload ? <PreparedRequestInspector payloadJson={payload} /> : <p role="status">Loading captured request…</p>;
}
export function BuildComposeProposal({ record, canInsert, onInsert }: { record: BuildProposalRecord; canInsert: boolean; onInsert: () => void }) {
  return <article className="build-compose-proposal" aria-label="Page proposal">
    <p className="build-compose-proposal__request"><strong>You</strong> {record.reservation.instruction}</p>
    {record.proposal ? <div className="world-plan-agent-conversation__message--assistant">
      <p>Proposed addition to your page</p>
      <WorldPlanAgentAnswer answer={record.proposal.replacement_markdown} />
      {record.proposal.assumptions.length ? <details><summary>Creative assumptions</summary><ul>{record.proposal.assumptions.map((text, i) => <li key={i}>{text}</li>)}</ul></details> : null}
      {record.inserted_in_draft ? <p role="status">Inserted into the draft. Save the page when you’re ready.</p>
        : canInsert ? <button type="button" onClick={onInsert}>Insert into page</button>
        : <p>This earlier proposal remains available to read. Ask again to insert at your current caret.</p>}
    </div> : <p role="status">{record.state === 'unknown' ? 'The request outcome is uncertain. It will not be repeated automatically.'
      : record.state === 'failed' ? 'The proposal could not be prepared.' : 'The proposal has not completed. It will not be repeated automatically.'}</p>}
    <details><summary>Inspect this proposal</summary><ResponseEvidenceTabs evidence={<p>Proposed authored lore for this page. This does not publish Graph facts or save the document.</p>}
      prompt={<BuildPrompt key={`${record.action_id}:${record.authorization?.evidence_id}`} record={record} />} /></details>
  </article>;
}
