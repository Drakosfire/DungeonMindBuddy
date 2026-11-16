import { useEffect, useState, useSyncExternalStore } from 'react'
import { getReadWaveVersion, subscribeReadWave } from '../../api/inFlightReads'
import { getWorldAgentNativeReplayAssertion, getWorldAgentReplayAssertion } from '../../api/liveApi'
import type { BuddyReplayAssertionResponse, BuddyReplayNativeAssertionResponse, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import type { RetrievalStep } from './BuddyRetrievalReplay'

export function useRecordedReplayAssertion({ trace, step, assertionId, open }: {
  trace: BuddyTurnContextTrace; step: RetrievalStep; assertionId: string; open: boolean
}) {
  const { world_id, turn_id, trace_id } = trace
  const { sequence, revision_pin, scope_mode, campaign_id, native } = step
  const wave = useSyncExternalStore(subscribeReadWave, getReadWaveVersion, getReadWaveVersion)
  const binding = JSON.stringify([world_id, turn_id, trace_id, sequence, assertionId, revision_pin, scope_mode, campaign_id, native])
  const [read, setRead] = useState<{ binding: string; wave: number; assertion: (BuddyReplayAssertionResponse['assertion'] & Pick<BuddyReplayNativeAssertionResponse['assertion'], 'metadata'>) | null; excerpts?: BuddyReplayNativeAssertionResponse['excerpts'] }>()
  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    setRead(undefined)
    const owns = () => !controller.signal.aborted && getReadWaveVersion() === wave
    const load = native ? getWorldAgentNativeReplayAssertion : getWorldAgentReplayAssertion
    void load(world_id, turn_id, trace_id, sequence, assertionId, controller.signal)
      .then(result => {
        if (!owns()) return
        const nativeResult = result.schema === 'dmb_replay_native_assertion_v1'
        if (nativeResult !== Boolean(native) || result.world_id !== world_id
          || result.turn_id !== turn_id || result.trace_id !== trace_id || result.sequence !== sequence
          || (nativeResult ? result.revision_id !== revision_pin
            : result.schema !== 'dmb_replay_assertion_v1' || result.scope?.managed_world_id !== world_id
              || result.scope.revision_id !== revision_pin || result.scope.scope_mode !== scope_mode
              || result.scope.campaign_id !== campaign_id)
          || result.assertion?.assertion_id !== assertionId) throw new Error('Assertion response binding differs')
        setRead({ binding, wave, assertion: result.assertion, excerpts: nativeResult ? result.excerpts : undefined })
      }).catch(() => { if (owns()) setRead({ binding, wave, assertion: null }) })
    return () => controller.abort()
  }, [open, wave, world_id, turn_id, trace_id, sequence, assertionId, revision_pin, scope_mode, campaign_id, native, binding])

  return read?.binding === binding && read.wave === wave ? read : undefined
}

export function BuddyReplayAssertion({ trace, step, assertionId }: {
  trace: BuddyTurnContextTrace; step: RetrievalStep; assertionId: string
}) {
  const [open, setOpen] = useState(false)
  const read = useRecordedReplayAssertion({ trace, step, assertionId, open })
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Open assertion · {assertionId}</summary>
    {open && (!read ? <p role="status">Reading the recorded assertion…</p>
      : read.assertion ? <RecordedReplayAssertionContent read={read} />
      : <p role="alert">The assertion is unavailable at the recorded revision.</p>)}
  </details>
}


export function RecordedReplayAssertionContent({
  read,
}: { read: NonNullable<ReturnType<typeof useRecordedReplayAssertion>> }) {
  if (!read.assertion) return null;
  return <>
    <p>{read.assertion.subject_entity_id} · {read.assertion.predicate}</p>
    <pre>{JSON.stringify(read.assertion.value, null, 2)}</pre>
    {read.excerpts?.map(excerpt => <blockquote key={excerpt.evidence_ref_id}>{excerpt.text}</blockquote>)}
  </>;
}
