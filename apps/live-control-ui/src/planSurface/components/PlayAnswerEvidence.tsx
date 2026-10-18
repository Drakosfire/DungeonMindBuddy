import { useEffect, useRef, useState } from 'react'
import { getWorldOwnedRunbookCommittedRevision, getWorldOwnedPlanCommittedRevision, LiveApiError } from '../../api/liveApi'
import type { AgentConversationTurnProvenanceV1 } from '../../api/types'
import { WorldPlanAgentAnswer } from './WorldPlanAgentAnswer'

type Props = { provenance: AgentConversationTurnProvenanceV1; worldId: string; turnId: string }
const uuid = (value: unknown): value is string => typeof value === 'string'
  && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)

export function PlayAnswerEvidence(props: Props) {
  // Remount on any saved-basis change, removing old private content synchronously.
  return <ScopedPlayAnswerEvidence key={JSON.stringify(props)} {...props} />
}
function ScopedPlayAnswerEvidence({ provenance, worldId }: Props) {
  const epoch = useRef(0)
  const [opened, setOpened] = useState<{ status: 'loading' | 'ready' | 'unavailable'; markdown?: string } | null>(null)
  useEffect(() => () => { epoch.current++ }, [])
  const references = provenance.supporting_work
  const runbooks = references.filter(ref => ref.kind === 'dmb_play_runbook_v1')
  const runbook = runbooks.length === 1 ? runbooks[0] : null
  const valid = provenance.world_id === worldId && provenance.surface_resolution === 'resolved'
    && provenance.surface_id === 'play' && provenance.primary_work.resolution === 'resolved'
    && provenance.primary_work.kind === 'run' && uuid(provenance.primary_work.object_id)
    && runbook?.resolution === 'resolved' && uuid(runbook.object_id) && uuid(runbook.work_revision_id)
    && typeof runbook.content_sha256 === 'string' && /^[0-9a-f]{64}$/.test(runbook.content_sha256)
    && Number.isSafeInteger(runbook.revision_n) && runbook.revision_n! > 0
  const selections = [
    ['dmb_play_current_beat_v1', 'Beat', 'beat:'],
    ['dmb_play_current_scene_v1', 'Scene', 'scene:'],
  ] as const
  async function open() {
    if (!valid || !runbook) return
    const generation = ++epoch.current
    setOpened({ status: 'loading' })
    try {
      let source
      try {
        source = await getWorldOwnedRunbookCommittedRevision(runbook.object_id!, worldId,
          runbook.revision_n!, runbook.content_sha256!)
      } catch (error) {
        // Runs can pin a Plan as their Runbook. Try only the same historical ID
        // and revision, never latest or another World, after a kind/not-found 404.
        if (!(error instanceof LiveApiError) || error.status !== 404) throw error
        source = await getWorldOwnedPlanCommittedRevision(runbook.object_id!, runbook.revision_n!)
        if (source.kind !== 'plan') throw new Error('Expected pinned Plan')
      }
      const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(source.markdown))
      const digest = Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('')
      if (source.schema_version !== 'dmb_workspace_committed_revision_v2' || source.scope_mode !== 'world'
        || source.world_id !== worldId || source.campaign_id !== null || !['runbook', 'plan'].includes(source.kind)
        || source.document_id !== runbook.object_id || source.work_revision_id !== runbook.work_revision_id
        || source.revision_n !== runbook.revision_n || source.content_sha256 !== runbook.content_sha256
        || digest !== runbook.content_sha256) throw new Error('Historical source differs')
      if (generation === epoch.current) setOpened({ status: 'ready', markdown: source.markdown })
    } catch { if (generation === epoch.current) setOpened({ status: 'unavailable' }) }
  }
  return <section aria-label="Authored Play context">
    <h4>Authored Play context</h4>
    <p>This answer’s saved context references identify prepared material, not recorded events or claim-level Graph citations.</p>
    {!valid ? <p>The exact Runbook reference is unavailable. No current material has been substituted.</p> : <>
      <p>Run <code>{provenance.primary_work.object_id}</code> · saved Run revision {provenance.primary_work.revision}</p>
      <p>Pinned Runbook · revision {runbook!.revision_n}</p>
      {selections.map(([kind, label, prefix]) => {
        const matches = references.filter(ref => ref.kind === kind)
        const ref = matches.length === 1 ? matches[0] : null
        return <p key={kind}>{label}: {ref?.resolution === 'resolved' && ref.object_id?.startsWith(prefix)
          ? <code>{ref.object_id}</code> : 'No unique saved reference.'}</p>
      })}
      <details><summary>Exact saved identity</summary>
        <p>Runbook <code>{runbook!.object_id}</code></p>
        <p>WorkRevision <code>{runbook!.work_revision_id}</code></p>
        <p>SHA-256 <code>{runbook!.content_sha256}</code></p>
      </details>
      <button type="button" disabled={opened?.status === 'loading'} onClick={() => { void open() }}>Open pinned Runbook</button>
    </>}
    {opened ? <section aria-label="Pinned Runbook source" aria-live="polite">
      <button type="button" onClick={() => { epoch.current++; setOpened(null) }}>Close pinned source</button>
      {opened.status === 'loading' ? <p>Opening exact saved revision…</p> : opened.status === 'unavailable'
        ? <p>The exact saved revision is unavailable. No newer text has been substituted.</p>
        : <><p>Exact pinned Runbook. This shows the authored source, not proof that every passage was used by the model.</p>
          <WorldPlanAgentAnswer answer={opened.markdown!} /></>}
    </section> : null}
  </section>
}
